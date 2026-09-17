from pathlib import Path

from app.asr.transcriber import Transcriber
from app.llm.analyzer import Analyzer
from app.docx_generator.generator import ProtocolDocxGenerator
from app.services.semantic_guard import SemanticGuard


class MeetingPipeline:
    def __init__(
            self,
            transcriber: Transcriber,
            analyzer: Analyzer,
            docx_generator: ProtocolDocxGenerator,
            semantic_guard: SemanticGuard | None = None,
    ):
        self.transcriber = transcriber
        self.analyzer = analyzer
        self.docx_generator = docx_generator

        self.semantic_guard = semantic_guard or SemanticGuard()


    def process(
            self,
            audio_path: Path,
            output_path: Path,
            *,
            num_speakers: int | None = None,
    ) -> dict:
        # Сначала переводим из аудио в текст
        asr_result = self.transcriber.transcribe(audio_path, num_speakers=num_speakers)
        transcription = asr_result['transcript']

        # Затем обобщаем через Qwen
        extraction = self.analyzer.analyze(transcription)

        guard_report =self.semantic_guard.validate(
            transcript=transcription,
            extraction=extraction,
        )

        # Генерируем DOCX.
        docx_path = self.docx_generator.generate(
            extraction=extraction,
            output_path=output_path,
        )

        # Собираем результат
        return {
            'language': asr_result['language'],
            'transcript': transcription,
            'speaker_turns': asr_result['speaker_turns'],
            'extraction': extraction,
            'guard': guard_report.model_dump(),
            'docx_path': docx_path,
        }