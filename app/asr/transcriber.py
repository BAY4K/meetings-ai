import gc
import os
from pathlib import Path

import torch
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
            language: str = 'ru',
            vad_onset: float = 0.5,
            vad_offset: float = 0.363,
            ):
        self.model_name = model_name
        self.device = device
        self.diarization_device = diarization_device
        self.diarization_model = diarization_model
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.language = language

        self.vad_onset = vad_onset
        self.vad_offset = vad_offset

        hf_token = os.getenv('HF_TOKEN')

        print('Loading diarization model...')

        #Запуск модели whisperx
        self.diarize_model = DiarizationPipeline(
            model_name=diarization_model,
            token=hf_token,
            device=self.diarization_device,
        )

        print('ASR pipeline ready...')

    def transcribe(self, audio_path: str | Path) -> dict:
        audio_path = str(audio_path)

        # Загружаем аудио
        audio = whisperx.load_audio(audio_path)

        print('Loading WhisperX model...')

        model = whisperx.load_model(
            self.model_name,
            self.device,
            compute_type=self.compute_type,
            language=self.language,
        )

        try:
            # Распознаём речь
            result = model.transcribe(
                audio,
                batch_size = self.batch_size,
            )
        finally:
            del model
            self._clear_cuda()

        print('WhisperX model released.')

        print('Loading alignment model...')

        # Запускаем модель выравнивания
        align_model, align_metadata = (
            whisperx.load_align_model(
                language_code=self.language,
                device=self.device,
            )
        )

        try:
            aligned_result = whisperx.align(
                result['segments'],
                align_model,
                align_metadata,
                audio,
                self.device,
                return_char_alignments = False,
            )
        finally:
            del align_model
            del align_metadata

            self._clear_cuda()

        print('Alignment model released.')

        # Разбиваем на спикеров
        diarize_segments = self.diarize_model(
            audio_path,
            min_speakers=2,
            max_speakers=4,
        )

        # Сопоставляем спикеров со словами
        result_with_speakers = (
            whisperx.assign_word_speakers(
                diarize_segments,
                aligned_result,
            )
        )

        # Конвертация формата whisperx к нужному нам формату
        speaker_turns = (
            self._build_speakers_turn(
                result_with_speakers['segments']
            )
        )

        transcript = self._build_transcript(speaker_turns)

        response = {
            "language" : result['language'],
            "transcript" : transcript,
            'speaker_turns' : speaker_turns,
            'segments' : (result_with_speakers['segments']),
        }

        del audio
        del aligned_result
        del diarize_segments
        del result_with_speakers
        del result

        self._clear_cuda()

        return response

    @staticmethod
    def _clear_cuda():
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

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