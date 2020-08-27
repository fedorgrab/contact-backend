import asyncio
import time
from typing import List

from contact.game import constants, storage_handler


class Player(storage_handler.StorageComplexObject):
    id_key = storage_handler.IdField()
    is_game_host = storage_handler.BooleanField(default=False)
    room_id = storage_handler.RelationKeyField()
    points = storage_handler.IntegerField(default=0)
    storage_key_prefix = "player"

    def increase_points(self, by):
        self._increment_field(field_name="points", by=by)


def open_answer_callback(instance: "Offer"):
    if not any((instance.is_contacted, instance.is_canceled)):
        return None

    return instance.answer_internal


class Offer(storage_handler.StorageComplexObject):
    """
    Structure representing the opportunity to contact with other players
    every time when the sender wants to explain a word
    """

    id_key = storage_handler.IdField()
    sender_id = storage_handler.RelationKeyField()
    definition = storage_handler.StringField()
    answer = storage_handler.CalculatedStringField(
        callback=open_answer_callback, null=True
    )
    answer_internal = storage_handler.StringField(internal=True)
    hints = storage_handler.ListField()
    # Contact related
    is_canceled = storage_handler.BooleanField(default=False)
    is_contacted = storage_handler.BooleanField(default=False)
    in_process = storage_handler.BooleanField(default=False)
    participants = storage_handler.ListField()
    estimated_word = storage_handler.StringField()

    storage_key_prefix = "offer"


def open_word_callback(instance: "Room"):
    if len(instance.hosted_word) == 0:
        return instance.hosted_word

    return instance.hosted_word[: instance.open_letters_number]


class Room(storage_handler.StorageComplexObject):
    id_key = storage_handler.IdField()

    number_of_players = storage_handler.IntegerField(default=0)
    game_host_key = storage_handler.StringField()
    is_full = storage_handler.BooleanField(default=False)
    game_is_started = storage_handler.BooleanField(default=False)
    game_is_finished = storage_handler.BooleanField(default=False)
    winner = storage_handler.StringField()
    game_finish_reason = storage_handler.StringField()

    hosted_word = storage_handler.StringField(internal=True)
    open_word = storage_handler.CalculatedStringField(callback=open_word_callback)
    open_letters_number = storage_handler.IntegerField(default=1, internal=True)

    contact_in_process = storage_handler.BooleanField(default=False)
    contact_offer_key = storage_handler.StringField(internal=True)

    storage_key_prefix = "room"
    free_room_storage_key = "free_room"
    players_storage_key_prefix = "players:room"
    offers_storage_key_prefix = "offers:room"
    processed_offers_key_prefix = "offers:processed:room"

    # TODO: Maybe I should use ListField instead of storage lists

    @property
    def players_list_key(self):
        return f"{self.players_storage_key_prefix}:{self.id_key}"

    @property
    def offer_list_key(self):
        return f"{self.offers_storage_key_prefix}:{self.id_key}"

    @property
    def processed_offers_set_key(self):
        return f"{self.processed_offers_key_prefix}:{self.id_key}"

    @classmethod
    def get_free_room(cls) -> "Room":
        free_room_id = storage_handler.get_redis_value(key=cls.free_room_storage_key)
        return cls.get_by_id(obj_id=free_room_id)

    @classmethod
    def create_room(cls) -> "Room":
        new_room = cls.create_object()
        storage_handler.set_value(key=cls.free_room_storage_key, value=new_room.id_key)
        return new_room

    def get_player_ids(self) -> List[str]:
        return storage_handler.get_list(key=self.players_list_key)

    def get_offer_ids(self) -> List[str]:
        return storage_handler.get_list(key=self.offer_list_key)

    @staticmethod
    def get_room_related_objects(obj_class, obj_ids):
        return [obj_class.get_by_id(obj_id) for obj_id in obj_ids]

    def get_room_players(self) -> List[Player]:
        return self.get_room_related_objects(Player, self.get_player_ids())

    def get_offers(self):
        self.data["offers"] = [
            offer.common_data
            for offer in self.get_room_related_objects(Offer, self.get_offer_ids())
        ]
        self._StorageComplexObject__update_fields()

    def clear_offers(self):
        storage_handler.delete(*self.get_offer_ids(), self.offer_list_key)

    def increment_number_of_players(self):
        self._increment_field(field_name="number_of_players")

    def decrement_number_of_player(self):
        self._increment_field(field_name="number_of_players", by=-1)

    def increment_open_letters_number(self):
        self._increment_field(field_name="open_letters_number")

    def unfree(self):
        storage_handler.delete(self.free_room_storage_key)


def append_player_to_room(player: Player, room: Room):
    player.room_id = room.id_key
    player.save()
    room.increment_number_of_players()
    storage_handler.list_push(room.players_list_key, player.id_key)


def append_offer_to_room(offer: Offer, room: Room):
    storage_handler.list_push(room.offer_list_key, offer.id_key)


def mark_offer_as_processed(offer: Offer, room: Room):
    storage_handler.add_value_to_set(
        set_key=room.processed_offers_set_key, value=offer.answer_internal
    )


def check_answer_relevance(answer, room: Room) -> bool:
    return not storage_handler.is_in_set(
        set_key=room.processed_offers_set_key, value=answer
    )


def set_player_disconnected(player):
    storage_handler.set_value(
        key=f"disconnection:{player.id_key}",
        value=1,
        expire=constants.PLAYER_DISCONNECTION_AWAITING_TIME + 5,
    )


def delete_player_from_disconnected(player):
    storage_handler.delete(
        constants.DISCONNECTION_KEY_FORMAT.format(player_id=player.id_key)
    )


def check_for_disconnected_player(player):
    return bool(
        storage_handler.get_value(
            constants.DISCONNECTION_KEY_FORMAT.format(player_id=player.id_key)
        )
    )


async def clean_room(room):
    start_time = time.time()
    print(f"Room cleaning will be processed in {constants.ROOM_CLEANING_DELAY}")
    storage_handler.set_value(
        key=constants.CLEANING_ROOM_KEY_FORMAT.format(room_id=room.id_key), value=1
    )
    await asyncio.sleep(constants.ROOM_CLEANING_DELAY)
    offer_ids = (f"offer:{offer_id}" for offer_id in room.get_offer_ids())
    player_ids = (f"player:{player_id}" for player_id in room.get_player_ids())
    storage_handler.delete(
        *offer_ids,
        *player_ids,
        room.storage_key,
        room.offer_list_key,
        room.players_list_key,
        room.processed_offers_set_key,
    )

    print(storage_handler.get_value("free_room"))
    if storage_handler.get_value("free_room") == room.id_key:
        storage_handler.delete("free_room")

    storage_handler.delete(
        constants.CLEANING_ROOM_KEY_FORMAT.format(room_id=room.id_key)
    )
    print(f"Room cleaning done. Spent {time.time() - start_time}")


def order_room_cleaning(room):
    asyncio.create_task(clean_room(room))


def room_is_cleaning(room):
    return storage_handler.exist(
        constants.CLEANING_ROOM_KEY_FORMAT.format(room_id=room.id_key)
    )


def room_exist(room):
    return storage_handler.exist(room.storage_key)
