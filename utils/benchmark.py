from argparse import ArgumentParser
from functools import wraps
from io import StringIO
import cProfile
import pstats

from requests_toolbelt import MultipartEncoder
from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.part import Part
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


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--content-type', type=str, required=True)
    parser.add_argument('-f', '--filename', type=str, required=True)
    return parser.parse_args()


@c_profile()
def main():
    args = parse_args()

    with open(args.filename, 'rb') as fd:
        encoder = MultipartEncoder(fields={
            'file': ('file', fd, args.content_type)
        })

        expected_parts = (Part('file', ValueTarget()),)

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())


if __name__ == '__main__':
    main()
