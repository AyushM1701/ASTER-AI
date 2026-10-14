"""Bounded public literature retrieval and quotation-bound review scaffolds.

No generated study findings, original results, clinical recommendations or
automatic systematic-review claims. Provider metadata is not medical validation.
"""

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import httpx
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from pydantic import Field, field_validator

from backend.app.schemas import StrictModel
from backend.app.services.output_validation import INSTRUCTIONS

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
MISSING = "Not extracted; assess in the original paper."


class ResearchRequest(StrictModel):
    question: str = Field(min_length=3, max_length=500)
    population: str = Field(min_length=1, max_length=300)
    article_type: Literal["narrative review", "scoping review planning", "protocol planning"] = (
        "narrative review"
    )
    query: str = Field(min_length=3, max_length=1000)
    inclusion: str = Field(default="", max_length=500)
    exclusion: str = Field(default="", max_length=500)
    limit: int = Field(default=10, ge=1, le=20)
    inspect_full_text: bool = False
    public_query_confirmed: Literal[True]

    @field_validator("question", "population", "query", "inclusion", "exclusion")
    @classmethod
    def public_fields(cls, value):
        value = value.strip()
        if re.search(
            r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:patient name|hospital number|my prescription|my report)\b",
            value,
            re.I,
        ):
            raise ValueError("Use public research topics without patient identifiers")
        return value


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).split())


def sha(value):
    return hashlib.sha256(value).hexdigest()


def notice_state(row):
    types = " ".join(row.get("pubTypeList", {}).get("pubType", []))
    notices = row.get("commentCorrectionList", {}).get("commentCorrection", [])
    description = json.dumps(notices) + " " + types
    if re.search(
        r"RetractionIn|Retracted Publication|Retraction of Publication", description, re.I
    ):
        return "retracted", notices
    if re.search(r"ErratumIn|Correction|ExpressionOfConcern|Concern", description, re.I):
        return "publication_notice_requires_review", notices
    return "notices_not_reported_by_provider", notices


class LiteratureSearch:
    def __init__(self, client=None):
        self.client = client

    def _get(self, client, path, params=None, max_bytes=3_000_000):
        # Only fixed provider routes and validated identifiers reach this method.
        with client.stream("GET", BASE + path, params=params, follow_redirects=False) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError("Provider redirected; no external destination followed")
            content = bytearray()
            for part in response.iter_bytes():
                content.extend(part)
                if len(content) > max_bytes:
                    raise ValueError("Provider response exceeds the retrieval limit")
        return bytes(content)

    def search(self, request):
        if self.client:
            return self._search(self.client, request)
        with httpx.Client(
            timeout=httpx.Timeout(15, connect=5),
            trust_env=False,
            headers={"User-Agent": "Aster-Local-Literature-Pilot/1.0"},
        ) as client:
            return self._search(client, request)

    def _search(self, client, request):
        params = dict(query=request.query, format="json", resultType="core", pageSize=request.limit)
        raw = self._get(client, "/search", params)
        data = json.loads(raw)
        rows = data.get("resultList", {}).get("result", [])
        if not isinstance(rows, list) or len(rows) > request.limit:
            raise ValueError("Unexpected provider result shape")
        papers, identities, duplicates, conflicts, rejected = [], {}, 0, 0, 0
        full_text_budget = 3
        for row in rows:
            paper = self._metadata(row)
            if not paper:
                rejected += 1
                continue
            keys = [f"{paper['source']}:{paper['provider_id']}"]
            if paper["doi"]:
                keys.append("doi:" + paper["doi"])
            if paper["pmcid"]:
                keys.append("pmcid:" + paper["pmcid"])
            matched = [identities[k] for k in keys if k in identities]
            if matched:
                previous = matched[0]
                if any(
                    p["title"].casefold() != paper["title"].casefold() or p["year"] != paper["year"]
                    for p in matched
                ):
                    conflicts += 1
                    for p in matched:
                        p["identity_status"] = "conflict_requires_review"
                        p["warnings"].append(
                            "Conflicting records share an identifier; excluded from draft evidence."
                        )
                else:
                    duplicates += 1
                    # Preserve a retraction/notice found on either duplicate.
                    severity = {
                        "notices_not_reported_by_provider": 0,
                        "publication_notice_requires_review": 1,
                        "retracted": 2,
                    }
                    if (
                        severity[paper["publication_status"]]
                        > severity[previous["publication_status"]]
                    ):
                        previous["publication_status"] = paper["publication_status"]
                    if paper["publication_notices"]:
                        previous["publication_notices"] += paper["publication_notices"]
                continue
            if (
                request.inspect_full_text
                and paper["pmcid"]
                and row.get("isOpenAccess") == "Y"
                and full_text_budget
            ):
                full_text_budget -= 1
                try:
                    xml = self._get(client, "/" + paper["pmcid"] + "/fullTextXML")
                    self._full_text(paper, xml)
                except (httpx.HTTPError, ValueError, ET.ParseError, DefusedXmlException):
                    paper["warnings"].append(
                        "Full text could not be admitted; abstract access only."
                    )
            for key in keys:
                identities[key] = paper
            papers.append(paper)
        project = {
            "id": str(uuid4()),
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "question": request.question,
            "population": request.population,
            "article_type": request.article_type,
            "search": {
                "provider": "Europe PMC",
                "scope": "limited_single_provider",
                "query": request.query,
                "parameters": params,
                "date_utc": datetime.now(timezone.utc).isoformat(),
                "inclusion": request.inclusion,
                "exclusion": request.exclusion,
                "screening": "Criteria recorded for manual screening; not automatically applied.",
                "hit_count": data.get("hitCount"),
                "received": len(rows),
                "duplicates_removed": duplicates,
                "identity_conflicts": conflicts,
                "invalid_records_excluded": rejected,
                "response_sha256": sha(raw),
                "full_text_requests_max": 3,
                "pagination": "First page only, provider relevance order; no exhaustive claim.",
            },
            "papers": papers,
            "evidence_table": [],
            "clinical_review": "pending",
            "contradictions": "Not assessed. Findings are kept separate; do not infer consensus.",
            "retention": "Saved locally until explicitly deleted; independent of temporary patient sessions.",
        }
        project["evidence_table"] = [evidence_row(p) for p in papers if eligible(p)]
        project["task_completion"] = False
        project["stage_completion"] = {
            "retrieval": True,
            "bibliography": True,
            "quoted_evidence": bool(project["evidence_table"]),
            "outline_scaffold": True,
            "medical_synthesis": False,
            "critical_appraisal": False,
            "manual_screening": False,
        }
        project["completion_scope"] = (
            "Bounded retrieval, quoted evidence and review scaffold only; critical appraisal and synthesis remain manual."
        )
        project["validation"] = validate_project(project)
        return project

    def _metadata(self, row):
        source, identity = str(row.get("source", "")), str(row.get("id", ""))
        title, authors, year = (
            plain(row.get("title")),
            plain(row.get("authorString")),
            str(row.get("pubYear", "")),
        )
        if (
            source not in {"MED", "PMC"}
            or not re.fullmatch(r"(?:PMC)?\d{1,12}", identity)
            or not title
            or not authors
            or not re.fullmatch(r"(?:19|20)\d{2}", year)
        ):
            return None
        doi = str(row.get("doi", "")).strip().lower().removeprefix("https://doi.org/")
        if doi and not re.fullmatch(r'10\.\d{4,9}/[^\s<>"{}]+', doi):
            return None
        pmcid = str(row.get("pmcid", ""))
        if pmcid and not re.fullmatch(r"PMC\d{1,12}", pmcid):
            return None
        status, notices = notice_state(row)
        abstract = plain(row.get("abstractText"))
        # Copyright permission is not inferred from an abstract being visible.
        quote = " ".join(abstract.split()[:25])
        if INSTRUCTIONS.search(quote):
            quote = ""
        passage = {
            "id": f"{source}:{identity}:abstract",
            "section": "Abstract fragment",
            "text": quote,
            "fragment": len(abstract.split()) > 25,
        }
        return {
            "id": f"{source}:{identity}",
            "provider_id": identity,
            "source": source,
            "title": title[:2000],
            "authors": authors[:3000],
            "structured_authors": [
                plain(a.get("fullName"))
                for a in row.get("authorList", {}).get("author", [])
                if plain(a.get("fullName"))
            ][:100],
            "year": year,
            "doi": doi,
            "pmcid": pmcid,
            "journal": plain(row.get("journalInfo", {}).get("journal", {}).get("title"))[:500],
            "url": f"https://europepmc.org/article/{source}/{identity}",
            "identity_status": "provider_metadata_checked",
            "publication_status": status,
            "publication_notices": notices,
            "study_design": row.get("pubTypeList", {}).get("pubType", []),
            "access": "abstract_only" if abstract else "metadata_only",
            "license": "No reuse permission asserted for abstract.",
            "passages": [passage] if quote else [],
            "warnings": [],
            "metadata_sha256": sha(json.dumps(row, sort_keys=True).encode()),
        }

    def _full_text(self, paper, xml):
        # JATS declares an external DTD. Parse without fetching it; forbid
        # entities and external references rather than rejecting all JATS.
        root = ET.fromstring(xml, forbid_entities=True, forbid_external=True)
        article_ids = {
            n.get("pub-id-type"): plain(n.text) for n in root.findall(".//article-meta/article-id")
        }
        pmc = article_ids.get("pmcid", article_ids.get("pmc", "")).removeprefix("PMC")
        if pmc != paper["pmcid"].removeprefix("PMC") or (
            paper["doi"] and article_ids.get("doi", "").casefold() != paper["doi"]
        ):
            raise ValueError("Full text identity differs from bibliographic metadata")
        licenses = root.findall(".//article-meta/permissions/license")
        license_url = next(
            (
                v
                for license_node in licenses
                for n in license_node.iter()
                for v in n.attrib.values()
                if re.fullmatch(
                    r"https?://creativecommons.org/(?:licenses/by/(?:3\.0|4\.0)|publicdomain/zero/1\.0)/?",
                    v,
                )
            ),
            None,
        )
        if not license_url:
            paper["warnings"].append("full_text_permission_not_supported")
            return
        passages = []
        for sec in root.findall(".//body//sec"):
            heading = plain(" ".join(sec.findtext("title", "").split()))
            for p in sec.findall("p"):
                value = plain(" ".join(p.itertext()))
                if not value or len(value) > 6000 or INSTRUCTIONS.search(value):
                    continue
                passages.append(
                    {
                        "id": f"{paper['id']}:full:{len(passages)}",
                        "section": heading or "Body",
                        "text": value,
                        "fragment": False,
                    }
                )
                if len(passages) >= 18:
                    break
            if len(passages) >= 18:
                break
        paper.update(
            access="permitted_full_text_inspected",
            license=license_url,
            full_text_sha256=sha(xml),
            passages=passages,
        )
        paper["warnings"].append(
            "Selected passages extracted from full text; critical appraisal and contradictions are not assessed."
        )


def eligible(paper):
    return (
        paper["identity_status"] == "provider_metadata_checked"
        and paper["publication_status"] == "notices_not_reported_by_provider"
        and bool(paper["passages"])
    )


def evidence_row(paper):
    def field(pattern):
        passage = next(
            (
                p
                for p in paper["passages"]
                if not p["fragment"] and re.search(pattern, p["section"], re.I)
            ),
            None,
        )
        return (
            {"text": passage["text"], "passage_id": passage["id"]}
            if passage
            else {"text": MISSING, "passage_id": None}
        )

    return {
        "paper_id": paper["id"],
        "title": paper["title"],
        "access": paper["access"],
        "question": field("objective|aim|purpose"),
        "study_design": paper["study_design"] or ["Not specified by provider"],
        "population_model": field("population|participant|patient|animal"),
        "methods": field("method|material"),
        "findings": field("result|finding"),
        "limitations": field("limitation"),
        "applicability": "Not assessed; no clinical recommendation or consensus inferred.",
        "supporting_passages": paper["passages"],
    }


def validate_project(project):
    papers = {p["id"]: p for p in project["papers"]}
    for row in project["evidence_table"]:
        paper = papers.get(row["paper_id"])
        if not paper or not eligible(paper):
            raise ValueError("Ineligible evidence identity")
        passages = {p["id"]: p["text"] for p in paper["passages"]}
        for name in ("question", "population_model", "methods", "findings", "limitations"):
            field = row[name]
            if field["passage_id"] and passages.get(field["passage_id"]) != field["text"]:
                raise ValueError("Evidence field changed its source passage")
            if not field["passage_id"] and field["text"] != MISSING:
                raise ValueError("Unsupported evidence field")
    return {
        "bibliography": "provider_metadata_checked",
        "claim_bindings": "exact_passage_checks_passed",
        "medical_accuracy": "not_independently_assessed",
        "critical_appraisal": "pending",
        "clinical_review": "pending",
        "release_eligibility": "development_pilot",
    }


def md(value):
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", str(value)).replace("\n", " ")


def export_markdown(project):
    validate_project(project)
    search = project["search"]
    lines = [
        "# " + md(project["question"]),
        "",
        "Editable review scaffold — not a completed or systematic review.",
        "",
        "## Scope and reproducible search",
        "",
        f"Population/context: {md(project['population'])}",
        f"Article intent: {md(project['article_type'])}",
        f"Provider: Europe PMC; {search['date_utc']}",
        "Query: " + md(search["query"]),
        f"Received {search['received']} records from the first page; retained {len(project['papers'])} bibliographic identities.",
        "Limited single-provider search. " + search["screening"],
        "Inclusion: " + md(search["inclusion"] or "Not specified"),
        "Exclusion: " + md(search["exclusion"] or "Not specified"),
        "",
        "## Introduction",
        "",
        "[Write the background using inspected, cited sources. Do not infer medical consensus from this search.]",
        "",
        "## Evidence by study",
        "",
    ]
    for row in project["evidence_table"]:
        paper = next(p for p in project["papers"] if p["id"] == row["paper_id"])
        lines += [
            "### " + md(paper["title"]),
            "",
            f"[{md(paper['id'])}]({paper['url']}) · {md(paper['access'])} · {md(paper['license'])}",
            "",
        ]
        for name in ("question", "population_model", "methods", "findings", "limitations"):
            field = row[name]
            lines.append(
                f"**{name.replace('_', ' ').title()}:** {md(field['text'])}"
                + (f" [{md(field['passage_id'])}]" if field["passage_id"] else "")
            )
        if paper["access"] == "abstract_only":
            lines += ["", "Abstract fragment only; full methods/results were not reviewed."]
        lines += ["", "**Supporting passages:**", ""]
        for passage in row["supporting_passages"]:
            lines += [
                f"[{md(passage['id'])}] {md(passage['section'])}"
                + (" (incomplete fragment)" if passage["fragment"] else ""),
                "",
                md(passage["text"]),
                "",
            ]
        lines += ["", "Applicability: " + row["applicability"], ""]
    lines += [
        "## Discussion and critical appraisal",
        "",
        "[Assess design, bias, population, uncertainty and contradictions in the original papers. Keep differing results separate.]",
        "",
        "## Conclusion",
        "",
        "[No clinical recommendation, pooled estimate or original results have been generated.]",
        "",
        "## References",
        "",
    ]
    for p in project["papers"]:
        lines += [
            f"- {md(p['authors'])} ({p['year']}). {md(p['title'])}. {md(p['journal'])}. DOI: {md(p['doi'] or 'not supplied')}. {p['url']} · {p['publication_status']}"
        ]
    lines += [
        "",
        "Medical accuracy and faculty review are not independently assessed. Check authorship, AI disclosure, ethics, institutional and journal requirements before submission.",
        "",
    ]
    if project.get("user_draft"):
        lines += [
            "## Your edited draft — unverified user writing",
            "",
            "This section has not passed claim-to-evidence or medical accuracy checks. Saving it does not validate results, ethics approval or citations.",
            "",
            project["user_draft"],
            "",
        ]
    return "\n".join(lines)


def export_bibtex(project):
    def clean(value):
        return re.sub(r"[{}\\\r\n]", " ", str(value))

    return "\n\n".join(
        "@article{aster"
        + str(i + 1)
        + ",\n"
        + ",\n".join(
            f"  {k} = {{{clean(v)}}}"
            for k, v in dict(
                title=p["title"],
                author=" and ".join(
                    p.get("structured_authors")
                    or [a.strip() for a in p["authors"].split(",") if a.strip()]
                ),
                year=p["year"],
                journal=p["journal"],
                doi=p["doi"],
                url=p["url"],
            ).items()
        )
        + "\n}"
        for i, p in enumerate(project["papers"])
    )
