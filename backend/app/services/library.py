"""Installed reference library: signed packs + hybrid (BM25 + dense) retrieval.

Packs live under ``<library_root>/packs/<pack_id>/`` with ``manifest.json``
(+ ``.sig``), ``units.jsonl``, ``documents.jsonl`` and ``index/``. The active
selection is ``<library_root>/active.json``; the previous selection is kept as
``last-known-good.json`` so a failed update never removes a working library.
"""
import json
import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger("medical_ai")

STOPWORDS = set("""a an and are as at be by can could did do does for from had has have how i if in into is it its
me my of on or our should so than that the their them then there these they this to was were what when where which
who why will with would you your about tell explain describe define list give mean means please also between versus
vs difference compare role brief short detail detailed discuss write note notes answer question""".split())


LOW_VALUE = re.compile(r"^\s*(?:keywords?\s*:|abbreviations?\s*:|the online version (?:of this article )?contains|"
                       r"supplementary (?:information|material)|electronic supplementary|this (?:is an )?open access article|"
                       r"publisher'?s note|data availability)", re.I)
METHODS_SECTION = re.compile(r"\b(?:methods?|methodology|search strategy|eligibility|study selection|data extraction|"
                             r"statistical analys|risk of bias|quality assessment|prisma|inclusion criteria|ethics|"
                             r"funding|conflicts? of interest|acknowledg|author contributions)\b", re.I)


@dataclass
class Hit:
    unit_id: str
    doc_id: str
    title: str
    section: str
    text: str
    content_class: str
    evidence_type: str
    license: str
    jurisdiction: str
    publisher: str
    url: str
    published: str
    acquired: str
    access: str
    publication_status: str
    kind: str
    reliability: str
    pack_id: str
    edition: str
    score: float = 0.0
    signals: dict = field(default_factory=dict)

    def citation(self):
        return {
            "chunk_id": self.unit_id, "source_id": self.doc_id, "title": self.title, "url": self.url,
            "section": self.section, "publisher": self.publisher or "", "source_date": self.published,
            "retrieved_date": self.acquired, "jurisdiction": self.jurisdiction, "license": self.license,
            "content_class": self.content_class, "evidence_type": self.evidence_type, "access": self.access,
            "publication_status": self.publication_status, "excerpt": self.text, "source_type": "library_" + self.content_class,
            "material_type": "research" if self.content_class == "research" else self.content_class,
            "extraction_reliability": self.reliability, "pack_id": self.pack_id, "edition": self.edition,
        }


class PackError(RuntimeError):
    pass


def fts_query(text, expansions=()):
    """Build a safe FTS5 MATCH expression: OR over content terms + quoted phrases."""
    terms, phrases = [], []
    for source in [text, *expansions]:
        words = [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", source.casefold()) if w not in STOPWORDS and len(w) > 1]
        for word in words:
            word = word.strip("'-").replace("'", "")
            if word and word not in terms:
                terms.append(word)
        if 1 < len(words) <= 5:
            phrase = " ".join(w.replace('"', "") for w in words)
            if phrase not in phrases:
                phrases.append(phrase)
    parts = [f'"{t}"' for t in terms[:40]] + [f'"{p}"' for p in phrases[:8]]
    return " OR ".join(parts)


class Pack:
    def __init__(self, path, public_key=None, verify_hashes=False):
        from aster_library.signing import SignatureError, verify_file

        self.path = Path(path)
        try:
            verify_file(self.path / "manifest.json", public_key)
            verify_file(self.path / "index" / "index-manifest.json", public_key)
        except (SignatureError, FileNotFoundError) as exc:
            raise PackError(f"{self.path.name}: signature check failed") from exc
        self.manifest = json.loads((self.path / "manifest.json").read_text(encoding="utf-8"))
        self.index_manifest = json.loads((self.path / "index" / "index-manifest.json").read_text(encoding="utf-8"))
        import hashlib

        manifest_hash = hashlib.sha256((self.path / "manifest.json").read_bytes()).hexdigest()
        if self.index_manifest["pack_manifest_sha256"] != manifest_hash:
            raise PackError(f"{self.path.name}: index was built for a different pack")
        for name, meta in self.index_manifest["files"].items():
            target = self.path / "index" / name
            if not target.exists() or target.stat().st_size != meta["bytes"]:
                raise PackError(f"{self.path.name}: index file {name} missing or truncated")
            if verify_hashes:
                from aster_library.index import sha256_file

                if sha256_file(target) != meta["sha256"]:
                    raise PackError(f"{self.path.name}: index file {name} hash mismatch")
        self.pack_id = self.manifest["pack_id"]
        self.edition = self.manifest["edition"]
        self.db = sqlite3.connect(f"file:{self.path / 'index' / 'units.sqlite'}?mode=ro", uri=True, check_same_thread=False)
        self.lock = threading.Lock()
        self.vectors = np.load(self.path / "index" / "dense.f16.npy", mmap_mode="r", allow_pickle=False)
        if self.vectors.shape != (self.index_manifest["units"], self.index_manifest["dense"]["dimension"]):
            raise PackError(f"{self.path.name}: dense index shape mismatch")

    def close(self):
        self.db.close()

    def bm25(self, match, limit=80, classes=None):
        if not match:
            return []
        sql = ("SELECT units_fts.rowid, bm25(units_fts, 3.0, 1.5, 1.0) AS s FROM units_fts "
               "WHERE units_fts MATCH ? ORDER BY s LIMIT ?")
        with self.lock:
            try:
                rows = self.db.execute(sql, (match, limit * 3 if classes else limit)).fetchall()
            except sqlite3.OperationalError:
                return []
        if classes:
            allowed = self.rows_with_class([r[0] for r in rows], classes)
            rows = [r for r in rows if r[0] in allowed][:limit]
        return [(rowid, -score) for rowid, score in rows]

    def rows_with_class(self, rowids, classes):
        if not rowids:
            return set()
        marks = ",".join("?" * len(rowids))
        cmarks = ",".join("?" * len(classes))
        with self.lock:
            return {r[0] for r in self.db.execute(
                f"SELECT rowid FROM units WHERE rowid IN ({marks}) AND content_class IN ({cmarks})", (*rowids, *classes))}

    def dense(self, vector, limit=80):
        scores = np.asarray(self.vectors @ vector.astype(np.float16), dtype=np.float32)
        if len(scores) <= limit:
            top = np.argsort(-scores)
        else:
            top = np.argpartition(-scores, limit)[:limit]
            top = top[np.argsort(-scores[top])]
        return [(int(i) + 1, float(scores[i])) for i in top]

    def fetch(self, rowids):
        if not rowids:
            return {}
        marks = ",".join("?" * len(rowids))
        with self.lock:
            rows = self.db.execute(
                f"SELECT rowid, unit_id, doc_id, title, section, text, content_class, evidence_type, license, jurisdiction, "
                f"publisher, url, published, acquired, access, publication_status, kind, extraction_reliability "
                f"FROM units WHERE rowid IN ({marks})", rowids).fetchall()
        out = {}
        for row in rows:
            out[row[0]] = Hit(*[value or "" for value in row[1:]], pack_id=self.pack_id, edition=self.edition)
        return out


class LibraryStore:
    """Loads active packs with last-known-good fallback and serves hybrid search."""

    CLASS_WEIGHT = {
        "patient": {"patient": 1.25, "drug_label": 1.0, "professional": 0.85, "research": 0.55},
        "study": {"professional": 1.2, "research": 0.9, "patient": 0.7, "drug_label": 0.8},
        "drug": {"drug_label": 1.3, "professional": 0.95, "patient": 0.95, "research": 0.6},
        "research": {"research": 1.15, "professional": 1.1, "patient": 0.5, "drug_label": 0.6},
    }
    TYPE_WEIGHT = {"textbook": 1.15, "guideline": 1.15, "systematic_review": 1.1, "meta_analysis": 1.1, "review": 1.05,
                   "patient_summary": 1.1, "patient_test_information": 1.1, "drug_label": 1.0, "rct": 0.95,
                   "original_research": 0.85, "case_report": 0.7, "editorial": 0.6, "educational": 1.05}

    def __init__(self, root, *, encoder_path=None, reranker_path=None, enabled=True, clock=time.time):
        self.root = Path(root)
        self.encoder_path = encoder_path
        self.reranker_path = reranker_path
        self._reranker = None
        self.reranker_error = None
        self.packs = []
        self.error = None
        self.status = "disabled" if not enabled else "loading"
        self.selection = None
        self.used_fallback = False
        self.clock = clock
        self._encoder = None
        self._encoder_lock = threading.Lock()
        if enabled:
            self._load()

    def _load(self):
        candidates = [("active.json", False), ("last-known-good.json", True)]
        errors = []
        for name, fallback in candidates:
            path = self.root / name
            if not path.exists():
                continue
            try:
                selection = json.loads(path.read_text(encoding="utf-8"))
                packs = [Pack(self.root / "packs" / pack_id) for pack_id in selection["packs"]]
                if not packs:
                    raise PackError("empty selection")
                self.packs, self.selection, self.used_fallback = packs, selection, fallback
                self.status = "ready"
                if fallback:
                    logger.warning("library: active selection unusable; using last-known-good")
                return
            except (PackError, OSError, ValueError, KeyError) as exc:
                errors.append(f"{name}: {exc}")
        self.status = "unavailable"
        self.error = "; ".join(errors) or "No installed reference library was found."

    def close(self):
        for pack in self.packs:
            pack.close()

    @property
    def encoder(self):
        with self._encoder_lock:
            if self._encoder is None:
                from aster_library.embed import OnnxEncoder

                self._encoder = OnnxEncoder(self.encoder_path) if self.encoder_path else OnnxEncoder()
            return self._encoder

    @property
    def reranker(self):
        with self._encoder_lock:
            if self._reranker is None and self.reranker_path and self.reranker_error is None:
                try:
                    from backend.app.services.rerank import CrossEncoderReranker

                    self._reranker = CrossEncoderReranker(self.reranker_path)
                except Exception as exc:  # retrieval still works with fused ranking only
                    self.reranker_error = f"{type(exc).__name__}"
            return self._reranker

    def generic_names(self):
        """{casefolded US generic name: display name} from installed drug labels (exact-match use only)."""
        if getattr(self, "_generics", None) is None:
            names = {}
            for pack in self.packs:
                with pack.lock:
                    rows = pack.db.execute("SELECT DISTINCT title FROM units WHERE content_class = 'drug_label'").fetchall()
                for (title,) in rows:
                    generic = (title or "").split(" — ", 1)[0].strip()
                    if generic:
                        names[" ".join(generic.casefold().split())] = generic
            self._generics = names
        return self._generics

    def freshness(self):
        """Per-class age status for the active packs. Never disables the library."""
        report = {}
        now = self.clock()
        for pack in self.packs:
            created = time.mktime(time.strptime(pack.manifest["created"][:10], "%Y-%m-%d"))
            age_days = int((now - created) / 86400)
            for content_class, rule in pack.manifest.get("freshness", {}).items():
                state = ("outdated_warning" if age_days > rule["warn_after_days"]
                         else "review_due" if age_days > rule["review_after_days"] else "current")
                previous = report.get(content_class)
                if previous is None or age_days > previous["age_days"]:
                    report[content_class] = {"age_days": age_days, "state": state, **rule, "pack": pack.pack_id}
        return report

    def manifest(self):
        return {
            "status": self.status,
            "error": self.error,
            "used_last_known_good": self.used_fallback,
            "packs": [{"pack_id": p.pack_id, "edition": p.edition, "version": p.manifest.get("version"),
                       "created": p.manifest.get("created"), "documents": p.manifest["counts"]["documents"],
                       "units": p.manifest["counts"]["units"], "by_content_class": p.manifest["counts"].get("by_content_class", {}),
                       "license_scope": p.manifest.get("license_scope")} for p in self.packs],
            "freshness": self.freshness() if self.packs else {},
        }

    def search(self, query, *, expansions=(), audience="patient", classes=None, k=8, per_doc=2, candidates=80):
        if not self.packs:
            return []
        vector = self.encoder.encode([query + (" " + " ".join(expansions[:3]) if expansions else "")])[0]
        match = fts_query(query, expansions)
        fused = {}
        for pack in self.packs:
            lexical = pack.bm25(match, candidates, classes)
            dense = pack.dense(vector, candidates)
            if classes:
                allowed = pack.rows_with_class([r for r, _ in dense], classes)
                dense = [(r, s) for r, s in dense if r in allowed]
            for rank, (rowid, score) in enumerate(lexical):
                entry = fused.setdefault((pack, rowid), {"rrf": 0.0, "bm25": None, "dense": None})
                entry["rrf"] += 1 / (60 + rank)
                entry["bm25"] = score
            for rank, (rowid, score) in enumerate(dense):
                entry = fused.setdefault((pack, rowid), {"rrf": 0.0, "bm25": None, "dense": None})
                entry["rrf"] += 1 / (60 + rank)
                entry["dense"] = score
        by_pack = {}
        for (pack, rowid) in fused:
            by_pack.setdefault(pack, []).append(rowid)
        hits = []
        weights = self.CLASS_WEIGHT.get(audience, self.CLASS_WEIGHT["patient"])
        for pack, rowids in by_pack.items():
            for rowid, hit in pack.fetch(rowids).items():
                if hit.publication_status == "retracted" or LOW_VALUE.match(hit.text):
                    continue
                signals = fused[(pack, rowid)]
                dense_score = signals["dense"]
                if dense_score is None:
                    dense_score = float(np.dot(np.asarray(pack.vectors[rowid - 1], dtype=np.float32), vector))
                    signals["dense"] = dense_score
                score = signals["rrf"] * weights.get(hit.content_class, 0.8) * self.TYPE_WEIGHT.get(hit.evidence_type, 1.0)
                if hit.kind == "table":
                    score *= 0.8
                if hit.access == "abstract":
                    score *= 0.9
                # Very weak semantic match is noise even if a rare word matched lexically.
                if dense_score < 0.2:
                    score *= 0.5
                prior = weights.get(hit.content_class, 0.8) * self.TYPE_WEIGHT.get(hit.evidence_type, 1.0)
                if audience != "research" and METHODS_SECTION.search(hit.section or ""):
                    prior *= 0.5  # search strategies/statistics of a review rarely explain the topic itself
                if hit.kind == "figure_caption":
                    prior *= 0.7
                hit.score, hit.signals = score, signals
                hit.signals["prior"] = prior
                hits.append(hit)
        hits.sort(key=lambda h: h.score, reverse=True)
        reranker = self.reranker
        if reranker is not None and hits:
            pool, per_pool = [], {}
            for hit in hits:
                if per_pool.get(hit.doc_id, 0) >= 12:
                    continue
                per_pool[hit.doc_id] = per_pool.get(hit.doc_id, 0) + 1
                pool.append(hit)
                if len(pool) >= 48:
                    break
            # Passage content only: titles all match the topic and saturate the cross-encoder.
            logits = reranker.scores(query, [f"{h.section}. {h.text[:700]}" for h in pool])
            for hit, logit in zip(pool, logits, strict=True):
                hit.signals["rerank"] = float(logit)
                # Additive prior keeps audience/source-type preferences as tie-breakers.
                hit.score = float(logit) + 2.0 * float(np.log(max(hit.signals["prior"], 1e-3)))
            hits = sorted(pool, key=lambda h: h.score, reverse=True)
        chosen, per = [], {}
        for hit in hits:
            if per.get(hit.doc_id, 0) >= per_doc:
                continue
            per[hit.doc_id] = per.get(hit.doc_id, 0) + 1
            chosen.append(hit)
            if len(chosen) >= k:
                break
        return chosen

    def best_similarity(self, query):
        """Max dense similarity of the query to the library (topicality signal)."""
        if not self.packs:
            return 0.0
        vector = self.encoder.encode([query])[0]
        best = 0.0
        for pack in self.packs:
            top = pack.dense(vector, 3)
            if top:
                best = max(best, top[0][1])
        return best

