from typing import Literal

from pydantic import Field

from backend.app.schemas import StrictModel


class DatasetManifest(StrictModel):
    name: str
    source_url: str
    revision: str | None = None
    license: str | None = None
    rights_state: Literal["unknown", "verified", "blocked"] = "unknown"
    license_evidence_sha256: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    declared_counts: dict[str, int] = Field(default_factory=dict)
    observed_count: int | None = Field(None, ge=0)
    observed_splits: dict[str, int] = Field(default_factory=dict)
    sample_unit: str = "unknown"
    class_schema: list[str] = Field(default_factory=list)
    class_histogram: dict[str, int] = Field(default_factory=dict)
    missing_rates: dict[str, float] = Field(default_factory=dict)
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    human_review_count: int | None = Field(None, ge=0)
    augmentation_lineage: list[dict] = Field(default_factory=list)
    source_hashes: dict[str, str] = Field(default_factory=dict)
    language: str | None = None
    not_acquired_reason: str | None = None

    def require_action(self, action):
        if self.rights_state != "verified" or not self.license_evidence_sha256 or action not in self.allowed_actions:
            raise ValueError(f"verified artifact-specific rights for {action} required")


class HoldoutManifest(StrictModel):
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["sealed", "development_exposed"] = "sealed"
    exposure_events: list[dict[str, str]] = Field(default_factory=list)

    @property
    def unseen(self):
        return self.status == "sealed" and not self.exposure_events

    def record_exposure(self, reason, timestamp):
        if not reason.strip() or not timestamp.strip():
            raise ValueError("exposure reason and timestamp required")
        self.exposure_events.append({"reason": reason, "timestamp": timestamp})
        self.status = "development_exposed"
