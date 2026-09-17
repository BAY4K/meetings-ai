from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import UPLOAD_DIR, OUTPUT_DIR
from app.core.settings import settings
from app.asr.transcriber import Transcriber
from app.llm.analyzer import Analyzer
from app.services.meeting_pipeline import MeetingPipeline
from app.docx_generator.generator import ProtocolDocxGenerator
from app.services.job_runner import JobRunner
from app.services.job_store import JobStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print('Loading ASR model...')

    transcriber = Transcriber(
        model_name=settings.asr.model_name,
        device=settings.asr.device,
        diarization_device=(
            settings.asr.diarization_device
        ),
        diarization_model=(
            settings.asr.diarization_model
        ),
        compute_type=settings.asr.compute_type,
        batch_size=settings.asr.batch_size,
        language=settings.asr.language,
        vad_onset=settings.asr.vad_onset,
        vad_offset=settings.asr.vad_offset,
    )

    print('ASR ready.')

    analyzer = Analyzer(
        model_name=settings.llm.model_name,
        base_url=settings.llm.base_url,
        timeout=settings.llm.timeout,
        num_ctx=settings.llm.num_ctx,
    )

    docx_generator = ProtocolDocxGenerator()

    pipeline = MeetingPipeline(
        transcriber=transcriber,
        analyzer=analyzer,
        docx_generator=docx_generator,
    )

    #Хранилище всех состояний
    job_store = JobStore()
    # Объект, который запускает pipeline и обновляет JobStore.
    job_runner = JobRunner(
        pipeline=pipeline,
        job_store=job_store,
    )

    app.state.pipeline = pipeline
    app.state.docx_generator = docx_generator
    app.state.job_store = job_store
    app.state.job_runner = job_runner

    print("Meeting pipeline ready.")

    yield

    app.state.pipeline = None
    app.state.docx_generator = None
    app.state.job_store = None
    app.state.job_runner = None
