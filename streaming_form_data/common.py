from functools import wraps
from io import StringIO
import cProfile
import pstats


def c_profile(sort_by='cumulative'):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()

            result = func(*args, **kwargs)

            profiler.disable()

            stream = StringIO()
            stats = pstats.Stats(profiler, stream=stream).sort_stats(sort_by)
            stats.print_stats()

            print(stream.getvalue())

            return result
        return wrapped
    return decorator
