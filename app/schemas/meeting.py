from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResolutionItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Текст решения
    text: str
    # Кто исполняет
    responsible_name: str | None = None
    responsible_speaker: str | None = None
    # На какой срок
    deadline: str | None = None



class HeardBlock(BaseModel):
    model_config = ConfigDict(extra='forbid')

    #Докладчик
    speaker_id: str
    speaker_name: str | None = None
    summary: str
    resolutions: list[ResolutionItem] = Field(default_factory=list)

class MeetingExtraction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    heard: list[HeardBlock] = Field(default_factory=list)

    unresolved_questions: list[str] = Field(default_factory=list)
    ambiguous_fragments: list[str] = Field(default_factory=list)