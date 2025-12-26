import os
import tempfile
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from streaming_form_data import AsyncStreamingFormDataParser
from streaming_form_data.targets import AsyncFileTarget, AsyncValueTarget

app = FastAPI()

@app.get("/")
async def index():
    # Serve the simple HTML form
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <title>FastAPI Streaming Upload</title>
        </head>
        <body>
            <h1>Upload a file (FastAPI)</h1>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <label>Name: <input type="text" name="name"></label><br><br>
                <label>File: <input type="file" name="file"></label><br><br>
                <input type="submit" value="Upload">
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/upload")
async def upload(request: Request):
    # Determine where to save the file
    filename = f"uploaded-file-fastapi-{int(time.time())}.dat"
    filepath = os.path.join(tempfile.gettempdir(), filename)

    # Define targets
    # AsyncValueTarget keeps the data in memory
    name_target = AsyncValueTarget()
    
    # AsyncFileTarget streams data to disk using aiofiles
    file_target = AsyncFileTarget(filepath)

    # Initialize the Async parser with request headers
    parser = AsyncStreamingFormDataParser(headers=request.headers)

    # Register targets
    parser.register("name", name_target)
    parser.register("file", file_target)

    # Iterate over the request stream asynchronously
    async for chunk in request.stream():
        await parser.data_received(chunk)

    # Render a response
    content = f"""
    <!DOCTYPE html>
    <html>
        <head><title>Upload Successful</title></head>
        <body>
            <h2>Upload Successful!</h2>
            <p><strong>Name:</strong> {name_target.value.decode('utf-8')}</p>
            <p><strong>Saved File:</strong> {file_target.multipart_filename}</p>
            <p><strong>Local Path:</strong> {filepath}</p>
            <br>
            <a href="/">Go back</a>
        </body>
    </html>
    """
    return HTMLResponse(content=content)

if __name__ == "__main__":
    import uvicorn
    print("Listening on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)