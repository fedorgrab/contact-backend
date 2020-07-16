from typing import List

from contact.game import storage_handler


class Player(storage_handler.StorageComplexObject):
    player_id = storage_handler.IdField()
    is_game_host = storage_handler.BooleanField(default=False)
    room_id = storage_handler.RelationKeyField()
    points = storage_handler.IntegerField(default=0)
    storage_key_prefix = "player"

    def increase_points(self, by):
        self._increment_field(field_name="points", by=by)


class Message(storage_handler.StorageComplexObject):
    message_id = storage_handler.IdField()
    sender_id = storage_handler.RelationKeyField()
    is_canceled = storage_handler.BooleanField(default=False)
    definition = storage_handler.StringField()
    answer_common = storage_handler.StringField()
    answer_internal = storage_handler.StringField(internal=True)
    hints = storage_handler.ListField()

    storage_key_prefix = "message"

    def open_answer(self):
        self.answer_common = self.answer_internal


class Contact(storage_handler.StorageComplexObject):
    contact_id = storage_handler.IdField(internal=True)
    message_id = storage_handler.RelationKeyField()
    initiator_id = storage_handler.RelationKeyField()
    estimated_word = storage_handler.StringField()
    successful = storage_handler.BooleanField(null=True)
    participants = storage_handler.ListField()

    storage_key_prefix = "contact:room"
    # participants_storage_key_prefix = "contact:room:participants"

    @classmethod
    def create_contact(
        cls,
        room_id: str,
        estimated_word: str,
        message_id: str,
        initiator_id: str,
        participant: Player,
    ) -> "Contact":
        return cls.create_object(
            contact_id=room_id,
            estimated_word=estimated_word,
            message_id=message_id,
            initiator_id=initiator_id,
            participants=[participant.player_id],
        )

    # @property
    # def participants_storage_key(self):
    #     return f"{self.participants_storage_key_prefix}:{self.contact_id}"

    def get_participants(self):
        return storage_handler.get_list(key=self.participants_storage_key)


# def append_contact_participant(contact, participant_id):
#     storage_handler.list_push(
#         list_key=contact.participants_storage_key, value=participant_id
#     )


def open_word_callback(instance: "Room"):
    if len(instance.hosted_word) == 0:
        return instance.hosted_word

    return instance.hosted_word[: instance.open_letters_number]


class Room(storage_handler.StorageComplexObject):
    room_id = storage_handler.IdField()
    is_full = storage_handler.BooleanField(default=False)
    number_of_players = storage_handler.IntegerField(default=0)
    game_host = storage_handler.StringField()
    hosted_word = storage_handler.StringField(internal=True)
    open_word = storage_handler.CalculatedStringField(callback=open_word_callback)
    open_letters_number = storage_handler.IntegerField(default=1, internal=True)
    game_is_started = storage_handler.BooleanField(default=False)
    game_is_finished = storage_handler.BooleanField(default=False)
    contact_value = storage_handler.StringField(internal=True)

    storage_key_prefix = "room"
    free_room_storage_key = "free_room"
    players_storage_key_prefix = "players:room"
    messages_storage_key_prefix = "messages:room"

    @property
    def players_list_key(self):
        return f"{self.players_storage_key_prefix}:{self.room_id}"

    @property
    def message_list_key(self):
        return f"{self.messages_storage_key_prefix}:{self.room_id}"

    @classmethod
    def get_free_room(cls) -> "Room":
        free_room_id = storage_handler.get_redis_value(key=cls.free_room_storage_key)
        return cls.get_by_id(obj_id=free_room_id)

    @classmethod
    def create_room(cls) -> "Room":
        new_room = cls.create_object()
        storage_handler.set_value(key=cls.free_room_storage_key, value=new_room.room_id)
        return new_room

    def get_player_ids(self) -> List[str]:
        return storage_handler.get_list(key=self.players_list_key)

    def get_message_ids(self) -> List[str]:
        return storage_handler.get_list(key=self.message_list_key)

    @staticmethod
    def get_room_related_objects(obj_class, obj_ids):
        return [obj_class.get_by_id(obj_id) for obj_id in obj_ids]

    def get_room_players(self) -> List[Player]:
        return self.get_room_related_objects(Player, self.get_player_ids())

    def get_room_messages(self) -> List[Message]:
        return self.get_room_related_objects(Message, self.get_message_ids())

    def increment_number_of_players(self):
        self._increment_field(field_name="number_of_players")

    def increment_open_letters_number(self):
        self._increment_field(field_name="open_letters_number")

    def unfree(self):
        storage_handler.delete_value(self.free_room_storage_key)


def append_player_to_room(player: Player, room: Room):
    player.room_id = room.room_id
    player.save()
    room.increment_number_of_players()
    storage_handler.list_push(room.players_list_key, player.player_id)


def append_message_to_room(message: Message, room: Room):
    storage_handler.list_push(room.message_list_key, message.message_id)
