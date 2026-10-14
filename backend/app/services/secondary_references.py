"""User-authorized, explicitly unverified secondary notes with exact master anchors."""

import hashlib
import json
import re
from collections import defaultdict

from backend.app.services.retrieval import Reference

USER_STATEMENT = "use this as secondary data in the ai with a subtly caution of unverified data"
SECONDARY_NOTICE = "Unverified secondary data · confirm with the product label."
SOURCE_COLLECTIONS = {
    "dmedhi/indian-medicines": "https://huggingface.co/datasets/dmedhi/indian-medicines",
    "shudhanshusingh/az-medicine-dataset-of-india": "https://www.kaggle.com/datasets/shudhanshusingh/az-medicine-dataset-of-india",
}


class SecondaryReferenceStore:
    def __init__(self, settings):
        self.settings = settings
        self.records = []
        self.by_anchor = defaultdict(list)
        self.identities = defaultdict(list)
        self.identity_tokens = defaultdict(set)
        self.error = None
        self.library_version = None
        if not settings.enable_secondary_references:
            return
        try:
            manifest_bytes = (settings.secondary_reference_path / "manifest.json").read_bytes()
            if not re.fullmatch(r"[0-9a-f]{64}", settings.secondary_manifest_sha256):
                raise ValueError("Secondary manifest must have a pinned checksum")
            if hashlib.sha256(manifest_bytes).hexdigest() != settings.secondary_manifest_sha256:
                raise ValueError("Secondary manifest checksum mismatch")
            manifest = json.loads(manifest_bytes)
            if (
                manifest["review_status"] != "unverified"
                or manifest["clinical_review"] is not False
                or manifest["authorization"] != {"type": "user_authorized_secondary", "user_statement": USER_STATEMENT}
            ):
                raise ValueError("Secondary source authorization/status changed")
            raw = (settings.secondary_reference_path / "records.jsonl").read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest["records_sha256"]:
                raise ValueError("Secondary records checksum mismatch")
            datasets = {row["dataset_ref"]: row["snapshot_sha256"] for row in manifest["source_datasets"]}
            seen = set()
            records = []
            for line in raw.splitlines():
                record = Reference.model_validate_json(line)
                basis = record.permission_basis
                dataset = basis.get("dataset_ref")
                if (
                    record.source_type != "unverified_secondary"
                    or record.clinical_review
                    or basis.get("review_status") != "unverified"
                    or basis.get("type") != "user_authorized_secondary"
                    or dataset not in datasets
                    or record.url != SOURCE_COLLECTIONS.get(dataset)
                    or basis.get("snapshot_sha256") != datasets[dataset]
                    or not re.fullmatch(r"[0-9a-f]{64}", basis.get("snapshot_sha256", ""))
                    or not str(basis.get("matched_netmeds_source_id", "")).startswith("netmeds-")
                    or not basis.get("source_rows")
                    or record.snapshot_id != manifest["library_version"]
                    or record.chunk_id != record.stable_id()
                    or record.chunk_id in seen
                    or len(record.text) > 1450
                ):
                    raise ValueError("Secondary note identity, provenance or status failed")
                seen.add(record.chunk_id)
                records.append(record)
            if len(records) != manifest["records"] or not 0 < len(records) <= 20000:
                raise ValueError("Secondary record count mismatch")
            self.records = records
            self.library_version = manifest["library_version"]
            for record in records:
                self.by_anchor[record.permission_basis["matched_netmeds_source_id"]].append(record)
                identity = " ".join((record.entity or "").casefold().split())
                if identity:
                    self.identities[identity].append(record)
                    self.identity_tokens[re.findall(r"[a-z0-9]+", identity)[0]].add(identity)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.records = []
            self.by_anchor.clear()
            self.error = str(error)

    def resolve_question(self, question):
        """Resolve one exact secondary source name to its checked master anchor.

        This is a qualified source link, not a new alias in the primary library.
        Outside strength/form/route words stay in the query for the primary gates.
        """
        candidates = set()
        for token in re.findall(r"[a-z0-9]+", question.casefold()):
            candidates.update(self.identity_tokens.get(token, ()))
        matched = {}
        for identity in candidates:
            pattern = r"(?<!\w)" + r"\s+".join(re.escape(word) for word in identity.split()) + r"(?!\w)"
            if match := re.search(pattern, question, re.I):
                matched[identity] = match
        # Ignore a contained shorter name only when the longer exact name is present.
        matched = {name: match for name, match in matched.items() if not any(name != other and name in other for other in matched)}
        if len(matched) != 1:
            return None
        identity, match = next(iter(matched.items()))
        notes = self.identities[identity]
        targets = {(r.permission_basis["matched_netmeds_source_id"], r.permission_basis.get("matched_netmeds_product")) for r in notes}
        if len(targets) != 1:
            return None
        _, product = next(iter(targets))
        if not product:
            return None
        outside = question[:match.start()] + " " + question[match.end():]
        if re.search(r"\b(?:junior|paediatric|pediatric|baby|kids|ds|sr|cr|mr|xr|xl|ir|er|plus|forte|sf|sugar[ -]free)\b", outside, re.I):
            return None
        return question[:match.start()] + product + question[match.end():]

    def search(self, question, anchors, limit=2):
        # Anchors have already passed the primary product/form/strength/route gates.
        identities = {r.source_id for r in anchors if r.source_type == "retailer_monograph"}
        if self.error or len(identities) != 1:
            return []
        if re.search(r"\b(?:interactions?|warnings?|precautions?|contraindications?|dosing|dosage|dose)\b", question, re.I):
            return []  # Neither table has those clinical sections.
        requested = []
        for intent, section in [
            (r"\b(?:ingredients?|composition|contains?|constituents?|salt)\b", "Dataset-reported composition"),
            (r"\b(?:uses|used for|purpose|indications)\b", "Dataset-reported uses"),
            (r"\b(?:side effects?|adverse effects?)\b", "Dataset-reported side effects"),
        ]:
            if re.search(intent, question, re.I):
                requested.append(section)
        if not requested:
            if not re.search(r"\b(?:what is|what are|tell me about|explain)\b", question, re.I):
                return []
            requested = ["Dataset-reported uses", "Dataset-reported composition"]
        available = self.by_anchor.get(next(iter(identities)), [])
        # Avoid giving the same composition twice from near-duplicate datasets.
        ranked = sorted(available, key=lambda r: (requested.index(r.section) if r.section in requested else 99, 0 if r.permission_basis["dataset_ref"] == "dmedhi/indian-medicines" else 1, r.chunk_id))
        selected, sections = [], set()
        for record in ranked:
            if record.section in requested and record.section not in sections:
                selected.append(record)
                sections.add(record.section)
            if len(selected) >= limit:
                break
        return selected

    def manifest(self):
        return {
            "enabled": self.settings.enable_secondary_references, "available": bool(self.records),
            "records": len(self.records), "matched_products": len(self.by_anchor),
            "library_version": self.library_version, "review_status": "unverified",
            "clinical_review": False, "error": self.error,
        }
