from datetime import datetime, timezone
from typing import  Any, Literal
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

JobStatus = Literal[
    'queued',
    'running',
    'completed',
    'failed',
]

class ProcessingJob(BaseModel): # Состояние одной задачи обработки.
    model_config = ConfigDict(extra='forbid')
    job_id: str
    filename: str
    status: JobStatus = 'queued'
    stage: str = 'Задача ожидает запуска.'
    result: dict[str, Any] | None = None
    error: str | None = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)