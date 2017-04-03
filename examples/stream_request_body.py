from tornado.web import stream_request_body, RequestHandler

from streaming_form_data.targets import ValueTarget, FileTarget
from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.part import Part


@stream_request_body
class UploadTarget(RequestHandler):
    def prepare(self):
        self.value = ValueTarget()
        self.file_ = FileTarget('/tmp/image.png')

        expected_parts = (
            Part('name', self.value),
            Part('image', self.file_),
        )

        self._parser = StreamingFormDataParser(
            expected_parts, headers=self.request.headers)

    def data_received(self, chunk):
        self._parser.data_received(chunk)

    def post(self):
        print('name: {}'.format(self.value))
        print('image: {}'.format(self.file_.name))

        self.finish()
