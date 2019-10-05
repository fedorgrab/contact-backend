import rom
from rom import ClassProperty, columns
from rom.model import Model as RedisStorageModel


class RoomQuery(rom.Query):
    @staticmethod
    def create():
        room = Room()
        room.save()
        return room

    def get_free(self):
        return self.filter(game_is_started=False).first() or self.create()

    @staticmethod
    def get_for_user(username):
        return Player.get_by(username=username).room


class Serializable:
    def serialize(self):
        raise NotImplementedError


class RoomMessages(Serializable, list):
    def serialize(self):
        return [i.serialize() for i in self]


class Room(Serializable, RedisStorageModel):
    players = columns.OneToMany(ftable="Player")
    game_host = columns.OneToOne(ftable="Player", on_delete="cascade")
    game_is_started = columns.Boolean(default=False, index=True)
    contact = columns.OneToOne(ftable="Contact", on_delete="cascade")
    messages = columns.OneToMany(ftable="Message")
    word = columns.Text(default="")
    number_of_opened_letters = columns.Integer(default=1)

    @property
    def opened_word(self):
        return self.word[: self.number_of_opened_letters]

    @ClassProperty
    def query(cls):
        return RoomQuery(cls)

    def serialize(self):
        values_to_be_ignored = ["contact", "word", "number_of_opened_letters"]
        data = dict(
            filter(
                lambda key: key[0] not in values_to_be_ignored, self.to_dict().items()
            )
        )
        data.update(
            players=list(map(lambda player: player.username, self.players)),
            game_host=self.game_host.username if self.game_host else None,
            opened_word=self.opened_word,
        )
        return data


class Contact(Serializable, RedisStorageModel):
    participants = columns.OneToMany(ftable="Player")
    guess_word = columns.Text()
    message_id = columns.Integer(required=True)


class Player(Serializable, RedisStorageModel):
    username = columns.Text(index=True, keygen=rom.FULL_TEXT, unique=True)
    room = columns.ManyToOne(ftable="Room", on_delete="cascade")
    messages = columns.OneToMany(ftable="Message")
    is_game_host = columns.Boolean(default=False)
    contact = columns.ManyToOne(ftable="Contact", on_delete="no action")


class Message(Serializable, RedisStorageModel):
    definition = columns.Text()
    word = columns.Text()
    sender = columns.ManyToOne(ftable="Player", on_delete="no action")
    room = columns.ManyToOne(ftable="Room", on_delete="cascade")
    is_canceled = columns.Boolean(default=False)

    def serialize(self):
        data = self.to_dict()
        data["sender"] = self.sender.id
        data.pop("room")
        return data