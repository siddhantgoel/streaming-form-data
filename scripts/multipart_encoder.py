import mimetypes
from argparse import ArgumentParser

from requests_toolbelt import MultipartEncoder


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("-f", "--filename", required=True, help="Data file")
    parser.add_argument(
        "-d",
        "--decode",
        help="Decode output before printing",
        action="store_true",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.filename, "rb") as file_:
        content_type = mimetypes.guess_type(args.filename)[0]

        fields = {
            "name": "hello world",
            "lines": "first line\r\n\r\nsecond line",
            "file": (args.filename, file_, content_type),
        }

        body = MultipartEncoder(fields=fields).to_string()

        if args.decode:
            print(body.decode("utf-8"))
        else:
            print(body)


if __name__ == "__main__":
    main()
