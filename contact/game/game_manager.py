from asgiref.sync import async_to_sync

from contact.game.constants import GameEvent
from contact.game.models import Message, Player, Room


class GameManagerDelegate:
    async def contact_closure(self, contact_data):
        raise NotImplementedError

    def perform_contact(self, contact_data):
        async_to_sync(self.contact_closure(contact_data))


class GameManager:
    """
    One GameManager on a single connection: manager for player and socket consumer
    """

    def __init__(self, user, delegate):
        self.player: Player = Player.get_by(username=user.username)
        self.delegate: GameManagerDelegate = delegate
        self.room: Room = None

        if not self.player:
            self.player = Player(username=user.username)

        super().__init__()

    @property
    def initial_information(self) -> dict:
        return {**self.room.serialize()}

    @property
    def game_is_started(self):
        return self.room.game_is_started

    # Room management methods #
    def append_user_to_game(self) -> Room:
        self.room = self.get_free_room()
        if len(self.room.players) == 2 and not self.room.game_is_started:
            # Means that the third player is added but isn't still saved
            # and also excludes case when game in the room was interrupted
            self.player.is_game_host = True
            self.room.game_host = self.player
            self.room.game_is_started = True
            self.room.save()

        self.player.room = self.room
        self.player.save()
        return self.room

    def remove_user_from_game(self) -> None:
        self.player.delete()

    @staticmethod
    def get_free_room() -> Room:
        return Room.query.get_free()

    # Game management methods #
    def receive_message(self, word: str, definition: str) -> Message:
        message = Message(
            word=word.lower(), definition=definition.lower(), sender=self.player
        )
        message.save()

        return message

    def set_word(self, word: str) -> Room:
        self.room.word = word.lower()
        self.room.save()
        return self.room

    # Game actions handlers #
    def __switch_action(self, event: GameEvent):
        return {
            GameEvent.RECEIVE_MESSAGE: self.receive_message,
            GameEvent.SET_WORD: self.set_word,
        }[event]

    def perform_game_action(self, event: GameEvent, data: dict):
        action = self.__switch_action(event)
        game_entity = action(**data)
        return game_entity.serialize()
