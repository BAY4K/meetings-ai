from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProtocolItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    kind: Literal['decision', 'task']

    text: str

    responsible_name: str | None = None
    responsible_speaker: str | None = None
    deadline: str | None = None

    active: bool

    evidence: list[str]


class DiscussionSection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    topic: str

    speaker_name: str | None = None
    speaker_id: str | None = None

    summary: str

    items: list[ProtocolItem]


class MeetingExtraction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    sections: list[DiscussionSection]

    unresolved_questions: list[str]
    ambiguous_fragments: list[str]