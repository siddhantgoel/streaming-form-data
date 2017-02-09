import os.path

from tornado.web import stream_request_body, RequestHandler

from streaming_form_data.delegates import ValueDelegate, FileDelegate
from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.part import Part


@stream_request_body
class UploadHandler(RequestHandler):
    def prepare(self):
        expected_parts = (
            Part('name', ValueDelegate()),
            Part('image', FileDelegate(os.path.join('/tmp', 'image.png'))),
        )

        self._parser = StreamingFormDataParser(expected_parts)

    def data_received(self, chunk):
        self._parser.data_received(chunk)

    def post(self):
        self.finish()
