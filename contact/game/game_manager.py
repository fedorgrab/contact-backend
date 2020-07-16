import random
from typing import Any, Callable, Dict

from django.contrib.auth import get_user_model

from contact.game import storage
from contact.game.constants import (
    CONTACT_AWAITING_TIME,
    NUMBER_OF_PLAYERS_TO_START,
    POINTS,
    GameEvent,
)
from contact.game.exceptions import GameActionError, GameRuleError

User = get_user_model()
JSON = Dict[str, Any]


class GameManagerDelegate:
    """
    A protocol describing the way how and which methods of async-based
    WSConsumer should be executed from sync-based GameManager.
    Generally GameManager (a.k.a brain or model from MVC) shouldn't know about
    WSConsumer (a.k.a communicator or controller from MVC) and its duties, but
    due to the specificity of the game WSConsumer should somehow know about
    exclusive game actions in a separate order. Hence even though brain does
    not wanna know about the communicator, it should signal about this specific
    actions. That's why this protocol implements the backwards connection to
    communicator (or in different words it helps to delegate the responsibility
    of brain to its delegate – communicator).
    That could be needed when users should have receive messages not strictly
    after the game event, but in a different time (e.g. delayed messages regarding
    to event, or message in the middle of the event)
    """

    game_manager: "GameManager"

    def order_delayed_action(self, after, event):
        raise NotImplementedError


class GameManager:
    """
    GameManager is single for player and websocket consumer
    All the game logic should be implemented in a sync way.
    """

    room: storage.Room
    player: storage.Player
    delegate: GameManagerDelegate

    def __init__(self, user: User, delegate: GameManagerDelegate):
        self.delegate = delegate
        player, created = storage.Player.get_or_create(obj_id=user.username)
        self.player = player
        self.restored = not created
        super().__init__()

    @property
    def initial_information(self) -> JSON:
        self.refresh()
        return self.room.common_data

    @property
    def initial_event(self) -> GameEvent:
        return GameEvent.CONTINUE if self.restored else GameEvent.START

    @staticmethod
    def select_host(room: storage.Room) -> str:
        host_id = random.choice(room.get_player_ids())
        host = storage.Player.get_by_id(host_id)
        host.is_game_host = True
        host.save()
        return host_id

    def append_user_to_game(self) -> storage.Room:
        if self.restored:
            room = storage.Room.get_by_id(obj_id=self.player.room_id)
        else:
            room = storage.Room.get_free_room() or storage.Room.create_room()
            storage.append_player_to_room(self.player, room)

            if room.number_of_players == NUMBER_OF_PLAYERS_TO_START:
                room.game_host = self.select_host(room)
                room.unfree()
                room.is_full = True
                room.save()

        self.room = room
        return room

    def refresh(self):
        self.room.refresh()
        self.player.refresh()

    # Game actions #
    def action_finish_game(self) -> storage.Room:
        # TODO: Work with that more. It isn't done
        self.refresh()
        self.room.game_is_finished = True
        self.room.save()
        return self.room

    def action_message(self, answer: str, definition: str) -> storage.Message:
        message = storage.Message.create_object(
            sender_id=self.player.player_id,
            definition=definition,
            answer_internal=answer,
        )
        storage.append_message_to_room(message, self.room)
        return message

    def action_comment_message(
        self, message_id: str, comment_text: str
    ) -> storage.Message:
        message = storage.Message.get_by_id(message_id)
        if message.is_canceled:
            raise GameRuleError("Canceled messages can not be commented")

        if message.sender_id != self.player.player_id:
            raise GameRuleError("Only message sender is able to comment it")

        message.hints.append(comment_text)
        message.save()
        return message

    def action_word(self, word: str) -> storage.Room:
        """After setting word users get room state"""
        self.refresh()

        if not self.player.is_game_host:
            raise GameRuleError("Only game host is able to set a room word")

        self.room.hosted_word = word.lower()
        self.room.game_is_started = True
        self.room.save()
        return self.room

    def action_cancel(self, message_id: str, estimated_word: str) -> storage.Message:
        """
        :param message_id: Message storage id
        :param estimated_word: Estimated word, which should be meant by message sender
        """
        message = storage.Message.get_by_id(message_id)

        if not self.player.player_id == self.room.game_host:
            raise GameRuleError("Only game host is able to cancel guesses")

        if message.is_canceled:
            raise GameRuleError("Messages can't be canceled multiple times")

        if message.answer_internal == estimated_word.lower():
            message.is_canceled = True
            message.open_answer()
            message.save()
            self.player.increase_points(by=POINTS.CONTACT_CANCEL)

        return message

    def action_contact(self, message_id: str, estimated_word: str) -> storage.Contact:
        message = storage.Message.get_by_id(message_id)
        estimated_word_cut = estimated_word[: self.room.open_letters_number]

        if message.sender_id == self.player.player_id:
            raise GameRuleError("Players can't guess their own messages")

        if message.is_canceled:
            raise GameRuleError("It is forbidden to guess canceled messages")

        if estimated_word_cut.lower() != self.room.open_word:
            raise GameActionError("Estimated word does not fit open letters")

        contact = storage.Contact.create_contact(
            room_id=self.room.room_id,
            message_id=message_id,
            estimated_word=estimated_word,
            initiator_id=message.sender_id,
            participant=self.player,
        )

        self.delegate.order_delayed_action(
            after=CONTACT_AWAITING_TIME, event=GameEvent.CONTACT_RESULT
        )
        return contact

    def action_contact_result(self) -> storage.Room:
        """
        Should be evoked in contact in a specific time after contact action
        to provide the game host some time to cancel the contact
        """
        contact = storage.Contact.get_by_id(self.room.room_id)
        message = storage.Message.get_by_id(contact.message_id)
        success = not message.is_canceled and (
            contact.estimated_word == message.answer_internal
        )
        contact.successful = success
        contact.save()
        if len(self.room.hosted_word) - self.room.open_letters_number == 1 or (
            self.room.hosted_word == contact.estimated_word and success
        ):
            self.delegate.order_delayed_action(after=0, event=GameEvent.FINISH)

        if success:
            contact_initiator = storage.Player.get_by_id(contact.initiator_id)
            contact_initiator.increase_points(POINTS.CONTACT_INITIATOR_SUCCESS)

            for participant in (
                storage.Player.get_by_id(p_id) for p_id in contact.participants
            ):
                participant.increase_points(by=POINTS.CONTACT_PARTICIPANT_SUCCESS)

        self.room.increment_open_letters_number()
        self.room.refresh()
        return self.room

    # Game action handling #
    def __switch_action(self, event: GameEvent) -> Callable:
        return {
            GameEvent.SET_WORD: self.action_word,
            GameEvent.CONTACT: self.action_contact,
            GameEvent.MESSAGE_RECEIVE: self.action_message,
            GameEvent.MESSAGE_COMMENT: self.action_comment_message,
            GameEvent.CANCEL_CONTACT: self.action_cancel,
            GameEvent.CONTACT_RESULT: self.action_contact_result,
            GameEvent.FINISH: self.action_finish_game,
        }[event]

    def perform_game_action(self, event: GameEvent, data: JSON) -> JSON:
        action = self.__switch_action(event)
        game_entity = action(**data)
        return game_entity.common_data
