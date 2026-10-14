"""Source-bound self-assessment; no automated medical grading."""

from typing import Literal

from pydantic import Field

from backend.app.schemas import StrictModel


class PracticeItem(StrictModel):
    version: Literal["1"] = "1"
    question: str
    topic: str
    expected_concepts: list[str]
    rubric: list[str]
    source_ids: list[str]
    review_status: Literal["clinical_review_pending"] = "clinical_review_pending"


class StudyRecord(StrictModel):
    topic: str = Field(max_length=200)
    self_assessment: Literal["revisit", "understood"]
    weak_concepts: list[str] = Field(default_factory=list, max_length=10)


def practice(plan, base):
    item = PracticeItem(
        question=f"How would you explain {plan.topic} and its key features?",
        topic=plan.topic,
        expected_concepts=[c["text"] for c in base["claims"]],
        rubric=[
            "Explain the concept in your own words.",
            "Check each claim against the reference answer.",
            "Retain the reference's exceptions and limitations.",
        ],
        source_ids=[c["chunk_id"] for c in base["citations"]],
    )
    return {
        **base,
        "message": "Source-based self-assessment",
        "practice_item": item.model_dump(),
        "answer": item.question
        + "\n\nUse the source-backed answer below as your self-assessment reference. This is not validated automated grading.",
        "task_completion": True,
    }
