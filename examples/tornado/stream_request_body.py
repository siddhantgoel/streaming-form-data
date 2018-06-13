import os.path
import tempfile
from time import time

from tornado.web import Application, RequestHandler, stream_request_body
from tornado.ioloop import IOLoop

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget, FileTarget


@stream_request_body
class UploadHandler(RequestHandler):
    def prepare(self):
        gigabyte = 1024 * 1024 * 1024
        self.request.connection.set_max_body_size(100 * gigabyte)
        self.value = ValueTarget()
        name = 'uploaded-file-tornado-{}.dat'.format(int(time()))
        self.file_ = FileTarget(os.path.join(tempfile.gettempdir(), name))

        self._parser = StreamingFormDataParser(headers=self.request.headers)

        self._parser.register('name', self.value)
        self._parser.register('file', self.file_)

    def data_received(self, chunk):
        self._parser.data_received(chunk)

    def post(self):
        self.render('upload.html', name=self.value.value,
                    filename=self.file_.filename)


class IndexHandler(RequestHandler):
    def get(self):
        self.render('index.html')


def main():
    handlers = [
        (r'/', IndexHandler),
        (r'/upload', UploadHandler),
    ]

    settings = dict(
        debug=True,
        template_path=os.path.dirname(__file__)
    )

    app = Application(handlers, **settings)
    app.listen(9999, address='localhost')

    IOLoop().current().start()


if __name__ == '__main__':
    print('Listening on localhost:9999')
    main()
