"""
Development server to print out the raw request body to the console
"""

from flask import Flask, request, render_template_string

app = Flask(__name__)

html = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Files</title>
</head>
<body>
    <h1>Upload Files</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <label for="file">Choose files:</label>
        <input type="file" id="file" name="files" multiple>
        <button type="submit">Upload</button>
    </form>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(html)


@app.route("/upload", methods=["POST"])
def upload():
    print(request.get_data(as_text=True))

    return "OK", 200


if __name__ == "__main__":
    app.run(debug=True)
