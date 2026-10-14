"""Local blinded review assignments with immutable, hash-bound submissions.

No network/API integration. Tokens authenticate assignment possession only;
medical identities, qualifications and independent rubrics require external
verification. This registry cannot promote production evidence or close F03.
"""

import hashlib
import json
import random
import re
import secrets
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def value_hash(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


DISPLAY_FIELDS = {
    "claims", "text", "citation_ids", "citations", "chunk_id", "source_id", "title", "url", "publisher",
    "section", "section_id", "snapshot_id", "source_date", "retrieved_date", "jurisdiction", "excerpt",
    "source_type", "source_review_notice", "missing_facets", "coverage_status", "topic_id", "facet", "query",
    "scope", "requested_by_user", "structured_answer", "task", "sections", "heading", "claim_indices", "state",
    "comparison", "entities", "rows", "axes", "label", "cells", "feature", "left", "right",
    "claim_evidence", "claim_index", "span", "start", "end", "text_sha256", "source_sha256",
    "prepared_claim_evidence", "prepared_id", "prepared_text_sha256", "source_hashes", "source_spans",
    "explanation_layers", "level", "content", "warnings", "limitations", "unsupported_parts",
    "version", "simple", "deeper", "context", "simple_notice", "deeper_notice",
}


def blinded_answer(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key not in DISPLAY_FIELDS:
                continue
            if key == "source_hashes" and isinstance(item, dict):
                result[key] = {identity: digest for identity, digest in item.items()
                               if re.fullmatch(r"chunk_[0-9a-f]{24}", identity)
                               and isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)}
            else:
                result[key] = blinded_answer(item)
        return result
    if isinstance(value, list):
        return [blinded_answer(item) for item in value]
    return value


class ReviewStore:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY, rubric TEXT NOT NULL, rubric_hash TEXT NOT NULL,
                source_version TEXT NOT NULL, seed INTEGER NOT NULL, rights TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cases (
                batch_id TEXT REFERENCES batches(id), blind_id TEXT NOT NULL,
                original_id TEXT NOT NULL, body TEXT NOT NULL, case_hash TEXT NOT NULL,
                PRIMARY KEY(batch_id, blind_id));
            CREATE TABLE IF NOT EXISTS reviewers (
                id TEXT PRIMARY KEY, qualification TEXT NOT NULL, specialty TEXT NOT NULL,
                independent INTEGER NOT NULL, credential_evidence TEXT);
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY, batch_id TEXT REFERENCES batches(id),
                reviewer_id TEXT REFERENCES reviewers(id), role TEXT NOT NULL,
                token_hash TEXT NOT NULL, UNIQUE(batch_id, reviewer_id));
            CREATE TABLE IF NOT EXISTS reviews (
                assignment_id TEXT REFERENCES assignments(id), blind_id TEXT NOT NULL,
                body TEXT NOT NULL, submitted_at TEXT NOT NULL,
                PRIMARY KEY(assignment_id, blind_id));
            CREATE TABLE IF NOT EXISTS review_freezes (
                batch_id TEXT PRIMARY KEY REFERENCES batches(id), frozen_at TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    def create_batch(self, cases, rubric, *, seed, source_version, rights):
        if rights != "local_review_authorized":
            raise ValueError("explicit local-review permission required")
        dimensions = rubric.get("dimensions", [])
        if (not rubric.get("version") or not dimensions or len(set(dimensions)) != len(dimensions)
                or not all(isinstance(item, str) and item for item in dimensions)
                or rubric.get("score_min") != 0 or rubric.get("score_max") != 4):
            raise ValueError("versioned 0–4 dimension rubric required")
        if not cases or len({case["case_id"] for case in cases}) != len(cases) or not source_version:
            raise ValueError("nonempty unique cases and source version required")
        batch = "batch_" + secrets.token_hex(16)
        shuffled = list(cases)
        random.Random(seed).shuffle(shuffled)
        with self.db:
            self.db.execute("INSERT INTO batches VALUES(?,?,?,?,?,?)",
                            (batch, encoded(rubric), value_hash(rubric), source_version, seed, rights))
            for case in shuffled:
                if not case.get("question") or not isinstance(case.get("answer"), dict) or not isinstance(case.get("source_hashes"), dict):
                    raise ValueError("original question, immutable answer and exact source hashes required")
                if any(not re.fullmatch(r"chunk_[0-9a-f]{24}", identity) or not isinstance(digest, str)
                       or not re.fullmatch(r"[0-9a-f]{64}", digest) for identity, digest in case["source_hashes"].items()):
                    raise ValueError("exact source identities and SHA-256 digests required")
                # Whitelist fields to prevent a model name or strategy label in
                # other input metadata from leaking into the blinded packet.
                answer = blinded_answer(case["answer"])
                body = {"question": case["question"], "answer": answer,
                        "original_answer_sha256": value_hash(case["answer"]),
                        "source_hashes": case["source_hashes"],
                        "independent_reference_rubric": case.get("independent_reference_rubric")}
                self.db.execute("INSERT INTO cases VALUES(?,?,?,?,?)",
                                (batch, "case_" + secrets.token_hex(16), case["case_id"], encoded(body), value_hash(body)))
        return batch

    def register_reviewer(self, identity, *, qualification, specialty, independent, credential_evidence=None):
        if not identity or not qualification or not specialty or independent is not True:
            raise ValueError("explicit independent reviewer and qualification declaration required")
        with self.db:
            self.db.execute("INSERT INTO reviewers VALUES(?,?,?,?,?)",
                            (identity, qualification, specialty, 1, credential_evidence))

    def assign(self, batch, reviewer, role="reviewer", *, deliver=None):
        if role not in {"reviewer", "adjudicator"}:
            raise ValueError("reviewer or adjudicator role required")
        if not self.db.execute("SELECT 1 FROM batches WHERE id=?", (batch,)).fetchone():
            raise ValueError("unknown batch")
        if not self.db.execute("SELECT 1 FROM reviewers WHERE id=? AND independent=1", (reviewer,)).fetchone():
            raise ValueError("registered independent reviewer required")
        if role == "adjudicator":
            existing = self.db.execute("SELECT reviewer_id FROM assignments WHERE batch_id=?", (batch,)).fetchall()
            pairs = self.db.execute("SELECT blind_id,COUNT(DISTINCT a.reviewer_id) n FROM reviews r JOIN assignments a ON a.id=r.assignment_id WHERE a.batch_id=? AND a.role='reviewer' GROUP BY blind_id", (batch,)).fetchall()
            n_cases = self.db.execute("SELECT COUNT(*) FROM cases WHERE batch_id=?", (batch,)).fetchone()[0]
            if reviewer in {row[0] for row in existing} or len(pairs) != n_cases or any(row["n"] < 2 for row in pairs):
                raise ValueError("independent third reviewer and two original submissions per case required")
        token, identity = secrets.token_urlsafe(32), "assignment_" + secrets.token_hex(16)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.db.execute("SELECT 1 FROM review_freezes WHERE batch_id=?", (batch,)).fetchone():
                raise ValueError("original review membership is frozen; create a new batch")
            self.db.execute("INSERT INTO assignments VALUES(?,?,?,?,?)",
                            (identity, batch, reviewer, role, hashlib.sha256(token.encode()).hexdigest()))
            if deliver is not None:
                # A failed token-file delivery rolls back the assignment, so
                # the reviewer is not stranded behind the UNIQUE constraint.
                deliver(identity, token)
            if role == "adjudicator":
                self.db.execute("INSERT INTO review_freezes VALUES(?,?)", (batch, datetime.now(timezone.utc).isoformat()))
        return identity, token

    def authorized(self, identity, token):
        row = self.db.execute("SELECT * FROM assignments WHERE id=?", (identity,)).fetchone()
        if not isinstance(token, str) or row is None or not secrets.compare_digest(row["token_hash"], hashlib.sha256(token.encode()).hexdigest()):
            raise ValueError("assignment authorization failed")
        return row

    def packet(self, assignment, token):
        assigned = self.authorized(assignment, token)
        batch = self.db.execute("SELECT * FROM batches WHERE id=?", (assigned["batch_id"],)).fetchone()
        cases = self.db.execute("SELECT * FROM cases WHERE batch_id=? ORDER BY rowid", (batch["id"],)).fetchall()
        body = {"assignment_id": assignment, "role": assigned["role"], "rubric": json.loads(batch["rubric"]),
                "rubric_sha256": batch["rubric_hash"], "source_version": batch["source_version"],
                "cases": [{"blind_id": case["blind_id"], "case_sha256": case["case_hash"], **json.loads(case["body"])} for case in cases],
                "independent_reference_state": "supplied_externally_unverified" if all(json.loads(case["body"])["independent_reference_rubric"] is not None for case in cases) else "pending",
                "qualification_verification": "external_pending", "rights": batch["rights"]}
        if assigned["role"] == "adjudicator":
            prior = self.db.execute("SELECT r.* FROM reviews r JOIN assignments a ON a.id=r.assignment_id WHERE a.batch_id=? AND a.role='reviewer' ORDER BY r.rowid", (batch["id"],)).fetchall()
            body["prior_assessments"] = {}
            for row in prior:
                data = json.loads(row["body"])
                body["prior_assessments"].setdefault(row["blind_id"], []).append(
                    {key: data[key] for key in ("scores", "critical_error", "reason", "review_type")})
        return {**body, "packet_sha256": value_hash(body)}

    def import_reviews(self, assignment, token, payload):
        assigned = self.authorized(assignment, token)
        packet = self.packet(assignment, token)
        if payload.get("packet_sha256") != packet["packet_sha256"] or payload.get("rubric_sha256") != packet["rubric_sha256"]:
            raise ValueError("packet/rubric identity changed")
        cases = {case["blind_id"]: case for case in packet["cases"]}
        reviews = payload.get("reviews", [])
        if len(reviews) != len(cases) or {row.get("blind_id") for row in reviews} != set(cases):
            raise ValueError("submit exactly the assigned cases")
        if self.db.execute("SELECT 1 FROM reviews WHERE assignment_id=?", (assignment,)).fetchone():
            raise ValueError("submitted reviews are immutable; create a corrected versioned batch")
        dimensions = set(packet["rubric"]["dimensions"])
        for row in reviews:
            if row.get("case_sha256") != cases[row["blind_id"]]["case_sha256"]:
                raise ValueError("case identity changed")
            scores = row.get("scores")
            if (not isinstance(scores, dict) or set(scores) != dimensions
                    or any(value is not None and (type(value) is not int or not 0 <= value <= 4) for value in scores.values())):
                raise ValueError("each rubric score must be 0–4 or explicit null")
            if not isinstance(row.get("critical_error"), bool) or not row.get("reason", "").strip():
                raise ValueError("explicit critical-error flag and assessment reason required")
            if row.get("review_type") not in {"human_declared", "synthetic_mechanics"}:
                raise ValueError("explicit submission provenance required")
            if assigned["role"] == "adjudicator" and not row.get("adjudication_rationale", "").strip():
                raise ValueError("explicit adjudication rationale required")
        submitted = datetime.now(timezone.utc).isoformat()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if assigned["role"] == "reviewer" and self.db.execute("SELECT 1 FROM review_freezes WHERE batch_id=?", (assigned["batch_id"],)).fetchone():
                raise ValueError("original review submissions are frozen for adjudication; create a new batch")
            for row in reviews:
                # Keep assessment reasons private in this local registry.
                self.db.execute("INSERT INTO reviews VALUES(?,?,?,?)", (assignment, row["blind_id"], encoded(row), submitted))
        return {"imported": len(reviews), "role": assigned["role"], "qualified_review": "external_verification_pending"}

    def report(self, batch):
        record = self.db.execute("SELECT * FROM batches WHERE id=?", (batch,)).fetchone()
        if record is None:
            raise ValueError("unknown batch")
        rows = self.db.execute("SELECT r.*,a.role,a.reviewer_id FROM reviews r JOIN assignments a ON a.id=r.assignment_id WHERE a.batch_id=? ORDER BY a.reviewer_id", (batch,)).fetchall()
        original, adjudicated = {}, set()
        for row in rows:
            if row["role"] == "adjudicator":
                adjudicated.add(row["blind_id"])
            else:
                original.setdefault(row["blind_id"], []).append(json.loads(row["body"]))
        agreement = {}
        disagreements = {identity for identity, ratings in original.items()
                         if len({rating["critical_error"] for rating in ratings}) > 1}
        for dimension in json.loads(record["rubric"])["dimensions"]:
            pairs = []
            for identity, ratings in original.items():
                values = [rating["scores"][dimension] for rating in ratings if rating["scores"][dimension] is not None]
                if len(set(values)) > 1:
                    disagreements.add(identity)
                # More than two raters requires a separately specified metric;
                # do not arbitrarily select two and report Cohen's kappa.
                if len(ratings) == 2 and len(values) == 2:
                    pairs.append(values)
            kappa, observed = None, None
            if pairs:
                observed = sum(left == right for left, right in pairs) / len(pairs)
                left, right = Counter(pair[0] for pair in pairs), Counter(pair[1] for pair in pairs)
                expected = sum(left[value] * right[value] for value in set(left) | set(right)) / len(pairs) ** 2
                if expected < 1:
                    kappa = (observed - expected) / (1 - expected)
            agreement[dimension] = {"paired_cases": len(pairs), "observed_agreement": observed,
                                    "cohen_kappa": kappa, "metric": "nominal; exactly two nonmissing raters"}
        return {"batch_id": batch, "cases": self.db.execute("SELECT COUNT(*) FROM cases WHERE batch_id=?", (batch,)).fetchone()[0],
                "submitted_reviews": sum(len(values) for values in original.values()),
                "disagreement_cases": len(disagreements), "adjudicated_cases": len(adjudicated), "agreement": agreement,
                "qualified_clinical_accuracy": None,
                "qualified_review": "external_credential_and_reference_verification_pending"}
