import gc
import os

from copy import deepcopy
from pathlib import Path
from collections.abc import Callable

import numpy as np
import pandas as pd
import torch
import whisperx

from pyannote.audio import Pipeline


StageCallback = Callable[
    [str, str],
    None,
]

class Transcriber:
    SAMPLE_RATE = 16_000

    DEFAULT_MIN_SPEAKERS = 2
    DEFAULT_MAX_SPEAKERS = 4

    # Только диагностический порог.
    # Сам по себе speaker с margin < 0.35
    # ещё не исправляется.
    SPEAKER_UNCERTAIN_MARGIN = 0.35

    # Более строгий порог именно
    # для автоматического boundary repair.
    BOUNDARY_REPAIR_MARGIN = 0.25


    def __init__(
            self,
            model_name: str = 'large-v3',
            device: str = 'cuda',
            diarization_device: str = 'cuda',
            diarization_model: str = (
                'pyannote/'
                'speaker-diarization-community-1'
            ),
            compute_type: str = 'float16',
            batch_size: int = 1,
            language: str = 'ru',
            vad_onset: float = 0.35,
            vad_offset: float = 0.25,
    ):
        self.model_name = model_name
        self.device = device

        self.diarization_device = (
            diarization_device
        )

        self.diarization_model = (
            diarization_model
        )

        self.compute_type = compute_type
        self.batch_size = batch_size
        self.language = language

        self.vad_onset = vad_onset
        self.vad_offset = vad_offset

        hf_token = os.getenv('HF_TOKEN')

        print('Loading diarization model...')

        # Сам pipeline создаём один раз.
        # На CUDA он будет переноситься
        # непосредственно перед diarization.
        self.diarize_model = (
            Pipeline.from_pretrained(
                self.diarization_model,
                token=hf_token,
            )
        )

        print('ASR pipeline ready.')


    def transcribe(
            self,
            audio_path: str | Path,
            *,
            num_speakers: int | None = None,
            hotwords: str | None = None,
            initial_prompt: str | None = None,
            on_stage: StageCallback | None = None,
    ) -> dict:
        audio_path = str(audio_path)

        if (
            num_speakers is not None
            and num_speakers < 1
        ):
            raise ValueError(
                'num_speakers must be >= 1'
            )

        # Декодируем аудио один раз.
        audio = whisperx.load_audio(
            audio_path
        )

        asr_options = {
            'beam_size': 5,
            'condition_on_previous_text': False,
            'initial_prompt': initial_prompt,
            'hotwords': hotwords,
            'suppress_numerals': False,
        }

        self._notify_stage(
            on_stage,
            stage='transcribing',
            message='Распознавание речи...',
        )

        print('Loading WhisperX model...')


        model = whisperx.load_model(
            self.model_name,
            self.device,
            compute_type=self.compute_type,
            language=self.language,
            asr_options=asr_options,
            vad_options={
                'vad_onset':
                    self.vad_onset,
                'vad_offset':
                    self.vad_offset,
                'chunk_size': 30,
            },
        )

        try:
            result = model.transcribe(
                audio,
                batch_size=self.batch_size,
            )

            raw_segments = deepcopy(
                result['segments']
            )

        finally:
            # Освобождаем память
            del model
            self._clear_cuda()

        print('WhisperX model released.')

        # Запускаем выравнивание

        self._notify_stage(
            on_stage,
            stage='aligning',
            message='Выравнивание текста...',
        )

        print('Loading alignment model...')

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
                return_char_alignments=False,
            )

        finally:
            # Освобождаем память
            del align_model
            del align_metadata

            self._clear_cuda()

        print('Alignment model released.')

        # Запуск диаризации

        self._notify_stage(
            on_stage,
            stage='diarizing',
            message='Определение участников...',
        )

        diarize_segments = (
            self._run_diarization(
                audio,
                num_speakers=num_speakers,
            )
        )


        # Соотносим слова к спикерам

        result_with_speakers = (
            whisperx.assign_word_speakers(
                diarize_segments,
                aligned_result,

                # В наших тестах это
                # хорошо убрало UNKNOWN.
                fill_nearest=True,
            )
        )

        # Проверка на подозрительные участки

        self._add_speaker_overlap_info(
            result_with_speakers[
                'segments'
            ],
            diarize_segments,
        )

        # Исправление подозрительных участков

        self._repair_leading_boundary_words(
            result_with_speakers[
                'segments'
            ]
        )

        # Создаём очередь как при диалоге

        speaker_turns = (
            self._build_speaker_turns(
                result_with_speakers[
                    'segments'
                ]
            )
        )

        transcript = self._build_transcript(
            speaker_turns
        )

        # Записываем результат

        response = {
            'language': result['language'],
            'transcript': transcript,

            'speaker_turns':
                speaker_turns,

            # Полезно для диагностики:
            # что услышал Whisper до
            # alignment + diarization.
            'raw_segments':
                raw_segments,

            # Здесь уже word timestamps,
            # speaker, margin и информация
            # об automatic repair.
            'segments':
                result_with_speakers[
                    'segments'
                ],
        }

        # Оптимизация и очистка

        del audio
        del aligned_result
        del diarize_segments
        del result_with_speakers
        del result

        self._clear_cuda()

        return response


    def _run_diarization(
            self,
            audio: np.ndarray,
            *,
            num_speakers: int | None = None,
    ) -> pd.DataFrame:
        """
        Запускает pyannote Community-1.

        Если точное число участников известно,
        используем num_speakers.

        Иначе используем auto-режим 2..4.
        """

        audio_data = {
            'waveform': torch.from_numpy(
                audio[None, :]
            ),
            'sample_rate':
                self.SAMPLE_RATE,
        }

        target_device = torch.device(
            self.diarization_device
        )

        # Модель хранится между запросами,
        # но на GPU переносится только
        # непосредственно перед diarization.
        self.diarize_model.to(
            target_device
        )

        try:
            if num_speakers is not None:
                output = self.diarize_model(
                    audio_data,
                    num_speakers=num_speakers,
                )

            else:
                output = self.diarize_model(
                    audio_data,
                    min_speakers=(
                        self.DEFAULT_MIN_SPEAKERS
                    ),
                    max_speakers=(
                        self.DEFAULT_MAX_SPEAKERS
                    ),
                )

            # Community-1 имеет специальный
            # exclusive-вариант, удобный
            # для объединения с ASR timestamps.
            diarization = (
                output
                .exclusive_speaker_diarization
            )

            dataframe = (
                self._diarization_to_dataframe(
                    diarization
                )
            )

            del diarization
            del output

            return dataframe

        finally:
            # Сразу после transcribe запускается Qwen,
            # поэтому не оставляем pyannote
            # занимать VRAM.
            if target_device.type == 'cuda':
                self.diarize_model.to(
                    torch.device('cpu')
                )

                self._clear_cuda()


    @staticmethod
    def _diarization_to_dataframe(
            diarization,
    ) -> pd.DataFrame:
        rows = []

        for (
            segment,
            _,
            speaker,
        ) in diarization.itertracks(
            yield_label=True
        ):
            rows.append({
                'segment':
                    segment,

                'speaker':
                    speaker,

                'start':
                    segment.start,

                'end':
                    segment.end,
            })

        return pd.DataFrame(rows)


    @classmethod
    def _add_speaker_overlap_info(
            cls,
            segments: list[dict],
            diarization: pd.DataFrame,
    ) -> None:
        """
        Для каждого слова считаем,
        насколько уверенно его timestamp
        относится к выбранному speaker.

        Это диагностика, а не самостоятельное
        исправление speaker.
        """

        for segment in segments:
            for word in segment.get(
                    'words',
                    []
            ):
                start = word.get('start')
                end = word.get('end')

                if (
                    start is None
                    or end is None
                ):
                    continue

                word_duration = (
                    end - start
                )

                if word_duration <= 0:
                    continue

                overlaps: dict[
                    str,
                    float
                ] = {}

                for _, row in (
                    diarization.iterrows()
                ):
                    intersection = (
                        min(
                            end,
                            row['end']
                        )
                        -
                        max(
                            start,
                            row['start']
                        )
                    )

                    if intersection <= 0:
                        continue

                    speaker = row['speaker']

                    overlaps[speaker] = (
                        overlaps.get(
                            speaker,
                            0.0
                        )
                        +
                        intersection
                    )

                ranked = sorted(
                    overlaps.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )

                if not ranked:
                    # fill_nearest мог назначить
                    # speaker, даже если прямого
                    # overlap не было.
                    word[
                        'speaker_uncertain'
                    ] = True

                    continue

                (
                    best_speaker,
                    best_overlap,
                ) = ranked[0]

                second_overlap = (
                    ranked[1][1]
                    if len(ranked) > 1
                    else 0.0
                )

                best_share = (
                    best_overlap
                    / word_duration
                )

                second_share = (
                    second_overlap
                    / word_duration
                )

                margin = (
                    best_share
                    - second_share
                )

                word[
                    'speaker_best_overlap'
                ] = best_speaker

                word[
                    'speaker_overlap'
                ] = round(
                    best_share,
                    3,
                )

                word[
                    'speaker_margin'
                ] = round(
                    margin,
                    3,
                )

                word[
                    'speaker_uncertain'
                ] = (
                    second_share > 0
                    and margin
                    < cls.SPEAKER_UNCERTAIN_MARGIN
                )


    @classmethod
    def _repair_leading_boundary_words(
            cls,
            segments: list[dict],
    ) -> None:
        """
        Исправляет только очень узкий
        тип недочёта, когда текст утекает другому спикеру.

        Перенос возможен только если:
        - speaker сменился;
        - слово имеет низкий margin;
        - оно завершает предложение;
        - предыдущее слово предложение
          не завершало;
        - следующее слово остаётся
          у нового speaker.
        """

        words = []

        for segment in segments:
            words.extend(
                segment.get(
                    'words',
                    []
                )
            )

        for index in range(
                1,
                len(words) - 1,
        ):
            previous = words[
                index - 1
            ]

            word = words[index]

            following = words[
                index + 1
            ]

            current_speaker = (
                word.get('speaker')
            )

            previous_speaker = (
                previous.get('speaker')
            )

            following_speaker = (
                following.get('speaker')
            )

            if (
                not current_speaker
                or not previous_speaker
            ):
                continue

            # Никакой смены speaker нет.
            if (
                current_speaker
                == previous_speaker
            ):
                continue

            margin = word.get(
                'speaker_margin'
            )

            if (
                margin is None
                or margin
                >= cls.BOUNDARY_REPAIR_MARGIN
            ):
                continue

            text = (
                word.get(
                    'word',
                    ''
                )
                .strip()
            )

            previous_text = (
                previous.get(
                    'word',
                    ''
                )
                .strip()
            )

            # Текущее слово должно заканчивать предложение.
            if not text.endswith(
                ('.', '!', '?')
            ):
                continue

            # Если предыдущее слово уже завершило предложение, то продолжения предыдущей реплики нет.
            if previous_text.endswith(
                ('.', '!', '?')
            ):
                continue

            # После сомнительного слова новый speaker должен продолжать свою реплику.
            if (
                following_speaker
                != current_speaker
            ):
                continue

            # Для аудита сохраняем, что именно изменила наша эвристика.
            word[
                'speaker_original'
            ] = current_speaker

            word[
                'speaker'
            ] = previous_speaker

            word[
                'speaker_repaired'
            ] = True

            word[
                'speaker_repair_reason'
            ] = (
                'leading_boundary_word'
            )


    @staticmethod
    def _build_speaker_turns(
            segments: list[dict],
    ) -> list[dict]:
        """
        Группирует последовательные слова
        одного speaker в цельные реплики.
        """

        turns = []

        current_speaker = None
        current_words = []

        start_time = None
        end_time = None

        for segment in segments:
            for word in segment.get(
                    'words',
                    []
            ):
                text = (
                    word.get(
                        'word',
                        ''
                    )
                    .strip()
                )

                if not text:
                    continue

                speaker = word.get(
                    'speaker',
                    'UNKNOWN',
                )

                if (
                    speaker
                    != current_speaker
                ):
                    if current_words:
                        turns.append({
                            'speaker':
                                current_speaker,

                            'start':
                                start_time,

                            'end':
                                end_time,

                            'text':
                                ' '.join(
                                    current_words
                                ),
                        })

                    current_speaker = (
                        speaker
                    )

                    current_words = []

                    start_time = (
                        word.get('start')
                    )

                current_words.append(
                    text
                )

                word_end = word.get(
                    'end'
                )

                if word_end is not None:
                    end_time = word_end

        if current_words:
            turns.append({
                'speaker':
                    current_speaker,

                'start':
                    start_time,

                'end':
                    end_time,

                'text':
                    ' '.join(
                        current_words
                    ),
            })

        return turns


    @staticmethod
    def _build_transcript(
            turns: list[dict],
    ) -> str:
        """
        Компактный transcript,
        который затем получает Qwen.
        """

        lines = []

        for turn in turns:
            start = (
                turn['start']
                or 0.0
            )

            speaker = (
                turn['speaker']
                or 'UNKNOWN'
            )

            text = turn['text']

            lines.append(
                f'[{start:.2f}] '
                f'{speaker}: '
                f'{text}'
            )

        return '\n'.join(lines)

    @staticmethod
    def _clear_cuda() -> None:
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @staticmethod
    def _notify_stage(
            callback: StageCallback | None,
            *,
            stage: str,
            message: str,
    ) -> None:
        """
        Сообщает внешнему pipeline, какой ASR-этап сейчас выполняется.
        Transcriber ничего не знает о FastAPI, JobStore или frontend.
        """

        if callback is None:
            return

        callback(
            stage,
            message,
        )