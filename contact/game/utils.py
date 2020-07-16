import redis
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured


def get_redis_connection(alias="default", write=True) -> redis.StrictRedis:
    """Helper used to obtain raw redis client
    """
    cache = caches[alias]
    if not hasattr(cache, "client"):
        raise ImproperlyConfigured("Redis backend is not installed")

    return cache.client.get_client(write)
