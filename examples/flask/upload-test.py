#!/usr/bin/python3

from flask import Flask, request
import time
import os
import tempfile

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget

app = Flask(__name__)

page = '''
<!doctype html>
<title>Upload new File</title>
<h1>Upload new File</h1>
<form method=post enctype=multipart/form-data id="upload-file">
  <input type=file name=file>
  <input type=submit value=Upload>
</form><br>
'''


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = FileTarget(os.path.join(tempfile.gettempdir(), "test"))

        hdict = {}
        for h in request.headers:
            hdict[h[0]] = h[1]

        parser = StreamingFormDataParser(headers=hdict)

        parser.register('file', file)

        timeA = time.perf_counter()
        while True:
            chunk = request.stream.read(8192)
            if not chunk:
                break
            parser.data_received(chunk)
        timeB = time.perf_counter()
        print("time spent on file reception: %fs" % (timeB-timeA))
        return "upload done"
    return page


if __name__ == '__main__':
    app.run(host='0.0.0.0')
