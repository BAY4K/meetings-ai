import gc
import os
from pathlib import Path
from typing import overload

import pandas as pd
import torch
from pyannote.audio import Pipeline
import whisperx


class Transcriber:
    def __init__(
            self,
            model_name: str = 'large-v3',
            device: str = 'cuda',
            diarization_device: str = 'cuda',
            diarization_model: str = (
                "pyannote/speaker-diarization-community-1"
            ),
            compute_type: str = 'float16',
            batch_size: int = 1,
            language: str = 'ru',
            vad_onset: float = 0.35,
            vad_offset: float = 0.25,
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

        #Запуск модели для диаризации
        self.diarize_model = Pipeline.from_pretrained(
            self.diarization_model,
            token=hf_token,
        )

        self.diarize_model.to(
            torch.device(diarization_device)
        )

        print('ASR pipeline ready...')

    def transcribe(
            self,
            audio_path: str | Path,
            *,
            num_speakers: int | None = None,
            hotwords: str | None = None,
            initial_prompt: str | None = None,
    ) -> dict:
        audio_path = str(audio_path)

        # Загружаем аудио
        audio = whisperx.load_audio(audio_path)

        asr_options = {
            'beam_size': 5,
            'condition_on_previous_text': False,
            'initial_prompt': initial_prompt,
            'hotwords': hotwords,
            'suppress_numerals': False,
        }

        print('Loading WhisperX model...')

        model = whisperx.load_model(
            self.model_name,
            self.device,
            compute_type=self.compute_type,
            language=self.language,
            asr_options=asr_options,
            vad_options={
                'vad_onset': self.vad_onset,
                'vad_offset': self.vad_offset,
                'chunk_size': 30,
            },
        )

        try:
            # Распознаём речь
            result = model.transcribe(
                audio,
                batch_size = self.batch_size,
            )

            raw_segments = result['segments']
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

        diarize_segments = (
            self._run_diarization(
                audio,
                num_speakers=num_speakers,
            )
        )

        # Сопоставляем спикеров со словами
        result_with_speakers = (
            whisperx.assign_word_speakers(
                diarize_segments,
                aligned_result,
                fill_nearest=True
            )
        )



        self._add_speaker_overlap_info(
            result_with_speakers['segments'],
            diarize_segments
        )

        self._repair_leading_boundary_words(
            result_with_speakers['segments'],
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
            'raw_segments': raw_segments,
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

    @staticmethod
    def _add_speaker_overlap_info(
            segments: list[dict],
            diarization
    ):
        for segment in segments:
            for word in segment.get('words', []):
                start = word.get('start')
                end = word.get('end')

                if start is None or end is None:
                    continue

                word_duration = end - start

                if word_duration <= 0:
                    continue

                overlaps = {}

                for _, row in diarization.iterrows():
                    intersection = (
                        min(end, row['end'])
                        - max(start, row['start'])
                    )

                    if intersection <= 0:
                        continue

                    speaker = row['speaker']

                    overlaps[speaker] = (
                        overlaps.get(speaker, 0) + intersection
                    )

                ranked = sorted(
                    overlaps.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )

                if not ranked:
                    word['speaker_uncertain'] = True
                    continue

                best_speaker, best_overlap = ranked[0]

                second_overlap = (
                    ranked[1][1]
                    if len(ranked) > 1
                    else 0
                )

                best_share = (
                    best_overlap / word_duration
                )

                second_share = (
                    second_overlap / word_duration
                )

                word['speaker_overlap'] = (
                    round(best_share, 3)
                )

                word['speaker_margin'] = round(
                    best_share-second_share,
                    3
                )

                word['speaker_uncertain'] = (
                    second_share > 0
                    and (
                        best_share
                        - second_share
                    ) < 0.35
                )

    @staticmethod
    def _repair_speaker_boundaries(
            segments: list[dict],
    ):
        words = []

        for segment in segments:
            words.extend(
                segment.get('words', [])
            )
        for index in range(1, len(words) - 1):
            word = words[index]

            if not word.get('speaker_uncertain', False):
                continue

            previous = words[index - 1]
            following = words[index + 1]

            current_speaker = word.get('speaker')
            previous_speaker = previous.get('speaker')
            following_speaker = following.get('speaker')

            if(
                previous_speaker
                and previous_speaker
                == following_speaker
                and current_speaker
                != previous_speaker
            ):
                word['speaker'] = (
                    previous_speaker
                )

    @staticmethod
    def _repair_sentence_end_boundaries(
            segments: list[dict],
    ):
        words = []
        for segment in segments:
            words.extend(
                segment.get('words', [])
            )

        for index in range(1, len(words) - 1):
            word = words[index]
            previous = words[index - 1]

            if not word.get('speaker_uncertain', False):
                continue

            text = word.get('word', '').strip()

            if not text.endswith(('.','!','?')):
                continue

            current_speaker = word.get('speaker')
            previous_speaker = previous.get('speaker')

            if(
                not previous_speaker
                or previous_speaker
                == current_speaker
            ):
                continue

            previous_text = previous.get('word', '').strip()

            if previous_text.endswith(('.','!','?')):
                continue

            word['speaker'] = (
                previous_speaker
            )

    def _repair_leading_boundary_words(
            self,
            segments: list[dict],
            margin_threshold: float = 0.25,
    ) -> None:
        words = []

        for segment in segments:
            for word in segment.get('words', []):
                words.append(word)

        for index in range(1, len(words) - 1):
            word = words[index]
            previous = words[index - 1]
            following = words[index + 1]

            current_speaker = word.get('speaker')
            previous_speaker = previous.get('speaker')
            following_speaker = following.get('speaker')

            if (
                    not current_speaker
                    or not previous_speaker
                    or current_speaker == previous_speaker
            ):
                continue

            margin = word.get('speaker_margin')

            if (
                    margin is None
                    or margin >= margin_threshold
            ):
                continue

            text = word.get('word', '').strip()
            previous_text = previous.get('word', '').strip()

            # Нас интересует слово,
            # которое завершает предыдущую фразу.
            if not text.endswith(('.', '!', '?')):
                continue

            # Предыдущая фраза уже закончилась —
            # значит переносить ничего не надо.
            if previous_text.endswith(('.', '!', '?')):
                continue

            # Следующее слово должно принадлежать
            # текущему speaker. Это означает,
            # что мы переносим только первое
            # пограничное слово, а не всю реплику.
            if following_speaker != current_speaker:
                continue

            word['speaker'] = previous_speaker
            word['speaker_repaired'] = True

    #Метод для распределения слов по ролям(разбивание реплик)
    @staticmethod
    def _build_speakers_turn(segments: list[dict]) -> list[dict]:
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

    def _run_diarization(
            self,
            audio: str,
            *,
            num_speakers: int | None = None,
    ):
        audio_data = {
            'waveform': torch.from_numpy(
                audio[None, :],
            ),
            'sample_rate': 16000,
        }

        if num_speakers is not None:
            output = self.diarize_model(
                audio_data,
                num_speakers=num_speakers,
            )
        else:
            output = self.diarize_model(
                audio_data,
                min_speakers=2,
                max_speakers=4,
            )

        diarization = (output.exclusive_speaker_diarization)

        return self._diarization_to_dataframe(diarization)

    @staticmethod
    def _diarization_to_dataframe(diarization) -> pd.DataFrame:
        rows = []

        for segment, _, speaker in (
                diarization.itertracks(
                    yield_label=True
                )
        ):
            rows.append({
                'segment' : segment,
                'speaker' : speaker,
                'start' : segment.start,
                'end' : segment.end,
            })

        return pd.DataFrame(rows)

    # Метод для составления удобной структуры диалога для Qwen
    @staticmethod
    def _build_transcript(turns: list[dict]) -> str:
        lines = []

        for turn in turns:
            start = turn["start"] or 0
            speaker = turn["speaker"]
            text = turn["text"]

            lines.append(
                f"[{start:2f}] {speaker}: {text}"
            )

        return "\n".join(lines)