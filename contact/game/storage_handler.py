import functools
import json
import secrets
from typing import Callable, Optional, Tuple

from contact.game.utils import get_redis_connection

redis = get_redis_connection()


def decode_value(value):
    if value is None:
        return ""

    return value.decode()


def deserialize_redis_list(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return list(map(decode_value, func(*args, **kwargs)))

    return wrapper


def get_redis_value(key):
    return decode_value(redis.get(name=key))


@deserialize_redis_list
def get_list(key):
    return redis.lrange(name=key, start=0, end=-1)


@deserialize_redis_list
def get_list_slice(key, start, end):
    return redis.lrange(name=key, start=start, end=end)


def set_value(key, value, expire=None):
    redis.set(name=key, value=value, ex=expire)


def get_value(key):
    return decode_value(redis.get(key))


def exist(key):
    return redis.exists(key)


def list_push(list_key, value):
    redis.rpush(list_key, value)


def delete(*keys):
    redis.delete(*keys)


def add_value_to_set(set_key, value):
    redis.sadd(set_key, value)


def is_in_set(set_key, value):
    value = redis.sismember(name=set_key, value=value)
    return bool(value)


class StorageObjectField:
    name: str

    def __init__(self, default=None, internal=False, null=False, *args, **kwargs):
        self.default = default
        self.internal = internal
        self.null = null
        super().__init__(*args, **kwargs)

    def __get__(self, instance, owner):
        return instance.data[self.name]

    def __set__(self, instance, value):
        instance.data[self.name] = value


class BooleanField(StorageObjectField):
    pass


class StringField(StorageObjectField):
    def __init__(self, default="", *args, **kwargs):
        super().__init__(default, *args, **kwargs)


class IntegerField(StorageObjectField):
    pass


class IdField(StringField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __set__(self, instance, value):
        raise ValueError(
            "It is forbidden to change redis id field. It should be set when"
            "new object is created either automatically or manually"
        )


class RelationKeyField(StringField):
    pass


class ListField(StorageObjectField):
    def __init__(self, *args, **kwargs):
        super().__init__(default=[], *args, **kwargs)


class CalculatedStringField(StringField):
    """
    Calculate value with a given logic by a callback
    This field should be used when its value depends on the values of other fields
    """

    def __init__(self, callback: Callable, *args, **kwargs):
        self.callback = callback
        super().__init__(*args, **kwargs)

    def __set__(self, instance, value):
        raise ValueError(
            "It is forbidden to change redis id field. It should be set when"
            "new object is created either automatically or manually"
        )


class StorageComplexObjectMeta(type):
    def __new__(mcls, name, bases, attrs, **kwargs):
        new_class = super().__new__(mcls, name, bases, attrs, **kwargs)
        descriptors = {
            attr_name: attr
            for attr_name, attr in attrs.items()
            if isinstance(attr, StorageObjectField)
        }
        new_class._default_values = {}
        new_class._calculated_fields = []
        new_class._hidden_values = []

        for attr_name, attr in descriptors.items():
            attr.name = attr_name
            new_class._default_values[attr_name] = attr.default

            if isinstance(attr, IdField):
                new_class.id_field_name = attr_name
            elif isinstance(attr, CalculatedStringField):
                new_class._calculated_fields.append(attr_name)

            if attr.internal:
                new_class._hidden_values.append(attr_name)

            if attr.null:
                new_class._default_values[attr_name] = None

        new_class._StorageComplexObject__descriptors = descriptors
        return new_class


class StorageComplexObject(metaclass=StorageComplexObjectMeta):
    """
    Objects are cached as hash data structures
    described by the classes inheriting from `StorageComplexObject`.
    This class designed to work with `StorageObjectField` inherited types as fields.
    """

    storage_key_prefix: str = ""

    @property
    def storage_key(self):
        return self.get_storage_key(redis_id=self.data[self.id_field_name])

    @classmethod
    def get_storage_key(cls, redis_id):
        return f"{cls.storage_key_prefix}:{redis_id}"

    def __update_calculated_fields(self):
        for calculated_field_name in self._calculated_fields:
            calculated_field_class = self.__descriptors[calculated_field_name]
            self.data[calculated_field_name] = calculated_field_class.callback(self)

    def __update_common_data(self):
        self.common_data = {}
        for attr, value in self.data.items():
            if attr not in self._hidden_values and (value != "" and value is not None):
                self.common_data[attr] = value

    def __update_fields(self):
        self.__update_calculated_fields()
        self.__update_common_data()

    def __init__(self, **kwargs):
        super().__init__()

        self.data = {**self._default_values, **kwargs}

        if not self.data[self.id_field_name]:
            self.data[self.id_field_name] = secrets.token_hex(12)

        self.__update_fields()

    def __serialize_values_for_storage(self) -> dict:
        storage_dict = {}

        for attr_name, field_type in self.__descriptors.items():
            if field_type.null and self.data[attr_name] is None:
                storage_dict[attr_name] = "none"
                continue
            if isinstance(field_type, BooleanField):
                #     if field_type.null and self.data[attr_name] is None:
                #         continue
                storage_dict[attr_name] = int(self.data[attr_name])
            elif isinstance(field_type, ListField):
                storage_dict[attr_name] = json.dumps(self.data[attr_name])
            else:
                storage_dict[attr_name] = self.data[attr_name]

        return storage_dict

    @classmethod
    def __deserialize_values_from_storage(cls, storage_data) -> dict:
        obj_dict = {}

        for key, value in storage_data.items():
            attr_name = key.decode()
            field_type = cls.__descriptors[attr_name]

            if field_type.null and value == "none":
                obj_dict[attr_name] = None
                continue
            if isinstance(field_type, BooleanField):
                obj_dict[attr_name] = bool(int(value))
            elif isinstance(field_type, IntegerField):
                obj_dict[attr_name] = int(value)
            elif isinstance(field_type, ListField):
                try:
                    obj_dict[attr_name] = json.loads(value.decode())
                except json.JSONDecodeError:
                    obj_dict[attr_name] = value.decode()
            else:
                obj_dict[attr_name] = value.decode()

        return obj_dict

    @classmethod
    def get_by_id(cls, obj_id) -> Optional["StorageComplexObject"]:
        redis_key = f"{cls.storage_key_prefix}:{obj_id}"
        redis_values_raw = redis.hgetall(name=redis_key)
        redis_value_processed = cls.__deserialize_values_from_storage(redis_values_raw)

        if not redis_value_processed:
            return None

        return cls(**redis_value_processed)

    @classmethod
    def create_object(cls, **kwargs) -> "StorageComplexObject":
        obj = cls(**kwargs)
        obj.save()
        return obj

    @classmethod
    def get_or_create(cls, obj_id) -> Tuple["StorageComplexObject", bool]:
        """
        Get a stored object using its id or create it if the object
        does not exist in a storage
        """
        obj = cls.get_by_id(obj_id=obj_id)
        created = False

        if obj is None:
            kwargs = {cls.id_field_name: obj_id}
            obj = cls.create_object(**kwargs)
            created = True

        return obj, created

    def refresh(self):
        """
        Refresh python object from the storage. You may want to use this
        method when you know that the object you work with could be
        changed by a different client which causes changes in the state
        of the current object in a storage
        """
        storage_values_raw = redis.hgetall(name=self.storage_key)
        storage_value_processed = self.__deserialize_values_from_storage(
            storage_data=storage_values_raw
        )
        self.data = storage_value_processed
        self.__update_fields()

    def save(self):
        """
        Save and commit changes amended to python object to a storage
        """
        redis_values = self.__serialize_values_for_storage()
        # Since redis 4.0.0 HMSET considered to be deprecated.
        redis.hmset(name=self.storage_key, mapping=redis_values)
        self.__update_calculated_fields()
        self.__update_common_data()

    def _increment_field(self, field_name, by=1):
        redis.hincrby(name=self.storage_key, key=field_name, amount=by)
        self.data[field_name] += by
        self.__update_common_data()
