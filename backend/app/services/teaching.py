"""Separate curriculum teaching retrieval and source-bound explanations.

Developer-reviewed explanations are approved paired text, not an automatic
semantic proof. Medical faculty review remains separate and explicit.
"""

import hashlib
import json
import math
import re
from collections import Counter
from functools import lru_cache

from backend.app.errors import SCOPE, envelope
from backend.app.services.policy import check_policy
from backend.app.services.retrieval import ReferenceStore, phrase_match, terms
from backend.app.services.teaching_query import plan_question

STOP = terms("explain define what why how does do is are the a an in on of for and or to with from by caused me please compare difference differences between relate related describe discuss briefly detailed detail mbbs mds postgraduate pg student students patient doctor medical clinical case fictional question answer mechanism mechanisms work works simple simplify language words viva exam")
FACETS = frozenset(terms("function functions structure structures anatomy histology development growth pathophysiology pathogenesis etiology etiopathogenesis features investigations principles principle procedure limitations consequences classify classification disorders causes effects indications identify misconceptions associated signs symptoms management diagnostic assessment risks risk reasoning common ability observe demonstrate process role stated curriculum scope written educational cannot certify observed performance introduction basic basics underlying relevant terminology can could would should whether every all any only always have has does its their these those as then other without claiming single causal name number correct count opposite meaning resulting needed explanation information agreement variability experimental changes location allow serve during list main shared who affected omit"))
DISCOURSE = frozenset(terms("can could would should whether have has does its their these those as then other without claiming needed explanation information list main shared omit serve"))
CLINICAL_ASPECTS = frozenset(terms("function functions structure structures histology development growth pathophysiology pathogenesis etiology etiopathogenesis investigations investigation management diagnostic assessment indications contraindications symptoms signs complications procedure"))
ALIASES = {"haemoglobin": "hemoglobin", "haemostasis": "hemostasis", "haemorrhage": "hemorrhage", "oedema": "edema", "tumour": "tumor", "tumours": "tumors", "anaemia": "anemia", "hepatic": "liver", "krebs cycle": "citric acid cycle", "tca cycle": "citric acid cycle", "rbc": "red blood cell", "rbcs": "red blood cells", "renal": "kidney", "immunohistochemistry": "immunohistochemical", "ihc": "immunohistochemical"}
ALIASES.update({"epithelial tissues": "epithelium", "epithelial tissue": "epithelium", "epithelia": "epithelium"})
ALIASES.update({"dentine": "dentin", "paediatric": "pediatric",
                "hypomineralisation": "hypomineralization", "anaesthesia": "anesthesia",
                "orthopaedics": "orthopedics", "aetiology": "etiology"})


@lru_cache(maxsize=4096)
def safe_teaching_text(text):
    return safe_source_text_uncached(text)


def safe_source_text_uncached(text):
    """Shared source predicate; private documents must bypass the public cache."""
    if re.match(r"\s*#.*\nURL:\s*https?://", text):
        return False
    if re.match(r"\s*(?:created by|adapted by|copyright|download this|learning objectives|view or print all sections|this content is also available in|(?:text )?references|bibliography)\b", text, re.I):
        return False
    if check_policy("Explain in general: " + text):
        return False
    return not re.search(r"\b(?:you should take|take\s+\d+(?:\.\d+)?|your diagnosis|definitely normal|increase your|stop taking)\b", text, re.I)


@lru_cache(maxsize=32768)
def canonical_teaching_text(text):
    text = re.sub(r"\b(?:without|excluding|do not include)\s+(?:personal\s+)?(?:dosing|dosage|doses?|dose calculations?)(?:\s+advice)?\b", "", text, flags=re.I)
    text = re.sub(r"\bprotein[ -]bound\b", "protein binding", text, flags=re.I)
    for key, value in ALIASES.items():
        text = re.sub(r"\b" + re.escape(key) + r"\b", value, text, flags=re.I)
    return text


@lru_cache(maxsize=32768)
def teaching_terms(text):
    canonical = canonical_teaching_text(text)
    words = terms(canonical) - STOP
    # "Simple" is often a presentation request, but in epithelial histology
    # it is a structural qualifier and must not disappear from the concept.
    if re.search(r"\bsimple\s+(?:(?:squamous|cuboidal|columnar)\s+)?epithelium\b", canonical, re.I):
        words.add("simple")
    morphology = {"glomerular": "glomerulus", "tubular": "tubules", "eruptions": "eruption",
                  "gametes": "gamete", "stools": "stool", "patterns": "pattern"}
    return frozenset(morphology.get(word, word) for word in words)


@lru_cache(maxsize=8192)
def evidence_text(section, text):
    # The contextual prefix describes a whole paper; it must not make every
    # unrelated paragraph appear to explain all the paper's topics.
    body = re.sub(r"^\[Research context:.*?\]\s*", "", text, flags=re.S)
    return canonical_teaching_text(section + " " + body)


@lru_cache(maxsize=16384)
def query_scope(question):
    flags = set()
    for name, pattern in {
        "protocol": r"\b(?:research|study|studies|protocol|experimental|experiment|methods?|results|systematic review|trial|evidence)\b",
        "drug": r"\b(?:drug|medicine|medication)\b",
        "metabolism": r"\bmetaboli[sz](?:m|e|ed|es|ing)\b",
        "vessels": r"\bblood vessels?\b",
        "protein": r"\b(?:free drug|protein[ -]bound drug)\b",
        "normal": r"\bnormal distribution\b",
        "skin": r"\b(?:skin|cutaneous|dermatological)\s+eruption(?:s)?\b",
        "india": r"\b(?:India|Indian)\b",
    }.items():
        if re.search(pattern, question, re.I):
            flags.add(name)
    names = tuple(name for name in re.findall(r"\b([A-Za-z][A-Za-z'-]*)\s+(?:congenital\s+)?syndrome\b", question, re.I)
                  if name.casefold() not in STOP | {"congenital", "genetic", "metabolic", "chromosomal", "developmental", "paraneoplastic"})
    return frozenset(flags), names


@lru_cache(maxsize=8192)
def record_scope(section, text, topics):
    """Cache pure checks by content, so changed records invalidate cached checks."""
    flags = set()
    anchors = section + " " + " ".join(topics)
    for name, pattern, value in (
        ("bibliography", r"(?:^| / )(?:text )?references(?:$| / )|(?:^| / )(?:bibliography|acknowledgements?)(?:$| / )", section),
        ("protocol", r"\b(?:methods|materials|results|literature search|statistical analysis)\b", section),
        ("drug", r"\b(?:drugs?|medicines?|medications?|pharmacokinetics|microsomal)\b", section + " " + text),
        ("vessels", r"\b(?:vessels?|arter(?:y|ies)|veins?|capillar(?:y|ies))\b", anchors),
        ("protein", r"\b(?:protein[ -]bound|protein binding|plasma proteins?|albumin|drug distribution|pharmacokinetics)\b", section + " " + text),
        ("normal", r"\b(?:normal distribution|gaussian|normal curve|bell.shaped)\b", section + " " + text),
        ("skin", r"\b(?:rash|rashes|exanthem|cutaneous|skin eruption)\b", anchors),
    ):
        if re.search(pattern, value, re.I):
            flags.add(name)
    if safe_teaching_text(text):
        flags.add("safe")
    return frozenset(flags)


def comparison_queries(question):
    """Retrieve both sides of an explicit comparison, preserving shared nouns."""
    match = re.search(r"\b(?:compare|difference(?:s)? between)\s+(.+?)\s+(?:and|with|versus|vs\.?)\s+(.+?)[?.]?$", question, re.I)
    if not match:
        return []
    left, right = (part.strip(" ?.:") for part in match.groups())
    shared = {"immunity", "inhibition", "transport", "respiration", "diabetes", "cells", "vaccines"}
    if len(left.split()) == 1 and right.split()[-1].casefold() in shared:
        left += " " + right.split()[-1]
    return [left, right]


@lru_cache(maxsize=16384)
def retrieval_queries(question):
    focus = plan_question(question).focus
    parts = comparison_queries(focus)
    # A trailing clinical qualifier may apply to every side of a comparison or
    # conjunction. Keep the complete request when scope cannot be assigned.
    scope_text = " ".join(parts) if parts else focus
    if re.search(r"\b(?:and|with|versus|vs)\b|;", focus, re.I) and re.search(
            r"\b(?:in|with|for|under|of|at|within|across|among|through|from|during|after|before|following|when|due to|caused by)\b", scope_text, re.I):
        return (focus,)
    if not parts:
        # A competency sentence usually lists facets of one shared condition.
        # Splitting it would detach e.g. "management" from "bladder cancer".
        if len(teaching_terms(focus)) > 8 or re.match(r"^(?:describe|discuss|classify|observe|demonstrate|identify)\b", focus, re.I):
            return (focus,)
        protected = re.sub(r"\bhead and neck\b", "head & neck", focus, flags=re.I)
        parts = [part.replace("head & neck", "head and neck") for part in re.split(r"\s+and\s+|;\s*", protected, flags=re.I)]
        if any(re.match(r"^(?:how|whether|why|when|what|which|does|explain|describe|discuss)\b", part, re.I) for part in parts[1:]):
            return (focus,)
        if any(teaching_terms(part) <= FACETS for part in parts):
            parts = [focus]
    parts = tuple(dict.fromkeys(part.strip(" .!?:") for part in parts if part.strip(" .!?:")))
    return parts if len(parts) <= 4 else (focus,)


def validate_explanation_units(units, references, metadata=None):
    seen = set()
    for unit in units:
        if unit["id"] in seen:
            raise ValueError("Duplicate explanation ID")
        seen.add(unit["id"])
        if unit.get("review_status") != "developer_reviewed" or not unit.get("reviewer") or unit.get("clinical_review") is not False:
            raise ValueError("Explanation lacks an explicit developer review")
        ids = unit.get("citation_ids", [])
        if not ids or set(ids) != set(unit.get("source_hashes", {})):
            raise ValueError("Explanation source binding incomplete")
        for key in ids:
            record = references.get(key)
            if record is None or record.content_hash() != unit["source_hashes"][key]:
                raise ValueError("Explanation source hash changed")
            context = (metadata or {}).get(key, {})
            if context.get("material_type") == "research" and context.get("study_context", "") not in unit["text"]:
                raise ValueError("Research explanation omitted its study context")
        for qualifier in unit.get("qualifications", []):
            if not phrase_match(qualifier, unit["text"]):
                raise ValueError("Explanation omitted a reviewed qualification")
        if check_policy(unit["text"]):
            raise ValueError("Explanation violates the educational policy")


class TeachingStore:
    def __init__(self, settings):
        self.settings, self.error = settings, None
        self.references, self.dense = None, None
        self.records, self.units, self.metadata = [], [], {}
        self.review_flags = {}
        self._derived_records = {}
        self.version = None
        if not settings.enable_teaching:
            return
        try:
            root = settings.teaching_release_path.resolve()
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            required = {"records.jsonl", "sources.yaml", "metadata.json"}
            if not required <= set(manifest["files"]):
                raise ValueError("Teaching release manifest incomplete")
            for name, expected in manifest["files"].items():
                path = (root / name).resolve()
                if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise ValueError("Teaching artifact hash changed")
            profile = settings.model_copy(update={"corpus_path": root / "records.jsonl", "source_register": root / "sources.yaml", "retrieval_backend": "lexical"})
            self.references = ReferenceStore(profile)
            if self.references.error:
                raise ValueError(self.references.error)
            self.records = self.references.records
            if any(r.source_type != "teaching" for r in self.records):
                raise ValueError("Teaching collection contains product or unreviewed material")
            metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
            self.metadata = metadata.get("chunks", metadata)
            for row in self.records:
                context = self.metadata.get(row.chunk_id, {})
                if context.get("material_type") == "research" or row.permission_basis.get("material_type") == "research":
                    if (context.get("material_type") != "research" or not row.source_date
                            or not all(context.get(key) for key in ("study_type", "study_context", "limitations"))
                            or context["study_context"] not in row.text):
                        raise ValueError("Research reference lacks bound study context or limitations")
            self.version = manifest.get("version", root.name)
            self.df = Counter(word for row in self.records for word in teaching_terms(row.text + " " + row.section))
            self.words = {row.chunk_id: teaching_terms(row.text + " " + row.section + " " + " ".join(row.keywords)) for row in self.records}
            for row in self.records:
                self._derived(row)
            embedded_notes = manifest["files"].get("explanations.json")
            if settings.teaching_explanations_sha256 or embedded_notes:
                note_path = settings.teaching_explanations_path if settings.teaching_explanations_sha256 else root / "explanations.json"
                raw = note_path.read_bytes()
                expected_notes = settings.teaching_explanations_sha256 or embedded_notes
                if hashlib.sha256(raw).hexdigest() != expected_notes:
                    raise ValueError("Reviewed explanation artifact changed")
                if embedded_notes and expected_notes != embedded_notes:
                    raise ValueError("Configured explanations differ from the release-bound review holds")
                document = json.loads(raw)
                if document["release_version"] != self.version:
                    raise ValueError("Explanations belong to another teaching release")
                validate_explanation_units(document["units"], self.references.id_records, self.metadata)
                self.units = document["units"]
                for flag in document.get("source_review_flags", []):
                    row = self.references.id_records.get(flag["chunk_id"])
                    if (not row or flag["content_sha256"] != row.content_hash()
                            or flag["runtime_policy"] not in {"exclude", "explanation_only"}
                            or not flag.get("reason") or flag.get("clinical_review") is not False):
                        raise ValueError("Invalid source review flag")
                    self.review_flags[row.chunk_id] = flag
            if settings.teaching_backend == "hybrid":
                from backend.app.adapters.embeddings import DenseRetriever

                profile = profile.model_copy(update={"chroma_path": settings.teaching_index_path, "reference_collection": "medical_teaching_v1"})
                self.dense = DenseRetriever(profile, self.records)
        except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
            self.error = str(error)
            self.records = []

    def _derived(self, row):
        # Collection-local storage avoids LRU thrashing when a library exceeds
        # global cache limits. A content signature invalidates modified rows.
        signature = (row.section, row.text, tuple(row.topics))
        cached = self._derived_records.get(row.chunk_id)
        if cached is None or cached[0] != signature:
            text = evidence_text(row.section, row.text)
            cached = (signature, {
                "scope": record_scope(*signature),
                "text": text,
                "words": teaching_terms(text),
                "anchors": teaching_terms(row.section + " " + " ".join(row.topics)),
            })
            self._derived_records[row.chunk_id] = cached
        return cached[1]

    def search(self, question, limit=5):
        _, groups = self._question_groups(question)
        # Round-robin avoids spending the entire evidence budget on one part.
        balanced = []
        for position in range(2):
            for _, rows in groups:
                if len(rows) > position and rows[position] not in balanced:
                    balanced.append(rows[position])
        return balanced[:limit]

    def _question_groups(self, question):
        plan = plan_question(question)
        from backend.app.services.question_plan import plan_question as understand

        if understand(question).intent == "symptom_information":
            return plan, []
        if not self.records or check_policy(question):
            return plan, []
        if re.search(r"\b(?:\d+(?:\.\d+)?\s*(?:mg|mcg|ml)|tablet|capsule|syrup|brand|catalogue|catalog)\b", question, re.I):
            return plan, []
        parts = retrieval_queries(question)
        groups = []
        for part in parts:
            promoted = []
            for unit in self.units:
                if self._unit_matches(unit, part):
                    for key in unit["citation_ids"]:
                        row = self.references.id_records[key]
                        if self._allowed(row, question, part) and row not in promoted:
                            promoted.append(row)
            ranked = [row for row in self._rank(part) if self._allowed(row, question, part)]
            # Parent concepts and their subtypes often share broad topic tags.
            # Prefer an eligible whole section heading at the requested level
            # over a heading that merely contains the term (e.g. epithelium vs
            # sulcular epithelium). Retain scope words and paired-note sources.
            focus_terms = teaching_terms(part)
            exact_headings = [row for row in ranked
                              if teaching_terms(row.section.rsplit(" / ", 1)[-1]) == focus_terms]
            if exact_headings:
                ranked = exact_headings
            groups.append((part, promoted + [row for row in ranked if row not in promoted]))
        return plan, groups

    @staticmethod
    def _unit_matches(unit, question):
        # Introductory notes may mention subtypes as examples. An explicitly
        # bounded overview must not answer a request about one such subtype.
        if unit.get("match_mode") == "exact_topic" and not any(
            teaching_terms(question) == teaching_terms(topic) for topic in unit.get("topics", [])
        ):
            return False
        # Topic names can have unrelated meanings (ST depression, tensor
        # diffusion). A paired note must address the rest of the request too.
        vocabulary = teaching_terms(unit["text"] + " " + " ".join(unit.get("topics", [])))
        ordered = [word for word in re.findall(r"[a-z0-9]+", canonical_teaching_text(question).casefold()) if word not in STOP]
        if len(ordered) == 2 and any(len(word) <= 2 for word in ordered):
            phrase = " ".join(ordered)
            if not phrase_match(phrase, unit["text"] + " " + " ".join(unit.get("topics", []))):
                return False
        return (any(phrase_match(canonical_teaching_text(topic), canonical_teaching_text(question)) for topic in unit.get("topics", []))
                and (teaching_terms(question) - DISCOURSE) <= vocabulary)

    def _allowed(self, row, question, focus=None):
        query, named_syndromes = query_scope(question)
        if focus is not None:
            focused, named_syndromes = query_scope(focus)
            global_scope = query & {"india"}
            if {"drug", "metabolism"} <= query:
                global_scope |= {"drug", "metabolism"}
            query = focused | global_scope
        content = self._derived(row)["scope"]
        if "bibliography" in content:
            return False
        if self.metadata.get(row.chunk_id, {}).get("material_type") == "research":
            if "protocol" in content and "protocol" not in query:
                return False
        if {"drug", "metabolism"} <= query:
            if "drug" not in content:
                return False
        if "vessels" in query:
            if "vessels" not in content:
                return False
        if "protein" in query:
            if "protein" not in content:
                return False
        if named_syndromes and not any(phrase_match(name, row.text + " " + row.section + " " + " ".join(row.topics)) for name in named_syndromes):
            return False
        if "normal" in query:
            if "normal" not in content:
                return False
        # Tooth eruption and grafts mentioning skin cannot explain a rash.
        if "skin" in query:
            if "skin" not in content:
                return False
        return (self.review_flags.get(row.chunk_id, {}).get("runtime_policy") != "exclude"
                and "safe" in content
                and not ("india" in query and row.jurisdiction not in {"India", "Global"}))

    def _rank(self, question):
        query = teaching_terms(question) - {"research", "evidence", "paper", "papers", "literature"}
        if not query:
            return []
        dense = self.dense.scores(question, list(self.words)) if self.dense else {}
        ranked = []
        weights = {word: math.log(1 + len(self.records) / (1 + self.df[word])) for word in query}
        total = sum(weights.values())
        research_request = bool(re.search(r"\b(?:research|study|studies|paper|trial|protocol|experimental|experiment|evidence|results|methods?)\b", question, re.I))
        for row in self.records:
            if not self._allowed(row, question):
                continue
            derived = self._derived(row)
            source_text = derived["text"]
            content_words = derived["words"]
            overlap = query & content_words
            # Named clinical tasks cannot disappear merely because the topic
            # itself matches. This is a conservative lexical gate, not a proof
            # that a passage fully explains an investigation or intervention.
            if not (query & CLINICAL_ASPECTS) <= content_words:
                continue
            # Short concepts need all their meaningful words. Broad metadata or
            # a partial homonym cannot supply a missing entity/context modifier.
            if len(query) <= 3 and not query <= content_words:
                continue
            entities = query - FACETS
            if len(query) > 3 and any(self.df[word] == 0 for word in entities):
                continue
            if entities:
                if len(entities) <= 4 and not entities <= content_words:
                    continue
                if len(entities) > 4 and len(entities & content_words) / len(entities) < .7:
                    continue
            ordered = [word for word in re.findall(r"[a-z0-9]+", canonical_teaching_text(question).casefold()) if word not in STOP]
            if len(ordered) == 2 and any(len(word) <= 2 for word in ordered) and not re.search(r"\b" + re.escape(ordered[0]) + r"[\s-]+" + re.escape(ordered[1]) + r"\b", source_text, re.I):
                continue
            anchors = derived["anchors"]
            coverage = sum(weights[w] for w in overlap) / total
            exact = any(phrase_match(topic, question) for topic in row.topics)
            # One generic word cannot stand in for an unknown medical concept.
            pharmacokinetic_anchor = any(phrase_match(phrase, question) and phrase_match(phrase, row.text)
                                         for phrase in ("free drug", "protein binding", "drug distribution", "liver metabolism"))
            body_definition = len(query) == 1 and bool(re.search(r"\b(?:is|are|called|defined as|refers to)\b[^.!?]{0,50}\b" + re.escape(next(iter(query))) + r"\b", source_text, re.I))
            lexical_ok = (exact or bool(query & anchors) or pharmacokinetic_anchor or body_definition) and coverage >= .4 and (len(overlap) >= min(2, len(query)) or exact)
            semantic_ok = dense.get(row.chunk_id, -1) >= .60 and coverage >= .25 and bool(overlap)
            if not (lexical_ok or semantic_ok):
                continue
            leaf = teaching_terms(row.section.rsplit(" / ", 1)[-1])
            specificity = len(query & leaf) / max(len(leaf), 1)
            score = coverage + .2 * len(query & anchors) / len(query) + .15 * exact + .5 * specificity
            if self.metadata.get(row.chunk_id, {}).get("material_type") != "research" and not research_request:
                score += .75
            if self.metadata.get(row.chunk_id, {}).get("material_type") == "research" and not research_request:
                if re.search(r"\b(?:introduction|background|abstract)\b", row.section, re.I):
                    score += .2
                design = self.metadata[row.chunk_id].get("study_design", "")
                methods = re.search(r"\b(?:methods|results|statistical analysis)\b", row.section, re.I)
                narrow_ihc = "review" not in design.casefold() and re.search(r"\b(?:immunohistochemistry|immunohistochemical procedure)\b", row.section, re.I)
                if methods or narrow_ihc:
                    score -= .5
            if dense:
                score = .4 * max(dense.get(row.chunk_id, 0), 0) + .6 * score
            ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        # A direct named concept takes precedence over disconnected token
        # mentions. If the full phrase is absent everywhere, retain the original
        # guarded lexical/semantic candidates (e.g. adjective/noun morphology).
        direct = [item for item in ranked if phrase_match(canonical_teaching_text(question), self._derived(item[1])["text"])]
        if direct:
            ranked = direct
        return [row for _, row in ranked]

    def answer(self, question):
        plan, groups = self._question_groups(question)
        if not groups:
            return None
        claims, rows, unsupported, supported = [], [], [], []
        selected = []
        for part, candidates in groups:
            ids = {row.chunk_id for row in candidates[:5]}
            units = [unit for unit in self.units if set(unit["citation_ids"]) <= ids and self._unit_matches(unit, part)]
            units.sort(key=lambda unit: max((len(topic) for topic in unit.get("topics", []) if phrase_match(topic, part)), default=0), reverse=True)
            part_claims = [{"text": unit["text"], "citation_ids": unit["citation_ids"]} for unit in units[:1]]
            if units:
                selected.extend(units[:1])
            else:
                raw = [row for row in candidates if row.chunk_id not in self.review_flags]
                # A definition should not append a neighbouring chapter just
                # because it mentions the concept. Keep complete source units.
                if re.fullmatch(r"\s*(?:what is|what are|define)\s+.+", question, re.I):
                    focused = [row for row in raw if phrase_match(
                        canonical_teaching_text(part), canonical_teaching_text(row.section))]
                    if focused:
                        raw = focused
                part_claims = [{"text": row.text, "citation_ids": [row.chunk_id]} for row in raw[:2]]
            if not part_claims:
                unsupported.append(part)
                continue
            supported.append(part)
            for claim in part_claims:
                if claim not in claims:
                    claims.append(claim)
            for row in candidates:
                if row not in rows:
                    rows.append(row)
        if not claims:
            return None
        used = {key for claim in claims for key in claim["citation_ids"]}
        used_rows = [row for row in rows if row.chunk_id in used]
        citations = []
        research = False
        for row in used_rows:
            context = self.metadata.get(row.chunk_id, {})
            citation = row.citation()
            citation.update({key: context[key] for key in ("material_type", "study_type", "study_design", "study_context", "limitations", "syllabus_ids") if key in context})
            if row.chunk_id in self.review_flags:
                citation["source_review_notice"] = self.review_flags[row.chunk_id].get("reason", "Source wording is under review; only the bounded explanation is available.")
            research |= context.get("material_type") == "research"
            citations.append(citation)
        limitations = [SCOPE, "Teaching material is source-backed and developer-reviewed; medical faculty review has not been performed.",
                       "Only the supported parts of the question are covered. Curriculum mastery and clinical accuracy are not established."]
        if research:
            limitations.append("Research excerpts retain their publication date and study setting. Experimental findings do not establish a treatment for people; a review is not itself a clinical trial.")
        warnings = []
        if unsupported:
            warnings.append("I could not find supported material for: " + "; ".join(unsupported) + ".")
        if plan.requests:
            limitations.append("These source notes do not establish completion of the additional requested tasks: " + "; ".join(plan.requests) + ".")
        return envelope("ok", "medical_education", "Let's break this down, starting with what the references explain.",
                        claims=claims, citations=citations,
                        warnings=warnings, supported_topics=supported, unsupported_topics=unsupported,
                        unverified_requested_tasks=list(plan.requests),
                        answer_method="reviewed_teaching_explanation" if selected else "source_backed_teaching",
                        teaching_version=self.version, clinical_review=False,
                        subjects=sorted({subject for row in used_rows for subject in self.metadata.get(row.chunk_id, {}).get("subjects", [])}),
                        limitations=limitations)

    def manifest(self):
        return {"enabled": self.settings.enable_teaching, "version": self.version, "records": len(self.records),
                "backend": self.settings.teaching_backend, "reviewed_explanations": len(self.units), "source_review_holds": len(self.review_flags), "clinical_review": False, "error": self.error}

    def close(self):
        if self.references:
            self.references.close()
