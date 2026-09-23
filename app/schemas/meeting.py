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


class ProtocolBlock(BaseModel):
    model_config = ConfigDict(extra='forbid')

    #Докладчик
    speaker_id: str
    speaker_name: str | None = None
    content: str
    resolutions: list[ResolutionItem] = Field(default_factory=list)


class ManualReviewItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    timestamp: str
    speaker_id: str
    # Исходный сомнительный фрагмент.
    fragment: str
    # Тип проверки ограничиваем
    # вариантами из промпта.
    check_type: Literal[
        'ФИО',
        'число',
        'дата',
        'срок',
        'подразделение',
        'организация',
        'оборудование',
        'технический термин',
        'неразборчивая речь',
        'возможная ошибка диаризации',
    ]


class MeetingExtraction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    protocol_blocks: list[ProtocolBlock] = Field(default_factory=list)
    manual_review: list[ManualReviewItem] = Field(default_factory=list)