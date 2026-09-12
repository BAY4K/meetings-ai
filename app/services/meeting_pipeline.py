from pathlib import Path

from app.asr.transcriber import Transcriber
from app.llm.analyzer import Analyzer


class MeetingPipeline:
    def __init__(
            self,
            transcriber: Transcriber,
            analyzer: Analyzer,
    ):
        self.transcriber = transcriber
        self.analyzer = analyzer

    def process(self, audio_path: Path) -> dict:
        # Сначала переводим из аудио в текст
        asr_result = self.transcriber.transcribe(audio_path)

        # Затем обобщаем через Qwen
        extraction = self.analyzer.analyze(
            asr_result['transcript'],
        )

        # Собираем результат
        return {
            'language': asr_result['language'],
            'transcript': asr_result['transcript'],
            'speaker_turns': asr_result['speaker_turns'],
            'extraction': extraction,
        }