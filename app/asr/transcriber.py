from pathlib import Path

import whisperx


class Transcriber:
    def __init__(
            self,
            model_name: str = 'medium',
            device: str = 'cuda',
            compute_type: str = 'float16',
            batch_size: int = 4,
            language: str = 'ru'
            ):
        self.device = device
        self.batch_size = batch_size
        self.language = language

        print('Loading whisperx model...')

        self.model = whisperx.load_model(
            model_name,
            device,
            compute_type = compute_type,
            language = language,
        )

        print('Whisperx model loaded.')

    def transcribe(self, audio_path: str | Path) -> dict:
        audio_path = str(audio_path)

        # Загружаем аудио
        audio = whisperx.load_audio(audio_path)

        # Распознаём речь
        result = self.model.transcribe(
            audio,
            batch_size = self.batch_size,
        )

        # Загружаем Alignment-модель
        align_model, metadata = whisperx.load_align_model(
            language_code = result['language'],
            device = self.device
        )

        # Уточнаяем временые метки
        aligned_result = whisperx.align(
            result['segments'],
            align_model,
            metadata,
            audio,
            self.device,
            return_char_alignments = False,
        )

        # Собираем текстовый результат
        transcript = "\n".join(
            segment['text'].strip()
            for segment in aligned_result['segments']
        )

        return {
            'language': result['language'],
            'transcript': transcript,
            'segments': result['segments'],
        }


