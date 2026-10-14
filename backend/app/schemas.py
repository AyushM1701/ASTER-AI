from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal[
    "ok",
    "partial",
    "needs_confirmation",
    "insufficient_evidence",
    "urgent_guidance",
    "unsupported_input",
    "quality_rejected",
    "busy",
    "error",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Claim(StrictModel):
    text: str = Field(min_length=1, max_length=1500)
    citation_ids: list[str] = Field(min_length=1, max_length=5)


class GeneratedAnswer(StrictModel):
    claims: list[Claim] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(default_factory=list, max_length=5)


class ConversationalAnswer(StrictModel):
    answer: str = Field(min_length=1, max_length=6000)
    deeper_explanation: str = Field(default="", max_length=6000)


class AttachmentClassification(StrictModel):
    kind: Literal["prescription", "xray", "other", "uncertain"]
    reason: str = Field(min_length=1, max_length=400)


class HandwritingTranscription(StrictModel):
    style: Literal["printed", "handwritten", "mixed", "uncertain"]
    raw_text: str = Field(max_length=12000)
    uncertain_line_numbers: list[int] = Field(default_factory=list, max_length=200)

    @field_validator("uncertain_line_numbers")
    @classmethod
    def valid_lines(cls, value):
        if any(n < 0 or n > 199 for n in value) or len(value) != len(set(value)):
            raise ValueError("Uncertainty lines must be unique nonnegative indices")
        return value


class ChatRequest(StrictModel):
    question: str = Field(min_length=1, max_length=4000)
    audience: Literal["understand", "study", "research"] = "understand"
    task_explicit: bool = False
    context_id: str | None = Field(None, max_length=80)
    expected_revision: int | None = Field(None, ge=0)
    viva_question_id: str | None = Field(None, min_length=1, max_length=80)

    @field_validator("question")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("Enter a question")
        return value.strip()


class RevisionRequest(StrictModel):
    expected_revision: int = Field(ge=0)


class ConfirmedField(StrictModel):
    field_id: str = Field(min_length=1, max_length=80)
    value: str | None = Field(None, max_length=12000)
    status: Literal["confirmed_by_user", "unreadable"]

    @field_validator("value")
    @classmethod
    def trim(cls, value, info):
        if value is not None and info.data.get("field_id") != "document_text" and len(value) > 500:
            raise ValueError("Medication fields are limited to 500 characters")
        return value.strip() or None if value is not None else None


class Confirmation(RevisionRequest):
    fields: list[ConfirmedField] = Field(min_length=1, max_length=100)
    confirmation_acknowledged: Literal[True]


class XrayRequest(StrictModel):
    asset_id: str = Field(min_length=1, max_length=80)
    question: str = Field("", max_length=4000)
