import traceback
from pathlib import Path

import httpx
import torch

from pydantic import ValidationError

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
            hotwords: str | None = None,
    ) -> None:

        self.job_store.mark_running(
            job_id
        )

        current_stage = 'starting'

        def on_stage(
                stage: str,
                message: str,
        ) -> None:
            nonlocal current_stage

            current_stage = stage

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
                hotwords=hotwords,
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
            # Полная техническая ошибка
            # остаётся в терминале разработчика.
            traceback.print_exc()

            # Пользователю отдаём короткое
            # и понятное сообщение.
            public_message = (
                self._get_public_error_message(
                    exc,
                    stage=current_stage,
                )
            )

            self.job_store.fail(
                job_id,
                error=public_message,
            )

        finally:
            # NEW 8.5 CLEANUP:
            #
            # Загруженное аудио нужно только
            # пока выполняется pipeline.
            #
            # Удаляем его и после успеха,
            # и после любой ошибки.
            self._cleanup_audio(
                audio_path
            )

    @staticmethod
    def _get_public_error_message(
            exc: Exception,
            *,
            stage: str,
    ) -> str:
        """
        Превращает технические исключения
        в понятные сообщения для UI.

        Traceback при этом остаётся
        в терминале.
        """

        # Ollama не запущена или
        # указанный host недоступен.
        if isinstance(
            exc,
            httpx.ConnectError,
        ):
            return (
                'Не удалось подключиться к Ollama. '
                'Проверьте, что локальный сервер '
                'Ollama запущен.'
            )

        # Qwen отвечает слишком долго.
        if isinstance(
            exc,
            httpx.TimeoutException,
        ):
            return (
                'Превышено время ожидания '
                'ответа от Ollama.'
            )

        # Ollama ответила HTTP-ошибкой:
        # например 404 / 500.
        if isinstance(
            exc,
            httpx.HTTPStatusError,
        ):
            return (
                'Ollama вернула ошибку '
                'при анализе встречи.'
            )

        # Qwen вернула JSON, который
        # не соответствует MeetingExtraction.
        if isinstance(
            exc,
            ValidationError,
        ):
            return (
                'Модель вернула результат '
                'в некорректном формате.'
            )

        # Не хватает VRAM.
        if isinstance(
            exc,
            torch.cuda.OutOfMemoryError,
        ):
            return (
                'Недостаточно памяти GPU '
                'для обработки записи.'
            )

        # Для ошибок ASR обычно нельзя
        # надёжно определить конкретную причину,
        # поэтому используем stage.
        if stage in {
            'transcribing',
            'aligning',
            'diarizing',
        }:
            return (
                'Не удалось обработать аудиозапись. '
                'Проверьте файл и повторите попытку.'
            )

        if stage == 'analyzing':
            return (
                'Не удалось выполнить '
                'анализ встречи.'
            )

        if stage == 'validating':
            return (
                'Не удалось проверить '
                'результат анализа.'
            )

        if stage == 'generating_docx':
            return (
                'Не удалось создать DOCX.'
            )

        return (
            'Во время обработки произошла ошибка.'
        )

    @staticmethod
    def _cleanup_audio(
            audio_path: Path,
    ) -> None:
        """
        Удаляет временный загруженный audio.

        missing_ok=True означает:
        если файла уже нет — это не ошибка.
        """

        try:
            audio_path.unlink(
                missing_ok=True
            )

            print(
                'Временный аудиофайл удалён:',
                audio_path,
            )

        except OSError as exc:
            # Cleanup не должен превращать
            # успешную обработку в failed job.
            print(
                'Невозможно удалить '
                'временный аудиофайл:',
                exc,
            )