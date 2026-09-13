from pathlib import Path
from contextlib import asynccontextmanager
from uuid import uuid4
import aiofiles

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.asr.transcriber import Transcriber

from app.llm.analyzer import Analyzer
from app.services.meeting_pipeline import MeetingPipeline
from app.docx.generator import ProtocolDocxGenerator


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Loading ASR model...')

    app.state.transcriber = Transcriber()

    print('ASR ready...')

    app.state.analyzer = Analyzer()

    app.state.docx_generator = ProtocolDocxGenerator()

    app.state.pipeline = MeetingPipeline(
        transcriber=app.state.transcriber,
        analyzer=app.state.analyzer,
        docx_generator=app.state.docx_generator,
    )

    yield

    app.state.transcriber = None

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return FileResponse("app/static/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File()):
    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only mp3, wav, and m4a are supported.",
        )

    stored_name = f'{uuid4().hex}{extension}'
    file_path = UPLOAD_DIR / stored_name

    async with aiofiles.open(file_path, mode="wb") as output:
        while chunk := await file.read(1024 * 1024):
            await output.write(chunk)

    result = await run_in_threadpool(
        app.state.transcriber.transcribe,
        file_path,
    )

    return  {
        'filename': original_name,
        'language': result['language'],
        'transcript': result['transcript'],
        'speaker_turns': result['speaker_turns'],
    }

@app.post("/process")
async def process(file: UploadFile = File()):
    original_name = Path(file.filename).name

    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only mp3, wav, and m4a are supported.",
        )

    stored_name = f'{uuid4().hex}{extension}'
    file_path = UPLOAD_DIR / stored_name

    async with aiofiles.open(file_path, mode="wb") as output:
        while chunk := await file.read(1024 * 1024):
            await output.write(chunk)

    file_id = uuid4().hex

    output_path = (
            OUTPUT_DIR
            / f'{file_id}.docx'
    )

    result = await run_in_threadpool(
        app.state.pipeline.process,
        file_path,
        output_path
    )

    return {
        'filename': original_name,
        'language': result['language'],
        'transcript': result['transcript'],
        'speaker_turns': result['speaker_turns'],
        'extraction': result['extraction'].model_dump(),
        'download_url': f'/download/{file_id}',
    }

@app.get("/download/{file_id}")
async def download(file_id: str):
    if (
        len(file_id) != 32
        or not all(
            char in '0123456789abcdef'
            for char in file_id
        )
    ):
        raise HTTPException(
            status_code=404,
            detail="Invalid file ID.",
        )

    file_path = OUTPUT_DIR / f'{file_id}.docx'

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    return FileResponse(
        str(file_path),
        media_type=(
            'application/'
            'vnd.openxmlformats-officedocument.'
            'wordprocessingml.document'
        ),
        filename='result.docx',
    )


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)