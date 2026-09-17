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
        issues: list[GuardIssue] = []

        speakers = set(
            self.SPEAKER_PATTERN.findall(
                transcript
            )
        )

        normalized_transcript = (
            self._normalize_for_search(
                transcript
            )
        )

        for block_index, block in enumerate(
            extraction.heard
        ):
            block_path = (
                f'heard[{block_index}]'
            )

            self._validate_speaker(
                speaker=block.speaker_id,
                speakers=speakers,
                path=f'{block_path}.speaker_id',
                issues=issues,
            )

            self._validate_numeric_literals(
                text=block.summary,
                transcript=transcript,
                path=f'{block_path}.summary',
                issues=issues,
            )

            for resolution_index, resolution in enumerate(
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
                    deadline=resolution.deadline,
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
                        f'{resolution_path}.text'
                    ),
                    issues=issues,
                )

        for index, text in enumerate(
            extraction.unresolved_questions
        ):
            self._validate_numeric_literals(
                text=text,
                transcript=transcript,
                path=(
                    f'unresolved_questions[{index}]'
                ),
                issues=issues,
            )

        for index, text in enumerate(
            extraction.ambiguous_fragments
        ):
            self._validate_numeric_literals(
                text=text,
                transcript=transcript,
                path=(
                    f'ambiguous_fragments[{index}]'
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
                    'Qwen использовал SPEAKER, '
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

    def _validate_numeric_literals(
            self,
            text: str,
            transcript: str,
            path: str,
            issues: list[GuardIssue],
    ) -> None:
        values = (
            self.NUMERIC_LITERAL_PATTERN
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