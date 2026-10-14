import hashlib
from pathlib import Path

import yaml

from backend.app.errors import AppError, envelope
from backend.app.services.policy import check_policy
from backend.app.services.uploads import decode_image, quality_measurements


def validate_asset(asset, settings):
    required = {
        "asset_id",
        "path",
        "sha256",
        "source",
        "license",
        "view",
        "adult",
        "supported_input_review",
        "deidentified",
        "partition",
        "patient_group",
    }
    if not required <= set(asset):
        raise AppError(422, "unsupported_input", "Curated asset provenance is incomplete.")
    if (
        asset["view"] not in {"AP", "PA"}
        or asset["adult"] is not True
        or asset["deidentified"] is not True
        or asset["supported_input_review"] is not True
        or not asset["license"]
        or not asset["source"]
    ):
        raise AppError(
            422,
            "unsupported_input",
            "Only reviewed, permitted adult frontal chest images are supported.",
        )
    path = Path(asset["path"])
    if not path.is_absolute():
        path = (settings.xray_manifest.parent / path).resolve()
    if not path.is_file() or path.stat().st_size > settings.max_upload_bytes:
        raise AppError(
            422, "unsupported_input", "Curated asset is missing or exceeds the byte limit."
        )
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != asset["sha256"]:
        raise AppError(
            422, "unsupported_input", "Curated asset hash changed. Review and register it again."
        )
    image, preview = decode_image(data, settings, xray=True)
    measurements = quality_measurements(image)
    if (
        min(image.size) < 224
        or not 0.65 <= measurements["aspect_ratio"] <= 1.55
        or measurements["dynamic_range"] < 30
    ):
        raise AppError(422, "quality_rejected", "Curated image failed the technical image checks.")
    return image, preview, measurements


class XrayService:
    def __init__(self, settings, compute, references):
        self.settings, self.compute, self.references = settings, compute, references
        self.assets = {}
        self.adapter = None
        self.setup_error = None
        try:
            manifest = yaml.safe_load(settings.xray_manifest.read_text(encoding="utf-8"))
            for asset in manifest.get("assets", []):
                if asset["asset_id"] in self.assets:
                    raise ValueError("Duplicate asset ID")
                validate_asset(asset, settings)
                self.assets[asset["asset_id"]] = asset
        except (OSError, KeyError, TypeError, ValueError, AppError):
            self.assets = {}
            self.setup_error = "Curated image manifest unavailable or invalid."
        if settings.enable_xray:
            try:
                from backend.app.adapters.xray_model import XrayAdapter

                self.adapter = XrayAdapter(settings)
            except (ImportError, OSError, ValueError, RuntimeError, KeyError):
                self.setup_error = (
                    "Cached X-ray weights or optional dependencies are unavailable or invalid."
                )

    def health(self):
        return {
            "available": self.adapter is not None and bool(self.assets),
            "enabled": self.settings.enable_xray,
            "registered_assets": len(self.assets),
            "note": self.setup_error
            or (
                "Ready for curated research inference."
                if self.adapter and self.assets
                else "Requires verified weights and permitted curated assets."
            ),
        }

    def list_assets(self):
        return [
            {
                "asset_id": a["asset_id"],
                "view": a["view"],
                "source": a["source"],
                "license": a["license"],
                "adult": a["adult"],
            }
            for a in self.assets.values()
        ]

    def analyze(self, payload):
        decision = check_policy(payload.question)
        if decision:
            return decision
        asset = self.assets.get(payload.asset_id)
        if not asset:
            return envelope(
                "unsupported_input",
                "xray",
                "This image is not a registered, reviewed adult frontal chest asset. "
                "Arbitrary image uploads cannot be scored.",
                findings=[],
            )
        image, _, measurements = validate_asset(asset, self.settings)
        if self.adapter is None:
            raise AppError(
                503, "error", "Research model unavailable. Complete the explicit asset setup."
            )
        with self.compute.enter():
            findings = self.adapter.predict(image)
        refs = {r.chunk_id: r for f in findings for r in self.references.search(f["name"])[:1]}
        return envelope(
            "ok",
            "xray",
            "Selected research model outputs",
            asset_id=payload.asset_id,
            findings=findings,
            quality=measurements,
            supported_input_decision="curated_adult_frontal",
            model_id=self.adapter.model_id,
            weight_sha256=self.adapter.weight_hash,
            preprocessing_version=self.adapter.preprocessing_version,
            score_semantics=self.adapter.score_semantics,
            evaluation_status="integration_only_not_independently_validated",
            claims=[{"text": r.text, "citation_ids": [r.chunk_id]} for r in refs.values()],
            citations=[r.citation() for r in refs.values()],
            warnings=["Research model scores; not calibrated probabilities or diagnoses."],
            limitations=[
                "No normality verdict. Low scores do not rule out disease.",
                "Technical checks do not establish diagnostic quality.",
                "Explanation unavailable for terms outside the local reference library.",
            ],
        )
