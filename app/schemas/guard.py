from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GuardIssue(BaseModel):
    model_config = ConfigDict(extra='forbid')

    severity: Literal['warning', 'error']

    code: str
    path: str
    message: str

    value: str | None = None

class GuardReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    issues: list[GuardIssue] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.saverity == 'error' for issue in self.issues)