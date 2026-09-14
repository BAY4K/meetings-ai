from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import UPLOAD_DIR, OUTPUT_DIR
from app.asr.transcriber import Transcriber
from app.llm.analyzer import Analyzer
from app.services.meeting_pipeline import MeetingPipeline
from app.docx_generator.generator import ProtocolDocxGenerator


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print('Loading ASR model...')

    transcriber = Transcriber()

    print('ASR ready.')

    analyzer = Analyzer()

    docx_generator = ProtocolDocxGenerator()

    pipeline = MeetingPipeline(
        transcriber=transcriber,
        analyzer=analyzer,
        docx_generator=docx_generator,
    )

    app.state.pipeline = pipeline
    app.state.docx_generator = docx_generator

    print("Meeting pipeline ready.")

    yield

    app.state.pipeline = None
    app.state.docx_generator = None

