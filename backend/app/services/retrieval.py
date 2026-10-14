import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from urllib.parse import urlsplit

import yaml
from pydantic import Field

from backend.app.schemas import StrictModel

APPROVED_HOSTS = {
    "www.nhlbi.nih.gov",
    "www.niddk.nih.gov",
    "dailymed.nlm.nih.gov",
    "medlineplus.gov",
    "www.cdc.gov",
    "www.icmr.gov.in",
    "stw.icmr.org.in",
    "cdsco.gov.in",
    "www.mohfw.gov.in",
    "mohfw.gov.in",
    "www.nice.org.uk",
    "www.fda.gov",
    "www.accessdata.fda.gov",
    "india-pharma.gsk.com",
    "www.gsk.com",
    "www.cipla.com",
    "www.nppa.gov.in",
    "qps.nhsrcindia.org",
}
DRUG_SOURCE_TYPES = {"drug_label", "retailer_monograph"}
TEACHING_HOSTS = {"opentextbc.ca", "pressbooks.lib.vt.edu", "humanbiology.pressbooks.tru.ca", "open.oregonstate.education", "open.lib.umn.edu", "iris.who.int", "www.who.int", "hlh.who.int", "openoregon.pressbooks.pub", "pmc.ncbi.nlm.nih.gov", "europepmc.org", "learningstatisticswithr.com"}
TEACHING_LICENSES = {"CC-BY-4.0", "CC-BY-NC-4.0", "CC-BY-SA-4.0", "CC-BY-NC-SA-4.0", "CC BY 4.0", "CC BY-NC 4.0", "CC BY-SA 4.0", "CC BY-NC-SA 4.0", "CC-BY-NC-SA-3.0-IGO", "CC-BY-NC-SA-3.0"}


def permitted_source(url, source):
    """Primary hosts or the exact secondary collection explicitly approved by the user."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return False
    if parsed.hostname in APPROVED_HOSTS:
        return True
    basis = source.get("permission_basis") or {}
    if parsed.hostname == "www.nimh.nih.gov":
        return (
            basis.get("type") == "publisher_reuse"
            and basis.get("approved_host") == parsed.hostname
            and basis.get("license") == "NIMH-public-domain"
            and basis.get("license_url") == "https://www.nimh.nih.gov/site-info/policies"
            and basis.get("clinical_review") is False
            and basis.get("snapshot_sha256") == source.get("raw_sha256")
            and bool(re.fullmatch(r"[0-9a-f]{64}", source.get("raw_sha256", "")))
        )
    if parsed.hostname in TEACHING_HOSTS:
        license_url = urlsplit(basis.get("license_url", ""))
        identifier = basis.get("license", "").replace(" ", "-").casefold()
        cc_path = "/licenses/" + identifier.removeprefix("cc-").removesuffix("-4.0") + "/4.0"
        if identifier == "cc-by-nc-sa-3.0-igo":
            cc_path = "/licenses/by-nc-sa/3.0/igo"
        if identifier == "cc-by-nc-sa-3.0":
            cc_path = "/licenses/by-nc-sa/3.0"
        license_location = license_url.hostname == parsed.hostname or (
            license_url.hostname == "creativecommons.org" and license_url.path.rstrip("/") == cc_path
        )
        return (
            basis.get("type") == "open_license"
            and basis.get("approved_host") == parsed.hostname
            and basis.get("license") in TEACHING_LICENSES
            and license_url.scheme == "https"
            and license_location
            and basis.get("clinical_review") is False
            and basis.get("snapshot_sha256") == source.get("raw_sha256")
            and bool(re.fullmatch(r"[0-9a-f]{64}", source.get("raw_sha256", "")))
        )
    if parsed.hostname in {"stacks.cdc.gov", "archive.cdc.gov"}:
        license_url = urlsplit(basis.get("license_url", ""))
        return (
            basis.get("type") == "publisher_reuse"
            and basis.get("approved_host") == parsed.hostname
            and basis.get("license") == "CDC-public-domain"
            and license_url.scheme == "https" and license_url.hostname in {"stacks.cdc.gov", "www.cdc.gov", "archive.cdc.gov"}
            and basis.get("clinical_review") is False
            and basis.get("snapshot_sha256") == source.get("raw_sha256")
            and bool(re.fullmatch(r"[0-9a-f]{64}", source.get("raw_sha256", "")))
        )
    return (
        parsed.hostname == "www.netmeds.com"
        and basis.get("approved_host") == parsed.hostname
        and basis.get("type") == "user_attested"
        and basis.get("dataset_ref") == "drowsyng/medicines-dataset"
        and bool(basis.get("user_statement"))
        and basis.get("asserted_license") is True
        and basis.get("asserted_verification") is True
        and basis.get("clinical_review") is False
        and basis.get("snapshot_sha256") == source.get("raw_sha256")
        and bool(re.fullmatch(r"[0-9a-f]{64}", source.get("raw_sha256", "")))
    )


class Reference(StrictModel):
    source_id: str
    title: str
    url: str
    publisher: str
    jurisdiction: str
    section: str
    source_date: str | None = None
    retrieved_date: str
    snapshot_id: str
    text: str = Field(min_length=10, max_length=4000)
    topics: list[str] = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)
    source_type: str = "education"
    entity: str | None = None
    formulations: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    chunk_id: str = ""
    # Optional v2 lineage is omitted from legacy hashes when unset.
    section_id: str | None = None
    text_revision: str | None = None
    aliases: list[str] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)
    product_identity: str | None = None
    clinical_review: bool = False
    label_strengths: list[str] = Field(default_factory=list)
    products: list[dict] = Field(default_factory=list)
    permission_basis: dict = Field(default_factory=dict)

    def stable_id(self):
        return "chunk_" + self.content_hash()[:24]

    def applicable_product(self, name=None, formulation=None, strength=None, route=None):
        if not self.products:
            return (
                (not formulation or formulation.casefold() in self.formulations)
                and (not strength or strength.casefold() in self.strengths)
                and (
                    not route
                    or route.casefold()
                    in (self.routes or (["oral"] if self.source_type == "drug_label" else []))
                )
            )
        products = self.products
        # A verified variant brand must stay within its own product tuple.
        if name and name.casefold() != (self.entity or "").casefold():
            exact = [
                p
                for p in products
                if name.casefold() in {p.get("brand", "").casefold(), p.get("name", "").casefold()}
            ]
            if exact:
                products = exact
        return any(
            (not formulation or formulation.casefold() == p.get("formulation", "").casefold())
            and (not strength or strength.casefold() in p.get("match_strengths", []))
            and (not route or route.casefold() == p.get("route", "").casefold())
            for p in products
        )

    def content_hash(self):
        payload = self.model_dump(exclude={"chunk_id"})
        for key in (
            "section_id",
            "text_revision",
            "aliases",
            "routes",
            "product_identity",
            "clinical_review",
            "label_strengths",
            "products",
            "permission_basis",
        ):
            if not payload[key]:
                payload.pop(key)
        content = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def citation(self):
        return {
            **self.model_dump(
                include={
                    "chunk_id",
                    "source_id",
                    "title",
                    "url",
                    "section",
                    "section_id",
                    "source_date",
                    "snapshot_id",
                    "jurisdiction",
                    "product_identity",
                    "text_revision",
                    "clinical_review",
                    "label_strengths",
                    "permission_basis",
                    "source_type",
                }
            ),
            "excerpt": self.text,
            "publisher": self.publisher,
        }


def terms(text):
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def phrase_match(phrase, text):
    return bool(re.search(r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", text.casefold()))


class ReferenceStore:
    def __init__(self, settings):
        self.settings = settings
        self.records = []
        self.error = None
        self.dense = None
        self.catalogue = None
        try:
            register = yaml.load(
                settings.source_register.read_text(encoding="utf-8"),
                Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader),
            )
            if register.get("catalogue"):
                entry = register["catalogue"]
                path = settings.source_register.parent / entry["path"]
                if not path.resolve().is_relative_to(settings.source_register.parent.resolve()):
                    raise ValueError("Catalogue path outside release")
                raw = path.read_bytes()
                if (
                    entry["approval"] != "developer_reviewed"
                    or hashlib.sha256(raw).hexdigest() != entry["checksum"]
                ):
                    raise ValueError("Catalogue is not approved or changed")
                self.catalogue = json.loads(raw)
            approvals = {
                entry["source_id"]: entry
                for entry in register["sources"]
                if entry["approval"] in {"developer_reviewed", "user_attested"}
                and entry.get("terms")
                and not entry.get("superseded_by")
            }
            if len({entry["source_id"] for entry in register["sources"]}) != len(
                register["sources"]
            ):
                raise ValueError("Duplicate source identity in register")
            seen = set()
            loaded = {}
            for line in self._corpus_lines(settings.corpus_path):
                if not line.strip():
                    continue
                record = Reference.model_validate_json(line)
                source = approvals.get(record.source_id)
                if (
                    source is None
                    or source["url"] != record.url
                    or not permitted_source(record.url, source)
                ):
                    raise ValueError("Source approval or URL failed")
                if record.source_type == "retailer_monograph" and (
                    source["approval"] != "user_attested"
                    or record.permission_basis != source.get("permission_basis")
                    or record.clinical_review
                ):
                    raise ValueError("Retailer source lacks its bound user attestation")
                if record.source_type == "teaching" and (
                    record.permission_basis != source.get("permission_basis", {})
                    or record.clinical_review != source.get("clinical_review", False)
                ):
                    raise ValueError("Teaching source permission/review binding changed")
                if (
                    urlsplit(record.url).hostname == "www.netmeds.com"
                    and record.source_type != "retailer_monograph"
                ):
                    raise ValueError("Retailer content cannot claim primary-label authority")
                checksums = source.get("record_checksums", [source.get("checksum")])
                if record.content_hash() not in checksums:
                    raise ValueError("Approved reference content hash changed")
                if source.get("version") and record.text_revision != source["version"]:
                    raise ValueError("Reference version differs from source register")
                record.chunk_id = record.stable_id()
                if record.chunk_id in seen:
                    raise ValueError("Duplicate section in active corpus")
                self.records.append(record)
                seen.add(record.chunk_id)
                loaded.setdefault(record.source_id, set()).add(record.content_hash())
            for source_id, source in approvals.items():
                expected = set(source.get("record_checksums", [source.get("checksum")]))
                if loaded.get(source_id, set()) != expected:
                    raise ValueError("Active corpus missing approved sections")
            if not self.records:
                raise ValueError("Empty reference corpus")
            self.document_frequencies = Counter(
                term
                for record in self.records
                if record.source_type != "retailer_monograph"
                for term in terms(record.text + " " + record.section)
            )
            self.rank_document_count = sum(
                r.source_type != "retailer_monograph" for r in self.records
            ) or len(self.records)
            self.id_records = {record.chunk_id: record for record in self.records}
            self.education_records = [
                r for r in self.records if r.source_type not in DRUG_SOURCE_TYPES
            ]
            self.drug_identities = defaultdict(list)
            self.identity_tokens = defaultdict(set)
            self.topic_tokens = defaultdict(set)
            for record in self.records:
                for identity in [record.entity, *record.aliases]:
                    if identity and record.source_type in DRUG_SOURCE_TYPES:
                        identity = identity.casefold()
                        self.drug_identities[identity].append(record)
                        tokens = re.findall(r"[a-z0-9]+", identity)
                        if tokens:
                            self.identity_tokens[tokens[0]].add(identity)
                for topic in record.topics:
                    tokens = re.findall(r"[a-z0-9]+", topic.casefold())
                    if tokens:
                        self.topic_tokens[tokens[0]].add(topic)
            if settings.retrieval_backend in {"chroma", "hybrid"}:
                from backend.app.adapters.embeddings import DenseRetriever

                self.dense = DenseRetriever(settings, self.records)
        except (OSError, ValueError, KeyError, TypeError, ImportError):
            self.records = []
            self.error = "Reference corpus unavailable or invalid. Run the ingestion check."

    def search(self, question, limit=3, entity=None, *, require_requested_section=True):
        if not self.records:
            return []
        query = terms(question)
        ranked = []
        candidates = []
        query_lower = question.casefold()
        india_requested = bool(re.search(r"\b(?:india|indian)\b", query_lower))
        matched_ingredients = self.matched_identities(question, entity)
        drug_query = bool(matched_ingredients)
        drug_records = {
            r.chunk_id: r for name in matched_ingredients for r in self.drug_identities[name]
        }
        search_records = [*self.education_records, *drug_records.values()]
        drug_word = bool(re.search(r"\b(?:drug|medicine|medication|tablet|capsule)\b", query_lower))
        semantic_eligible = bool(
            re.search(
                r"\b(?:blood|red cells|white cells|haemoglobin|hemoglobin|heart|lung|kidney|"
                r"liver|thyroid|airway|breathing|glucose|sugar|urine|cholesterol|air sacs|"
                r"scan|radiograph|opacity|fluid|pain|inflammation|antibody|electrical|"
                r"insulin|cough|clot|platelet|iron|acid|test|oxygen|sleep)\b",
                query_lower,
            )
        )
        for record in search_records:
            identities = [(p or "").casefold() for p in [record.entity, *record.aliases]]
            if entity is not None and entity.casefold() not in identities:
                continue
            if record.source_type in DRUG_SOURCE_TYPES:
                if entity is None and not any(p and phrase_match(p, question) for p in identities):
                    continue
                if india_requested and record.jurisdiction != "India":
                    continue
                quantity_query = query_lower
                if record.source_type == "retailer_monograph":
                    named = [name for name in matched_ingredients if name in identities]
                    if named:
                        name = max(named, key=len)
                        quantity_query = re.sub(
                            r"(?<!\w)" + re.escape(name) + r"(?!\w)", " ", quantity_query
                        )
                for spelling, unit in {
                    "milligrams": "mg",
                    "milligram": "mg",
                    "micrograms": "mcg",
                    "microgram": "mcg",
                    "grams": "g",
                    "gram": "g",
                    "millilitres": "ml",
                    "milliliters": "ml",
                    "millilitre": "ml",
                    "milliliter": "ml",
                    "ug": "mcg",
                    "gm": "g",
                }.items():
                    quantity_query = re.sub(r"(?<=\d)\s*" + spelling + r"\b", unit, quantity_query)
                # Only reviewed unit-dose solid strengths are matched in v2.
                # Unknown units or concentrations must not be silently ignored.
                if re.search(
                    r"\d+(?:\.\d+)?\s*(?:units?\b|iu\b|u/|%|(?:mg|mcg|g)\s*/)", quantity_query
                ):
                    continue
                variant_unresolved = False
                for identity in identities:
                    if not identity:
                        continue
                    marker = re.search(
                        r"(?<!\w)"
                        + re.escape(identity)
                        + r"\s+(t|d|ds|cv|mr|sr|cr|xl|plus|forte)\b",
                        query_lower,
                    )
                    if marker and marker[0] not in identities:
                        variant_unresolved = True
                if variant_unresolved:
                    continue
                route_aliases = {
                    "oral": "oral",
                    "by mouth": "oral",
                    "intravenous": "intravenous",
                    "iv": "intravenous",
                    "intravenously": "intravenous",
                    "intramuscular": "intramuscular",
                    "im": "intramuscular",
                    "intramuscularly": "intramuscular",
                    "subcutaneous": "subcutaneous",
                    "subcutaneously": "subcutaneous",
                    "topical": "topical",
                    "rectal": "rectal",
                    "ophthalmic": "ophthalmic",
                    "otic": "otic",
                    "ear drops": "otic",
                    "vaginal": "vaginal",
                    "intravaginal": "vaginal",
                    "nasal": "nasal",
                    "inhaled": "respiratory (inhalation)",
                    "inhalation": "respiratory (inhalation)",
                }
                qualifier_query = (
                    quantity_query if record.source_type == "retailer_monograph" else question
                )
                routes = {
                    value
                    for alias, value in route_aliases.items()
                    if phrase_match(alias, qualifier_query)
                }
                default_routes = ["oral"] if record.source_type == "drug_label" else []
                if routes and not routes <= set(record.routes or default_routes):
                    continue
                forms = [
                    p
                    for p in [
                        "injection",
                        "capsule",
                        "tablet",
                        "suspension",
                        "solution",
                        "cream",
                        "ointment",
                        "chewable",
                        "syrup",
                        "drops",
                        "inhaler",
                        "gel",
                        "shampoo",
                        "soap",
                        "powder",
                        "lotion",
                        "expectorant",
                        "spray",
                        "sachet",
                        "patch",
                        "suppository",
                        "softgel",
                    ]
                    if phrase_match(p, qualifier_query)
                ]
                relevant_products = record.products or [
                    {"formulation": f, "match_strengths": record.strengths}
                    for f in record.formulations
                ]
                matching_brands = [
                    p.get("brand", "")
                    for p in relevant_products
                    if p.get("brand") and phrase_match(p["brand"], question)
                ]
                if matching_brands:
                    brand = max(matching_brands, key=len).casefold()
                    relevant_products = [
                        p for p in relevant_products if p.get("brand", "").casefold() == brand
                    ]
                if forms and not any(
                    all(phrase_match(form, p.get("formulation", "")) for form in forms)
                    for p in relevant_products
                ):
                    continue
                # Explicit release form or strength must belong to this product.
                if re.search(
                    r"\b(?:extended|immediate|delayed)[ -]release\b", qualifier_query, re.I
                ):
                    requested = (
                        re.search(
                            r"\b(?:extended|immediate|delayed)[ -]release\b", qualifier_query, re.I
                        )[0]
                        .casefold()
                        .replace(" ", "-")
                    )
                    if not any(requested in f.replace(" ", "-") for f in record.formulations):
                        continue
                strength_matches = re.findall(
                    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b", quantity_query
                )
                if strength_matches and not all(
                    re.sub(r"\s+", "", value)
                    in [re.sub(r"\s+", "", s.casefold()) for s in record.strengths]
                    for value in strength_matches
                ):
                    continue
                if strength_matches and not any(
                    all(phrase_match(form, p.get("formulation", "")) for form in forms)
                    and all(
                        re.sub(r"\s+", "", s) in p.get("match_strengths", [])
                        for s in strength_matches
                    )
                    for p in relevant_products
                ):
                    continue
            matches = [p for p in record.topics if phrase_match(p, question)]
            if drug_query and record.source_type not in DRUG_SOURCE_TYPES:
                matches = [
                    p
                    for p in matches
                    if not any(phrase_match(p, identity) for identity in matched_ingredients)
                ]
            if (
                record.source_type not in DRUG_SOURCE_TYPES
                and not matches
                and (drug_query or drug_word)
            ):
                continue
            candidates.append(record)
            if entity is None and not matches and record.source_type not in DRUG_SOURCE_TYPES:
                continue
            body_terms = terms(record.section + " " + record.text + " " + " ".join(record.keywords))
            # IDF weighting prefers specific test/section words over generic terms.
            score = len(matches) * 3 + sum(
                math.log(1 + self.rank_document_count / (1 + self.document_frequencies[term]))
                for term in query & body_terms
            )
            if india_requested and record.jurisdiction == "India":
                score += 8
            if record.source_type == "retailer_monograph":
                intent_sections = [
                    (r"\b(?:used for|uses|purpose|indications)\b", r"\b(?:USES(?: OF)?|indications)\b"),
                    (
                        r"\b(?:warnings?|precautions?|contraindications?)\b",
                        r"\b(?:WARNING|PRECAUTIONS|contraindications)\b",
                    ),
                    (r"\binteractions?\b", r"\bINTERACTIONS?\b"),
                    (r"\b(?:work|works|mechanism)\b", r"\b(?:WORKS|mechanism)\b"),
                    (r"\bside effects?\b", r"\bSIDE EFFECTS\b"),
                ]
                if any(
                    re.search(intent, question, re.I) and re.search(section, record.section, re.I)
                    for intent, section in intent_sections
                ):
                    score += 20
            ranked.append((score, record))
        if drug_query and not any(r.source_type in DRUG_SOURCE_TYPES for r in candidates):
            return []
        # A secondary retail alias is not a cross-product equivalence mapping.
        for name in matched_ingredients:
            ids = {
                r.source_id
                for r in candidates
                if r.source_type == "retailer_monograph"
                and name in [(r.entity or "").casefold(), *(a.casefold() for a in r.aliases)]
            }
            if len(ids) > 1:
                if not any(r.source_type == "drug_label" for r in candidates):
                    return []
                candidates = [r for r in candidates if r.source_id not in ids]
                ranked = [(s, r) for s, r in ranked if r.source_id not in ids]
        if require_requested_section and candidates and all(r.source_type == "retailer_monograph" for r in candidates):
            requested_sections = [
                section
                for intent, section in [
                    (r"\binteractions?\b", r"\bINTERACTIONS?\b"),
                    (
                        r"\b(?:warnings?|precautions?|contraindications?)\b",
                        r"\b(?:WARNING|PRECAUTIONS|contraindications)\b",
                    ),
                    (r"\b(?:work|works|mechanism)\b", r"\b(?:WORKS|mechanism)\b"),
                    (r"\bside effects?\b", r"\bSIDE EFFECTS\b"),
                    (
                        r"\b(?:used for|uses|purpose|indications)\b",
                        r"\b(?:USES(?: OF)?|indications|INTRODUCTION)\b",
                    ),
                ]
                if re.search(intent, question, re.I)
            ]
            if requested_sections and not all(
                any(re.search(section, r.section, re.I) for r in candidates)
                for section in requested_sections
            ):
                return []
        # For a simple definition, prefer a section explicitly about the subject
        # over incidental mentions in other chapters. Preserve the full section
        # and all qualifications. Never apply this to medicine identity routing,
        # contextual questions, or comparisons.
        definition = re.fullmatch(r"\s*(?:what is|what are|define)\s+(.+?)[.?!]*\s*", question, re.I)
        if definition and not drug_query and entity is None:
            subject = definition.group(1).strip().casefold()
            focused = [(score, record) for score, record in ranked
                       if phrase_match(subject, record.section)]
            if focused:
                ranked = focused
                kept = {record.chunk_id for _, record in focused}
                candidates = [record for record in candidates if record.chunk_id in kept]
        ranked.sort(key=lambda pair: (-pair[0], pair[1].chunk_id))
        if self.dense is not None and self.settings.retrieval_backend == "hybrid" and candidates:
            dense_scores = self.dense.scores(question, [r.chunk_id for r in candidates])
            lexical = {r.chunk_id: score for score, r in ranked}
            maximum = max(lexical.values(), default=1)
            combined = []
            for r in candidates:
                similarity = dense_scores.get(r.chunk_id, -1)
                score = lexical.get(r.chunk_id, 0)
                if score or (
                    semantic_eligible and similarity >= self.settings.semantic_min_similarity
                ):
                    combined.append((0.62 * max(similarity, 0) + 0.38 * score / maximum, r))
            ranked = sorted(combined, key=lambda pair: (-pair[0], pair[1].chunk_id))
        elif self.dense is not None and ranked:
            order = self.dense.rank(question, [r.chunk_id for _, r in ranked])
            ranks = {key: i for i, key in enumerate(order)}
            ranked.sort(key=lambda pair: ranks.get(pair[1].chunk_id, 999))
        return [r for _, r in ranked[:limit]]

    @property
    def snapshot_hash(self):
        return hashlib.sha256("".join(r.chunk_id for r in self.records).encode()).hexdigest()

    def by_id(self, chunk_id):
        return self.id_records.get(chunk_id)

    @staticmethod
    def _corpus_lines(path):
        with path.open(encoding="utf-8") as source:
            yield from source

    def matched_identities(self, question, entity=None):
        if entity is not None:
            return [entity.casefold()] if entity.casefold() in self.drug_identities else []
        possible = {
            name for token in terms(question) for name in self.identity_tokens.get(token, ())
        }
        matches = [name for name in possible if phrase_match(name, question)]
        # The longest named product wins over an ingredient embedded in its name.
        return [
            name
            for name in matches
            if not any(name != other and phrase_match(name, other) for other in matches)
        ]

    def has_known_topic(self, question):
        return bool(self.matched_identities(question)) or any(
            phrase_match(topic, question)
            for token in terms(question)
            for topic in self.topic_tokens.get(token, ())
        )

    def close(self):
        if self.dense is not None and self.dense.client is not None:
            self.dense.client.close()

    def catalogue_match(self, question):
        if not self.catalogue or self.error:
            return None
        matches = [e for e in self.catalogue["entries"] if phrase_match(e["name"], question)]
        if not matches:
            return None
        entry = max(matches, key=lambda e: len(e["name"]))
        source = self.catalogue["source"]
        text = f"{entry['name']} is listed in India's National List of Essential Medicines 2022. "
        text += (
            "Listed formulations: " + "; ".join(entry["formulations"]) + ". "
            if entry.get("formulations")
            else "Formulation extraction is unavailable for this entry. "
        )
        text += "This catalogue listing does not establish indications, contraindications, brand equivalence or personal treatment."
        ref = Reference(
            source_id="india-nlem-2022",
            title="National List of Essential Medicines 2022",
            url=source["url"],
            publisher=source["publisher"],
            jurisdiction="India",
            section=f"Entry {entry.get('entry_number', '')}; PDF page {entry.get('page', '')}",
            retrieved_date=source["retrieved_date"],
            source_date=source.get("source_date"),
            snapshot_id=self.records[0].snapshot_id,
            text=text,
            topics=[entry["name"]],
            keywords=[entry["name"]],
            source_type="catalogue",
            entity=entry["name"].casefold(),
        )
        ref.chunk_id = ref.stable_id()
        return ref

    def manifest(self):
        return {
            "records": len(self.records),
            "snapshot_hash": self.snapshot_hash,
            "backend": self.settings.retrieval_backend,
            "topics": sorted(
                {
                    topic
                    for r in self.records
                    if r.source_type != "retailer_monograph"
                    for topic in r.topics
                }
            ),
            "review": "Developer-curated references and user-attested retailer material; no qualified clinical review claimed.",
            "documents": len({r.source_id for r in self.records}),
            "medicine_entities": sorted(
                {
                    r.entity
                    for r in self.records
                    if r.entity and r.source_type != "retailer_monograph"
                }
            ),
            "jurisdictions": sorted({r.jurisdiction for r in self.records}),
            "library_version": self.records[0].snapshot_id if self.records else None,
            "indian_catalogue_entries": len(self.catalogue["entries"])
            if self.catalogue and not self.error
            else 0,
            "retailer_sections": sum(r.source_type == "retailer_monograph" for r in self.records),
            "retailer_products": len(
                {r.source_id for r in self.records if r.source_type == "retailer_monograph"}
            ),
        }
