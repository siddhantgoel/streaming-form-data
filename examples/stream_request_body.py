import os.path
from time import time

from tornado.web import Application, RequestHandler, stream_request_body
from tornado.ioloop import IOLoop

from streaming_form_data import StreamingFormDataParser, Part
from streaming_form_data.targets import ValueTarget, FileTarget


@stream_request_body
class UploadHandler(RequestHandler):
    def prepare(self):
        self.value = ValueTarget()
        self.file_ = FileTarget('/tmp/file-{}.dat'.format(int(time())))

        expected_parts = (
            Part('name', self.value),
            Part('file', self.file_),
        )

        self._parser = StreamingFormDataParser(
            expected_parts, headers=self.request.headers)

    def data_received(self, chunk):
        self._parser.data_received(chunk)

    def post(self):
        print('name: {}'.format(self.value.value))
        print('file: {}'.format(self.file_.filename))

        self.finish()


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
    app.listen(9999)

    IOLoop().current().start()


if __name__ == '__main__':
    print('Listening on port 9999')
    main()
