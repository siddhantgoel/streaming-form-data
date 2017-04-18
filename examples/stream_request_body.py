import os.path
from time import time

from tornado.web import Application, RequestHandler, stream_request_body
from tornado.ioloop import IOLoop

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget, FileTarget


@stream_request_body
class UploadHandler(RequestHandler):
    def prepare(self):
        self.value = ValueTarget()
        self.file_ = FileTarget('/tmp/file-{}.dat'.format(int(time())))

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
    app.listen(9999)

    IOLoop().current().start()


if __name__ == '__main__':
    print('Listening on port 9999')
    main()
