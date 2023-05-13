import os.path
import tempfile
from time import time

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, stream_request_body


one_hundred_gb = 100 * 1024 * 1024 * 1024


@stream_request_body
class UploadHandler(RequestHandler):
    def prepare(self):
        self.request.connection.set_max_body_size(one_hundred_gb)

        name = "uploaded-file-tornado-{}.dat".format(int(time()))

        self.value = ValueTarget()
        self.file_ = FileTarget(os.path.join(tempfile.gettempdir(), name))

        self._parser = StreamingFormDataParser(headers=self.request.headers)

        self._parser.register("name", self.value)
        self._parser.register("file", self.file_)

    def data_received(self, chunk):
        self._parser.data_received(chunk)

    def post(self):
        self.render("upload.html", name=self.value.value, filename=self.file_.filename)


class IndexHandler(RequestHandler):
    def get(self):
        self.render("index.html")


def main():
    handlers = [(r"/", IndexHandler), (r"/upload", UploadHandler)]

    settings = {"debug": True, "template_path": os.path.dirname(__file__)}

    app = Application(handlers, **settings)
    app.listen(9999, address="localhost")

    IOLoop().current().start()


if __name__ == "__main__":
    print("Listening on localhost:9999")
    main()
