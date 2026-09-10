import os
from pathlib import Path

import whisperx
from whisperx.diarize import DiarizationPipeline


class Transcriber:
    def __init__(
            self,
            model_name: str = 'medium',
            device: str = 'cuda',
            diarization_device: str = 'cpu',
            diarization_model: str = (
                "pyannote/speaker-diarization-community-1"
            ),
            compute_type: str = 'float16',
            batch_size: int = 4,
            language: str = 'ru'
            ):
        self.device = device
        self.diarization_device = diarization_device
        self.diarization_model = diarization_model
        self.batch_size = batch_size
        self.language = language

        hf_token = os.getenv('HF_TOKEN')

        # if not hf_token:
        #     raise RuntimeError(
        #         "HF_TOKEN is not set"
        #         "It is required for speaker diarization"
        #     )

        print('Loading whisperx model...')

        #Запуск модели whisperx
        self.model = whisperx.load_model(
            model_name,
            device,
            compute_type = compute_type,
            language = language,
        )

        print('Loading alignment model...')

        #Запуск русской модели выравнивания данных
        self.align_model, self.align_metadata = (
            whisperx.load_align_model(
                language_code = language,
                device = device,
            )
        )

        print("Loading diarization model...")

        #Запуск разделения речи по спикерам
        self.diarize_model = DiarizationPipeline(
            model_name=diarization_model,
            token=hf_token,
            device=self.diarization_device,
        )

        print("ASR pipeline ready.")

    def transcribe(self, audio_path: str | Path) -> dict:
        audio_path = str(audio_path)

        # Загружаем аудио
        audio = whisperx.load_audio(audio_path)

        # Распознаём речь
        result = self.model.transcribe(
            audio,
            batch_size = self.batch_size,
        )

        # Запускаем выравнивание текста
        aligned_result = whisperx.align(
            result['segments'],
            self.align_model,
            self.align_metadata,
            audio,
            self.device,
            return_char_alignments = False,
        )

        # Разбиваем на спикеров
        diarize_segments = self.diarize_model(
            audio_path,
            min_speakers=3,
            max_speakers=4,
        )

        # Сопоставляем спикеров со словами
        result_with_speakers = whisperx.assign_word_speakers(
            diarize_segments,
            aligned_result,
        )

        # Конвертация формата whisperx к нужному нам формату
        speaker_turns = self._build_speakers_turn(
            result_with_speakers['segments']
        )

        transcript = self._build_transcript(speaker_turns)

        return {
            "language" : result['language'],
            "transcript" : transcript,
            'speaker_turns' : speaker_turns,
            'segments' : result_with_speakers['segments'],
        }

    #Метод для распределения слов по ролям(разбивание реплик)
    def _build_speakers_turn(self, segments: list[dict]) -> list[dict]:
        turns = []

        current_speaker = None
        current_words = []
        start_time = None
        end_time = None

        for segment in segments:
            for word in segment.get('words', []):
                text = word.get('word', '').strip()

                if not text:
                    continue

                speaker = word.get('speaker', 'UNKNOWN')

                if speaker != current_speaker:
                    if current_words:
                        turns.append({
                            'speaker' : current_speaker,
                            'start' : start_time,
                            'end' : end_time,
                            'text': " ".join(current_words),
                        })

                    current_speaker = speaker
                    current_words = []
                    start_time = word.get('start')

                current_words.append(text)
                end_time = word.get('end')

        if current_words:
            turns.append({
                'speaker' : current_speaker,
                'start' : start_time,
                'end' : end_time,
                'text': " ".join(current_words),
            })

        return turns

    # Метод для составления удобной структуры диалога для Qwen
    def _build_transcript(self, turns: list[dict]) -> str:
        lines = []

        for turn in turns:
            start = turn["start"] or 0
            speaker = turn["speaker"]
            text = turn["text"]

            lines.append(
                f"[{start:2f}] {speaker}: {text}"
            )

        return "\n".join(lines)