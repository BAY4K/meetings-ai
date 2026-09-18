from functools import partial
from pathlib import Path
from uuid import uuid4

import aiofiles

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
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

def _validate_num_speakers(num_speakers: int | None) -> None:
    if (
        num_speakers is not None
        and num_speakers
        not in {2, 3, 4}
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                'Количество участников должно быть: Авто, 2, 3 или 4.'
            ),
        )

# LEGACY
@router.post("/process")
async def process(
        request: Request,
        file: UploadFile = File(),
        num_speakers: int | None = Form(default=None),
        hotwords: str | None = Form(
            default=None
        ),
):
    _validate_num_speakers(num_speakers)
    original_name, file_path = (await _save_audio_file(file))

    file_id = uuid4().hex

    output_path = (
            OUTPUT_DIR
            / f'{file_id}.docx'
    )

    pipeline_call = partial(
        request.app.state.pipeline.process,
        file_path,
        output_path,
        num_speakers=num_speakers,
        hotwords=hotwords,
    )

    try:
        result = await run_in_threadpool(
            pipeline_call
        )

        return {
            'filename':
                original_name,

            'language':
                result['language'],

            'transcript':
                result['transcript'],

            'speaker_turns':
                result['speaker_turns'],

            'extraction':
                result[
                    'extraction'
                ].model_dump(),

            'guard':
                result['guard'],

            'download_url':
                f'/download/{file_id}',
        }

    finally:
        # Cleanup legacy endpoint.
        file_path.unlink(
            missing_ok=True
        )

@router.post('/process/jobs', status_code=202)
async def create_processing_job(
        request: Request,
        background_tasks: BackgroundTasks,

        file: UploadFile = File(),

        num_speakers: int | None = Form(
            default=None
        ),
        hotwords: str | None = Form(
            default=None
        ),
):
    _validate_num_speakers(num_speakers)

    original_name, file_path = (
        await _save_audio_file(
            file
        )
    )

    # Один ID используем одновременно
    # для job и готового DOCX.
    job_id = uuid4().hex

    output_path = (
        OUTPUT_DIR
        / f'{job_id}.docx'
    )

    # Сразу регистрируем job.
    job = (
        request.app.state
        .job_store
        .create(
            job_id=job_id,
            filename=original_name,
        )
    )

    if hotwords is not None:
        hotwords = hotwords.strip()

        if not hotwords:
            hotwords = None

    # BackgroundTasks запускает sync JobRunner после того,
    # как HTTP response уже отправлен.
    # То есть клиенту не надо ждать Whisper + Qwen несколько минут.
    background_tasks.add_task(
        request.app.state.job_runner.run,
        job_id=job_id,
        original_name=original_name,
        audio_path=file_path,
        output_path=output_path,
        num_speakers=num_speakers,
        hotwords=hotwords,
    )

    return {
        'job_id':
            job.job_id,
        'status':
            job.status,
        'stage':
            job.stage,
        'message':
            job.message,
        'status_url':
            (
                f'/process/jobs/'
                f'{job.job_id}'
            ),
    }

# Чтение текущего состояния job.
@router.get('/process/jobs/{job_id}')
async def get_processing_job(
        request: Request,
        job_id: str,
):
    job = (
        request.app.state
        .job_store
        .get(job_id)
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail='Processing job not found.',
        )

    # mode='json' преобразует datetime
    # в JSON-friendly ISO строки.
    return job.model_dump(
        mode='json'
    )