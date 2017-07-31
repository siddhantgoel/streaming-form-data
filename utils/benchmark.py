from argparse import ArgumentParser
from functools import wraps
from io import StringIO
import cProfile
import pstats

from requests_toolbelt import MultipartEncoder
from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget


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
            stats.print_stats(25)

            print(stream.getvalue())

            return result
        return wrapped
    return decorator


# https://zapier.com/engineering/profiling-python-boss/
try:
    from line_profiler import LineProfiler

    def line_profile(follow=[]):
        def inner(func):
            def profiled_func(*args, **kwargs):
                try:
                    profiler = LineProfiler()
                    profiler.add_function(func)
                    for f in follow:
                        profiler.add_function(f)
                    profiler.enable_by_count()
                    return func(*args, **kwargs)
                finally:
                    profiler.print_stats()
            return profiled_func
        return inner

except ImportError:
    def line_profile(follow=[]):
        "Helpful if you accidentally leave in production!"
        def inner(func):
            def nothing(*args, **kwargs):
                return func(*args, **kwargs)
            return nothing
        return inner


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--content-type', type=str, required=True,
                        help='Content Type of the input file')
    parser.add_argument('-f', '--filename', type=str, required=True,
                        help='File to be uploaded')
    return parser.parse_args()


@c_profile()
def main():
    args = parse_args()

    with open(args.filename, 'rb') as fd:
        encoder = MultipartEncoder(fields={
            'file': ('file', fd, args.content_type)
        })

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.register('file', ValueTarget())

        parser.data_received(encoder.to_string())


if __name__ == '__main__':
    main()
