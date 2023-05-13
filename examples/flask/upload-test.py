#!/usr/bin/python3

import os
import tempfile
import time
from textwrap import dedent

from flask import Flask, request

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget


app = Flask(__name__)


page = dedent(
    """
    <!doctype html>
    <head>
        <title>Upload new File</title>
    </head>
    <body>
        <h1>Upload new File</h1>
        <form method="post" enctype="multipart/form-data" id="upload-file">
          <input type="file" name="file">
          <input type="submit" value="Upload">
        </form>
    </body>
    """
)


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file_ = FileTarget(os.path.join(tempfile.gettempdir(), "test"))

        parser = StreamingFormDataParser(headers=request.headers)

        parser.register("file", file_)

        time_start = time.perf_counter()

        while True:
            chunk = request.stream.read(8192)
            if not chunk:
                break
            parser.data_received(chunk)

        time_finish = time.perf_counter()

        response = dedent(
            """
            <!doctype html>
            <head>
                <title>Done!</title>
            </head>
            <body>
                <h1>
                    {file_name} ({content_type}): upload done
                </h1>
                <h2>
                    Time spent on file reception: {duration}s
                </h2>
            </body>
        """.format(
                file_name=file_.multipart_filename,
                content_type=file_.multipart_content_type,
                duration=(time_finish - time_start),
            )
        )

        return response
    return page


if __name__ == "__main__":
    app.run(host="0.0.0.0")
