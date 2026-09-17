from threading import Lock

from app.schemas.jobs import (
    ProcessingJob,
    utc_now,
)


class JobStore:
    def __init__(self):
        self._jobs: dict[
            str,
            ProcessingJob
        ] = {}

        self._lock = Lock()

    def create(
            self,
            *,
            job_id: str,
            filename: str,
    ) -> ProcessingJob:
        job = ProcessingJob(
            job_id=job_id,
            filename=filename,
        )

        with self._lock:
            self._jobs[job_id] = job

        return job.model_copy(
            deep=True
        )

    def get(
            self,
            job_id: str,
    ) -> ProcessingJob | None:
        with self._lock:
            job = self._jobs.get(
                job_id
            )

            if job is None:
                return None

            # Не отдаём наружу сам объект,
            # который хранится внутри store.
            return job.model_copy(
                deep=True
            )

    def mark_running(
            self,
            job_id: str,
    ) -> None:
        with self._lock:
            job = self._get_required(
                job_id
            )

            job.status = 'running'
            job.stage = 'starting'
            job.message = (
                'Обработка запускается...'
            )
            job.updated_at = utc_now()

    def update_stage(
            self,
            job_id: str,
            *,
            stage: str,
            message: str,
    ) -> None:
        with self._lock:
            job = self._get_required(
                job_id
            )

            job.status = 'running'
            job.stage = stage
            job.message = message
            job.updated_at = utc_now()

    def complete(
            self,
            job_id: str,
            *,
            result: dict,
    ) -> None:
        with self._lock:
            job = self._get_required(
                job_id
            )

            job.status = 'completed'
            job.stage = 'completed'
            job.message = (
                'Обработка завершена.'
            )

            job.result = result
            job.error = None
            job.updated_at = utc_now()

    def fail(
            self,
            job_id: str,
            *,
            error: str,
    ) -> None:
        with self._lock:
            job = self._get_required(
                job_id
            )

            job.status = 'failed'
            job.stage = 'failed'
            job.message = (
                'Не удалось обработать запись.'
            )

            job.error = error
            job.updated_at = utc_now()

    def _get_required(
            self,
            job_id: str,
    ) -> ProcessingJob:
        job = self._jobs.get(
            job_id
        )

        if job is None:
            raise KeyError(
                f'Unknown job: {job_id}'
            )

        return job