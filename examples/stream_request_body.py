import os.path

from tornado.web import stream_request_body, RequestTarget

from streaming_form_data.targets import ValueTarget, FileTarget
from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.part import Part


@stream_request_body
class UploadTarget(RequestTarget):
    def prepare(self):
        expected_parts = (
            Part('name', ValueTarget()),
            Part('image', FileTarget(os.path.join('/tmp', 'image.png'))),
        )

        self._parser = StreamingFormDataParser(expected_parts,
                                               headers=self.request.headers)

    def data_received(self, chunk):
        self._parser.data_received(chunk)

    def post(self):
        self.finish()
