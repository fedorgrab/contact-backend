import random
import weakref
from typing import Any, Callable, Dict, Optional

from django.contrib.auth import get_user_model

from contact.game import storage
from contact.game.constants import (
    CONTACT_AWAITING_TIME,
    GAME_TIME_LIMIT,
    NUMBER_OF_PLAYERS_TO_START,
    PLAYER_DISCONNECTION_AWAITING_TIME,
    POINTS,
    GameEvent,
    GameFinishReason,
)
from contact.game.exceptions import (
    DontTellAnyOneOfThisAction,
    GameActionError,
    GameRuleError,
)

User = get_user_model()
JSON = Dict[str, Any]


class GameManagerDelegate:
    """
    A protocol describing the way how and which methods of async-based
    WSConsumer should be executed from sync-based GameManager.
    Generally GameManager (a.k.a brain or model from MVC) shouldn't know about
    WSConsumer (a.k.a communicator or controller from MVC) and its duties, but
    due to the specificity of the game WSConsumer should somehow know about
    exclusive game actions in a separate order. Even though brain does
    not want to know about the communicator, it should signal about these specific
    actions. That's why this protocol implements the backwards connection to
    communicator (or in different words it helps to delegate the responsibility
    of brain to communicator).
    That is needed when users should have receive message not strictly
    after the game event, but in a different time (e.g. delayed message regarding
    to event, or message in the middle of the event)
    """

    game_manager: "GameManager"

    def order_delayed_action(self, after, event, action_kwargs=None):
        raise NotImplementedError


class GameManager:
    """
    GameManager is single for player and websocket consumer
    All the game logic should be implemented in a sync way.
    """

    room: storage.Room
    player: storage.Player

    def __init__(self, user: User, delegate: GameManagerDelegate):
        self._delegate = weakref.ref(delegate)
        player, created = storage.Player.get_or_create(obj_id=user.username)
        # noinspection PyTypeChecker
        self.player = player
        self.restored = not created
        super().__init__()

    @property
    def delegate(self) -> GameManagerDelegate:
        return self._delegate()

    @property
    def initial_information(self) -> JSON:
        self.refresh()
        self.room.get_offers()
        return self.room.common_data

    @property
    def initial_event(self) -> GameEvent:
        return GameEvent.CONTINUE if self.restored else GameEvent.START

    @staticmethod
    def select_host(room: storage.Room) -> str:
        # host_id = random.choice(room.get_player_ids())
        host_id = room.get_player_ids()[0]
        host = storage.Player.get_by_id(host_id)
        host.is_game_host = True
        host.save()
        return host_id

    def append_user_to_game(self) -> storage.Room:
        if self.restored:
            storage.delete_player_from_disconnected(self.player)
            room = storage.Room.get_by_id(obj_id=self.player.room_id)
        else:
            room = storage.Room.get_free_room() or storage.Room.create_room()
            storage.append_player_to_room(self.player, room)

            if room.number_of_players == NUMBER_OF_PLAYERS_TO_START:
                room.game_host_key = self.select_host(room)
                room.unfree()
                room.is_full = True
                room.save()
                self.delegate.order_delayed_action(
                    after=GAME_TIME_LIMIT,
                    event=GameEvent.FINISH,
                    action_kwargs={"reason": GameFinishReason.GAME_TIME_LIMIT_EXPIRED},
                )

        self.room = room
        return room

    def disconnect_player(self):
        if self.room.is_full:
            if not storage.room_is_cleaning(self.room) and storage.room_exist(
                self.room
            ):
                self.delegate.order_delayed_action(
                    after=PLAYER_DISCONNECTION_AWAITING_TIME,
                    event=GameEvent.FINISH,
                    action_kwargs={"reason": GameFinishReason.DISCONNECTION},
                )
            storage.set_player_disconnected(self.player)

    def refresh(self):
        self.room.refresh()
        self.player.refresh()

    # Game actions #

    def action_player_state(self) -> storage.Player:
        self.player.refresh()
        return self.player

    def action_finish_game(self, reason):
        self.refresh()
        self.room.game_is_finished = True

        if reason == GameFinishReason.DISCONNECTION:
            player_still_disconnected = storage.check_for_disconnected_player(
                player=self.player
            )
            if player_still_disconnected:
                self.room.winner = "none"
                self.room.game_is_finished = True
                self.room.game_finish_reason = GameFinishReason.DISCONNECTION
                storage.order_room_cleaning(self.room)
            else:
                # Could not think of anything better ¯\_(ツ)_/¯
                raise DontTellAnyOneOfThisAction()

        self.room.save()

    def action_word(self, word: str):
        """After setting word users get room state"""
        self.player.refresh()
        if not self.player.is_game_host:
            raise GameRuleError("Only game host is able to set a room word")

        self.room.hosted_word = word.lower()
        self.room.game_is_started = True
        self.room.save()

    def action_offer(self, answer: str, definition: str):
        if self.player.id_key == self.room.game_host_key:
            raise GameRuleError("Game host is not able to offer guesses")

        offer_is_relevant = storage.check_answer_relevance(
            answer=answer.lower(), room=self.room
        )

        if not offer_is_relevant:
            raise GameActionError("This word was already guessed")

        answer_cut = answer[: self.room.open_letters_number]

        if answer_cut.lower() != self.room.open_word:
            raise GameActionError("Answer does not fit open letters")

        offer = storage.Offer.create_object(
            sender_id=self.player.id_key,
            definition=definition.lower(),
            answer_internal=answer.lower(),
        )
        storage.append_offer_to_room(offer, self.room)

    def action_comment_offer(self, offer_id: str, comment_text: str):
        offer = storage.Offer.get_by_id(offer_id)
        if offer.is_canceled:
            raise GameRuleError("Canceled offers can not be commented")

        if offer.sender_id != self.player.id_key:
            raise GameRuleError("Only offer sender is able to comment it")

        offer.hints.append(comment_text)
        offer.save()

    def action_cancel(self, offer_id: str, estimated_word: str):
        """
        :param offer_id: Offer storage id
        :param estimated_word: Estimated word, which should be meant by offer sender
        """

        offer = storage.Offer.get_by_id(offer_id)

        if not self.player.id_key == self.room.game_host_key:
            raise GameRuleError("Only game host is able to cancel guesses")

        if offer.is_canceled:
            raise GameRuleError("Offers can't be canceled multiple times")

        if offer.answer_internal == estimated_word.lower():
            offer.is_canceled = True
            offer.save()
            self.player.increase_points(by=POINTS.CONTACT_CANCEL)

    def action_accept_offer(self, offer_id: str, estimated_word: str):
        if self.room.contact_in_process:
            raise GameRuleError(
                "It is forbidden to accept multiple offers simultaneously"
            )

        offer = storage.Offer.get_by_id(offer_id)
        estimated_word = estimated_word.lower()
        estimated_word_cut = estimated_word[: self.room.open_letters_number]

        if offer.sender_id == self.player.id_key:
            raise GameRuleError("Players can't accept their own offers")

        if offer.is_canceled:
            raise GameRuleError("It is forbidden to guess canceled offers")

        if estimated_word_cut.lower() != self.room.open_word:
            raise GameActionError("Estimated word does not fit open letters")

        offer.in_process = True
        offer.participants.append(self.player.id_key)
        offer.estimated_word = estimated_word
        offer.save()

        self.room.contact_in_process = True
        self.room.contact_offer_key = offer.id_key
        self.room.save()

        self.delegate.order_delayed_action(
            after=CONTACT_AWAITING_TIME, event=GameEvent.CONTACT_RESULT
        )

    def action_contact_result(self):
        """
        Should be evoked in a specific time after contact action
        to provide the game host some time to cancel the offer
        """
        processed_offer = storage.Offer.get_by_id(self.room.contact_offer_key)

        success = not processed_offer.is_canceled and (
            processed_offer.estimated_word == processed_offer.answer_internal
        )
        processed_offer.is_contacted = success
        processed_offer.save()

        if len(self.room.hosted_word) - self.room.open_letters_number == 1 or (
            self.room.hosted_word == processed_offer.estimated_word and success
        ):
            self.delegate.order_delayed_action(after=0.5, event=GameEvent.FINISH)

        if processed_offer.answer_internal == self.room.hosted_word:
            self.delegate.order_delayed_action(after=0.5, event=GameEvent.FINISH)

        if success:
            self.room.increment_open_letters_number()
            self.room.clear_offers()
            storage.mark_offer_as_processed(offer=processed_offer, room=self.room)
            # TODO: Think of moving this logic out of the method to separate action
            # TODO: to let the client understand when their points are updated
            # contact_initiator = storage.Player.get_by_id(contact.initiator_id)
            # contact_initiator.increase_points(POINTS.CONTACT_INITIATOR_SUCCESS)
            #
            # for participant in (
            #     storage.Player.get_by_id(p_id) for p_id in processed_offer.participants
            # ):
            #     participant.increase_points(by=POINTS.CONTACT_PARTICIPANT_SUCCESS)

        self.room.contact_in_process = False
        self.room.save()

    # Game action handling #
    def switch_action(self, event: GameEvent) -> Callable:
        return {
            GameEvent.FINISH: self.action_finish_game,
            GameEvent.PLAYER_STATE: self.action_player_state,
            GameEvent.SET_WORD: self.action_word,
            GameEvent.OFFER: self.action_offer,
            GameEvent.OFFER_COMMENT: self.action_comment_offer,
            GameEvent.CONTACT: self.action_accept_offer,
            GameEvent.CANCEL_CONTACT: self.action_cancel,
            GameEvent.CONTACT_RESULT: self.action_contact_result,
        }[event]

    def perform_game_action(self, event: GameEvent, data: JSON) -> Optional[JSON]:
        self.room.refresh()
        self.switch_action(event)(**data)
        self.room.get_offers()
        return self.room.common_data
