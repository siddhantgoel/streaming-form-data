import os.path
import tempfile
from time import time

import bottle
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget


bottle.TEMPLATE_PATH = [os.path.join(os.path.dirname(__file__), "templates")]


@bottle.route("/")
@bottle.view("index.html")
def root_page():
    return {}


@bottle.post("/upload")
@bottle.view("upload.html")
def upload_page():
    name = "uploaded-file-tornado-{}.dat".format(int(time()))

    value = ValueTarget()
    file_ = FileTarget(os.path.join(tempfile.gettempdir(), name))

    parser = StreamingFormDataParser(headers=bottle.request.headers)

    parser.register("name", value)
    parser.register("file", file_)

    while True:
        chunk = bottle.request.environ["wsgi.input"].read(8192)
        if not chunk:
            break
        parser.data_received(chunk)

    return {"name": value.value, "filename": file_.filename}


if __name__ == "__main__":
    bottle.run(
        app=bottle.app(),
        server="paste",
        host="localhost",
        port=9000,
        debug=True,
    )
