from typing import Literal

from pydantic import BaseModel, ConfigDict


class DecisionSection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    text: str
    status: Literal['active', 'superseded', 'cancelled']
    evidence: list[str]


class Task(BaseModel):
    model_config = ConfigDict(extra='forbid')

    text: str
    responsible_name: str | None = None
    responsible_speaker: str | None = None
    deadline: str | None = None
    status: Literal['accepted', 'cancelled']
    evidence: str


class DiscussionSection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    topic: str

    speaker_name: str | None = None
    speaker_id: str | None = None

    summary: str

    description: list[DecisionSection]
    tasks: list[Task]


class MeetingExtraction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    sections: list[DiscussionSection]

    unresolved_questions: list[str]
    ambiguous_fragments: list[str]