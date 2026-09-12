from pathlib import Path

from app.asr.transcriber import Transcriber
from app.llm.analyzer import Analyzer
from app.docx.generator import ProtocolDocxGenerator


class MeetingPipeline:


    def __init__(
            self,
            transcriber: Transcriber,
            analyzer: Analyzer,
            docx_generator: ProtocolDocxGenerator,
    ):
        self.transcriber = transcriber
        self.analyzer = analyzer
        self.docx_generator = docx_generator


    def process(
            self,
            audio_path: Path,
            output_path: Path,
    ) -> dict:
        # Сначала переводим из аудио в текст
        asr_result = self.transcriber.transcribe(audio_path)

        # Затем обобщаем через Qwen
        extraction = self.analyzer.analyze(
            asr_result['transcript'],
        )

        docx_path = self.docx_generator.generate(
            extraction=extraction,
            output_path=output_path,
        )

        # Собираем результат
        return {
            'language': asr_result['language'],
            'transcript': asr_result['transcript'],
            'speaker_turns': asr_result['speaker_turns'],
            'extraction': extraction,
            'docx_path': docx_path,
        }