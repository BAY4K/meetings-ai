from pathlib import Path
from uuid import uuid4
import aiofiles

from fastapi import (
    APIRouter, UploadFile, File, HTTPException, Request
)
from starlette.concurrency import run_in_threadpool

from app.core.config import ALLOWED_EXTENSIONS, UPLOAD_DIR, OUTPUT_DIR


router = APIRouter(
    tags=["processing"],
)

async def _save_audio_file(file: UploadFile) -> tuple[str, Path]:
    original_name = Path(file.filename or '').name

    if not original_name:
        raise HTTPException(
            status_code=400,
            detail="File name is missing",
        )

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

    return original_name, file_path


@router.post("/process")
async def process(
        request: Request,
        file: UploadFile = File(),
):
    original_name, file_path = (await _save_audio_file(file))

    file_id = uuid4().hex

    output_path = (
            OUTPUT_DIR
            / f'{file_id}.docx'
    )

    result = await run_in_threadpool(
        request.app.state.pipeline.process,
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