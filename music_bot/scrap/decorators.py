import functools
from music_bot.scrap.models import Song, Artist


def music_model_cached(cache):
    """
    Caching decorator for Song and Artist instances.
    """
    def decorator_cache(func):
        @functools.wraps(func)
        async def wrapper_cache(*args, **kwargs):
            kwargs_copy = dict(kwargs) # kwargs_copy is kwargs -> False
            args_copy = list(args)
            for i, item in enumerate(args_copy):
                if isinstance(item, Artist) or isinstance(item, Song):
                    args_copy[i] = item.name
            for key, value in kwargs_copy.items():
                if isinstance(value, Artist) or isinstance(value, Song):
                    kwargs_copy[key] = value.name
            cache_key = tuple(args_copy) + tuple(kwargs_copy.items())
            if cache_key not in cache:
                cache[cache_key] =  await func(*args, **kwargs)
            return cache[cache_key]
        return wrapper_cache
    return decorator_cache