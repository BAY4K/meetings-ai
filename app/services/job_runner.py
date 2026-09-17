import traceback
from pathlib import Path

from app.services.job_store import (
    JobStore,
)
from app.services.meeting_pipeline import (
    MeetingPipeline,
)


class JobRunner:
    def __init__(
            self,
            pipeline: MeetingPipeline,
            job_store: JobStore,
    ):
        self.pipeline = pipeline
        self.job_store = job_store

    def run(
            self,
            *,
            job_id: str,
            original_name: str,
            audio_path: Path,
            output_path: Path,
            num_speakers: int | None,
    ) -> None:

        self.job_store.mark_running(
            job_id
        )

        def on_stage(
                stage: str,
                message: str,
        ) -> None:
            self.job_store.update_stage(
                job_id,
                stage=stage,
                message=message,
            )

        try:
            result = self.pipeline.process(
                audio_path,
                output_path,
                num_speakers=num_speakers,
                on_stage=on_stage,
            )

            job_result = {
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
                    f'/download/{job_id}',
            }

            self.job_store.complete(
                job_id,
                result=job_result,
            )

        except Exception as exc:
            traceback.print_exc()

            self.job_store.fail(
                job_id,
                error=str(exc),
            )