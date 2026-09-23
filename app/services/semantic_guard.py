import re

from app.schemas.guard import (
    GuardIssue,
    GuardReport,
)
from app.schemas.meeting import (
    MeetingExtraction,
)


class SemanticGuard:
    SPEAKER_PATTERN = re.compile(
        r'\bSPEAKER_\d+\b'
    )

    NUMERIC_LITERAL_PATTERN = re.compile(
        r'(?<!\w)'
        r'\d+(?:[.,:]\d+)*'
        r'(?!\w)'
    )

    def validate(
            self,
            transcript: str,
            extraction: MeetingExtraction,
    ) -> GuardReport:
        issues: list[
            GuardIssue
        ] = []

        speakers = set(
            self.SPEAKER_PATTERN.findall(
                transcript
            )
        )

        # NEW:
        # UNKNOWN тоже является допустимым
        # техническим speaker ID,
        # если он реально присутствует
        # в transcript.
        if re.search(
            r'\bUNKNOWN\b',
            transcript,
        ):
            speakers.add(
                'UNKNOWN'
            )

        normalized_transcript = (
            self._normalize_for_search(
                transcript
            )
        )

        # CHANGED:
        # extraction.heard заменён
        # на protocol_blocks.
        for (
            block_index,
            block,
        ) in enumerate(
            extraction.protocol_blocks
        ):
            block_path = (
                f'protocol_blocks['
                f'{block_index}]'
            )

            self._validate_speaker(
                speaker=block.speaker_id,
                speakers=speakers,
                path=(
                    f'{block_path}.'
                    'speaker_id'
                ),
                issues=issues,
            )

            # CHANGED:
            # Проверяем content,
            # а не старый summary.
            self._validate_numeric_literals(
                text=block.content,
                transcript=transcript,
                path=(
                    f'{block_path}.'
                    'content'
                ),
                issues=issues,
            )

            for (
                resolution_index,
                resolution,
            ) in enumerate(
                block.resolutions
            ):
                resolution_path = (
                    f'{block_path}.'
                    f'resolutions['
                    f'{resolution_index}]'
                )

                self._validate_speaker(
                    speaker=(
                        resolution
                        .responsible_speaker
                    ),
                    speakers=speakers,
                    path=(
                        f'{resolution_path}.'
                        'responsible_speaker'
                    ),
                    issues=issues,
                )

                self._validate_deadline(
                    deadline=(
                        resolution.deadline
                    ),
                    normalized_transcript=(
                        normalized_transcript
                    ),
                    path=(
                        f'{resolution_path}.'
                        'deadline'
                    ),
                    issues=issues,
                )

                self._validate_numeric_literals(
                    text=resolution.text,
                    transcript=transcript,
                    path=(
                        f'{resolution_path}.'
                        'text'
                    ),
                    issues=issues,
                )

        # Проверяем служебные места
        # ручной проверки.
        for (
            index,
            item,
        ) in enumerate(
            extraction.manual_review
        ):
            item_path = (
                f'manual_review[{index}]'
            )

            self._validate_speaker(
                speaker=item.speaker_id,
                speakers=speakers,
                path=(
                    f'{item_path}.'
                    'speaker_id'
                ),
                issues=issues,
            )

            self._validate_timestamp(
                timestamp=item.timestamp,
                transcript=transcript,
                path=(
                    f'{item_path}.'
                    'timestamp'
                ),
                issues=issues,
            )

            # Если Qwen переписала сомнительное
            # число в fragment, guard также
            # сможет это заметить.
            self._validate_numeric_literals(
                text=item.fragment,
                transcript=transcript,
                path=(
                    f'{item_path}.'
                    'fragment'
                ),
                issues=issues,
            )

        return GuardReport(
            issues=issues,
        )

    @staticmethod
    def _validate_speaker(
            speaker: str | None,
            speakers: set[str],
            path: str,
            issues: list[GuardIssue],
    ) -> None:
        if speaker is None:
            return

        if speaker in speakers:
            return

        issues.append(
            GuardIssue(
                severity='error',
                code='unknown_speaker',
                path=path,
                value=speaker,
                message=(
                    'Qwen использовал speaker, '
                    'которого нет в transcript.'
                ),
            )
        )

    def _validate_deadline(
            self,
            deadline: str | None,
            normalized_transcript: str,
            path: str,
            issues: list[GuardIssue],
    ) -> None:
        if deadline is None:
            return

        normalized_deadline = (
            self._normalize_for_search(
                deadline
            )
        )

        if (
            normalized_deadline
            in normalized_transcript
        ):
            return

        issues.append(
            GuardIssue(
                severity='error',
                code='unsupported_deadline',
                path=path,
                value=deadline,
                message=(
                    'Срок не найден дословно '
                    'в исходной расшифровке.'
                ),
            )
        )

    # NEW:
    # Таймкод manual_review должен
    # реально существовать в transcript.
    @staticmethod
    def _validate_timestamp(
            timestamp: str,
            transcript: str,
            path: str,
            issues: list[GuardIssue],
    ) -> None:
        value = (
            timestamp
            .strip()
            .strip('[]')
        )

        expected = (
            f'[{value}]'
        )

        if expected in transcript:
            return

        issues.append(
            GuardIssue(
                severity='error',
                code=(
                    'unsupported_timestamp'
                ),
                path=path,
                value=timestamp,
                message=(
                    'Таймкод ручной проверки '
                    'не найден в transcript.'
                ),
            )
        )

    def _validate_numeric_literals(
            self,
            text: str,
            transcript: str,
            path: str,
            issues: list[GuardIssue],
    ) -> None:
        values = (
            self
            .NUMERIC_LITERAL_PATTERN
            .findall(text)
        )

        for value in values:
            if value in transcript:
                continue

            issues.append(
                GuardIssue(
                    severity='error',
                    code=(
                        'unsupported_numeric_value'
                    ),
                    path=path,
                    value=value,
                    message=(
                        'Числовое значение '
                        'не найдено в transcript.'
                    ),
                )
            )

    @staticmethod
    def _normalize_for_search(
            text: str,
    ) -> str:
        text = (
            text
            .lower()
            .replace('ё', 'е')
        )

        text = re.sub(
            r'[^\w.:]+',
            ' ',
            text,
        )

        return re.sub(
            r'\s+',
            ' ',
            text,
        ).strip()