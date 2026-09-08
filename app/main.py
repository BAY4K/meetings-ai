from email import message

import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}

app = FastAPI()

@app.get("/")
def root():
    return FileResponse("app/static/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File()):
    extensions = Path(file.filename).suffix.lower()

    if extensions not in ALLOWED_EXTENSIONS:
        return {
            "error": "Unsupported file type"
        }

    file_path = UPLOAD_DIR / file.filename

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return {
        "message": "Uploaded file",
        "filename": file.filename,
        "filepath": file_path,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)