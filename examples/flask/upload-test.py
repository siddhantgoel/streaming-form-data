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
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery.form/4.2.2/jquery.form.min.js"></script>
<title>Upload new File</title>
<h1>Upload new File</h1>
<form method=post enctype=multipart/form-data id="upload-file">
  <input type=file name=file>
  <input type=submit value=Upload>
</form><br>
<div id="msg"/>
<script>
$(function() {
    var timestamp;
    $('#upload-file').ajaxForm({
        beforeSend: function() {
            timestamp = performance.now();
            $("#msg").html("starting upload<br>")
        },
        complete: function(xhr) {
            $("#msg").append(xhr.responseText + "<br>")
            $("#msg").append("time spent on file transmission: " + (performance.now()-timestamp) / 1000 + "s")
        }
    });
});
</script>
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
