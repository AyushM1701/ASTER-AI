"""Bounded, resumable Europe PMC collection. Outputs remain STAGED; no app imports.

Run with .venv/Scripts/python.exe -m scripts.mds_open_collect --dry-run,
then without --dry-run. --stage report/export rebuilds derived outputs offline.
Dependency: defusedxml==0.7.1 (already pinned in requirements.txt).
"""
import argparse
import csv
import hashlib
import http.client
import io
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
ALLOWED_HOSTS = {"www.ebi.ac.uk"}
XLINK = "{http://www.w3.org/1999/xlink}href"
STAGES = ["discover", "verify-rights", "download", "extract", "deduplicate", "quality-check", "export", "report"]
FACETS = {
    "mechanisms": r"mechanism|pathogenesis|molecular|physiolog",
    "classification": r"classif|categor|taxonomy",
    "clinical_features": r"clinical features|clinical presentation|signs and symptoms",
    "diagnosis": r"diagnos|investigation|screening",
    "imaging_histology": r"histolog|radiograph|tomograph|imaging|microscop",
    "differentials": r"differential",
    "treatment_evidence": r"treatment|therap|management|intervention",
    "outcomes": r"outcome|prognos|survival",
    "complications": r"complication|adverse|failure",
    "laboratory_methods": r"laboratory|protocol|assay",
    "research_methods": r"method|systematic review|meta.analysis|statistic",
    "controversies": r"controvers|uncertain|limitation|debate",
}
FOUNDATIONS = [
    ("head_neck_anatomy", "Head and neck anatomy", "head AND neck AND anatomy"),
    ("embryology", "Embryology", "craniofacial AND embryology"),
    ("oral_dental_histology", "Oral and dental histology", "oral AND dental AND histology"),
    ("physiology", "Physiology", "salivary AND physiology"),
    ("biochemistry", "Biochemistry", "dental AND biochemistry"),
    ("general_pathology", "General pathology", "cell AND death AND pathology"),
    ("microbiology", "Microbiology", "oral AND microbiology"),
    ("immunology", "Immunology", "oral AND immunology"),
    ("pharmacology", "Pharmacology", "dental AND pharmacology"),
    ("dental_materials", "Dental materials", "dental AND materials"),
    ("genetics", "Genetics", "tooth AND genetics"),
    ("molecular_biology", "Molecular biology", "oral AND molecular AND biology"),
    ("research_methods", "Research methods", "dental AND research AND methods"),
    ("epidemiology", "Epidemiology", "dental AND epidemiology"),
    ("biostatistics", "Biostatistics", "dental AND biostatistics"),
    ("evidence_appraisal", "Evidence appraisal", "dentistry AND evidence AND appraisal"),
    ("ethics", "Ethics", "dental AND ethics"),
    ("forensic_odontology", "Forensic odontology", "forensic AND odontology"),
]
CANONICAL = {
    "oral_pathology": "Oral and Maxillofacial Pathology and Oral Microbiology",
    "oral_medicine": "Oral Medicine and Radiology",
    "oral_surgery": "Oral and Maxillofacial Surgery",
    "endodontics": "Conservative Dentistry and Endodontics",
    "prosthodontics": "Prosthodontics and Crown & Bridge",
    "periodontology": "Periodontology",
    "orthodontics": "Orthodontics and Dentofacial Orthopaedics",
    "pediatric_dentistry": "Pediatric and Preventive Dentistry",
    "public_health": "Public Health Dentistry",
    "foundations": "Shared foundations",
}
ALIASES = {"periodontics": "periodontology", "paediatric_dentistry": "pediatric_dentistry", "pedodontics": "pediatric_dentistry", "public_health_dentistry": "public_health", "oral_medicine_radiology": "oral_medicine", "conservative_endodontics": "endodontics", "oral_maxillofacial_surgery": "oral_surgery"}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def normalized(node):
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip() if node is not None else ""


def safe_path(base, name):
    base = Path(base).resolve()
    if Path(name).is_absolute() or re.match(r"^[A-Za-z]:", str(name)):
        raise ValueError("Absolute storage name")
    path = (base / name).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Storage path traversal")
    return path


def atomic_bytes(path, raw, immutable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Attempt to replace immutable source version")
        return
    part = path.with_name(path.name + ".part")
    try:
        with part.open("wb") as handle:
            handle.write(raw)
            handle.flush()
        part.replace(path)
    finally:
        part.unlink(missing_ok=True)


def checked_bytes(path, expected):
    if not Path(path).is_file():
        return None
    raw = Path(path).read_bytes()
    return raw if sha(raw) == expected else None


def json_write(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def jsonl_write(path, rows):
    atomic_bytes(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode())


def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443):
        raise ValueError("Unsafe URL scheme, credentials, fragment or port")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Unapproved download host")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Destination is not a public IP")
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        # Redirects are refused rather than escaping request accounting.
        raise ValueError("Redirect refused: use a verified canonical API endpoint")


class BudgetStop(RuntimeError):
    pass


class Budget:
    def __init__(self, config):
        self.config = config
        self.started = time.monotonic()
        self.requests = 0
        self.bytes = 0
        self.hosts = Counter()

    def check_time(self):
        if time.monotonic() - self.started >= self.config["max_seconds"]:
            raise BudgetStop("time_budget_reached")

    def request(self, host):
        self.check_time()
        if self.requests >= self.config["max_requests"] or self.hosts[host] >= self.config["per_host_requests"]:
            raise BudgetStop("request_budget_reached")
        self.requests += 1
        self.hosts[host] += 1

    def add_bytes(self, size):
        self.check_time()
        if self.bytes + size > self.config["max_bytes"]:
            raise BudgetStop("byte_budget_reached")
        self.bytes += size

    def usage(self):
        return {"requests": self.requests, "bytes_received": self.bytes, "elapsed_seconds": round(time.monotonic() - self.started, 2), "requests_by_host": dict(self.hosts)}


class Client:
    def __init__(self, budget, config, opener=None, sleep=time.sleep):
        self.budget, self.config = budget, config
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), SafeRedirect())
        self.sleep = sleep
        self.last = {}

    def fetch(self, url, expected):
        validate_url(url)
        host = urllib.parse.urlsplit(url).hostname
        for attempt in range(self.config.get("retries", 2) + 1):
            self.budget.check_time()
            delay = max(0, self.config.get("host_interval_seconds", .35) - (time.monotonic() - self.last.get(host, 0)))
            if delay:
                self.sleep(delay)
            self.budget.request(host)
            self.last[host] = time.monotonic()
            request = urllib.request.Request(url, headers={"User-Agent": "Aster-MDS-Staged-Collector/1.0", "Accept": "application/xml" if expected == "xml" else "application/json"})
            try:
                with self.opener.open(request, timeout=min(self.config.get("timeout_seconds", 25), max(1, self.budget.config["max_seconds"] - (time.monotonic() - self.budget.started)))) as response:
                    mime = response.headers.get("Content-Type", "").casefold()
                    if expected not in mime:
                        raise ValueError("Unexpected API media type")
                    length = response.headers.get("Content-Length")
                    limit = min(self.budget.config["max_file_bytes"], self.budget.config["max_bytes"] - self.budget.bytes)
                    if length and int(length) > limit:
                        raise ValueError("File size exceeds configured cap")
                    parts, size = [], 0
                    while True:
                        self.budget.check_time()
                        piece = response.read(min(65536, max(1, limit - size + 1)))
                        if not piece:
                            break
                        self.budget.add_bytes(len(piece))
                        size += len(piece)
                        if size > limit:
                            raise ValueError("File size exceeds configured cap")
                        parts.append(piece)
                    if length and size != int(length):
                        raise ValueError("Interrupted response: size differs from Content-Length")
                    return b"".join(parts)
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403, 451):
                    raise ValueError(f"Access restriction HTTP {exc.code}; no bypass") from exc
                if exc.code not in (429, 500, 502, 503, 504) or attempt == self.config.get("retries", 2):
                    raise
                retry = exc.headers.get("Retry-After", "")
                try:
                    seconds = float(retry)
                except ValueError:
                    try:
                        seconds = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError):
                        seconds = 2 ** (attempt + 1)
                cap = self.config.get("max_retry_after_seconds", 30)
                if seconds > cap or seconds > self.budget.config["max_seconds"] - (time.monotonic() - self.budget.started):
                    raise ValueError("Retry-After exceeds bounded run; deferred") from exc
                self.sleep(max(0, seconds))
            except (OSError, TimeoutError, http.client.HTTPException):
                if attempt == self.config.get("retries", 2):
                    raise
                self.sleep(min(2 ** (attempt + 1), self.config.get("max_retry_after_seconds", 30)))
        raise RuntimeError("Unreachable retry state")


def license_id(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname not in {"creativecommons.org", "www.creativecommons.org"} or parsed.scheme not in {"http", "https"} or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/licenses/(by(?:-[a-z]+)*)/(1\.0|2\.0|2\.5|3\.0|4\.0)/?", parsed.path)
    if match:
        return "CC-" + match[1].upper() + "-" + match[2]
    if parsed.path.rstrip("/") == "/publicdomain/zero/1.0":
        return "CC0-1.0"
    return None


def extract_authors(article):
    authors = []
    for contrib in article.findall("./front/article-meta/contrib-group/contrib"):
        if contrib.get("contrib-type") != "author":
            continue
        name = contrib.find("name")
        value = " ".join(filter(None, (normalized(name.find(part)) for part in ("given-names", "surname", "suffix")))) if name is not None else normalized(contrib.find("collab"))
        if value:
            authors.append(value)
    return authors


def inspect_xml(raw, pmcid):
    try:
        article = SafeET.fromstring(raw)
    except (ET.ParseError, DefusedXmlException) as exc:
        raise ValueError("Malformed or unsafe XML") from exc
    if article.tag != "article":
        raise ValueError("Not a JATS article")
    original_coordinates = {}
    def coordinate_tree(node, path, depth=0):
        if depth > 80:
            raise ValueError("XML depth exceeds extraction cap")
        if len(original_coordinates) >= 100000:
            raise ValueError("XML node count exceeds extraction cap")
        original_coordinates[id(node)] = node.get("aster-source-coordinate", path)
        node.set("aster-source-coordinate", original_coordinates[id(node)])
        counts = Counter()
        for child in node:
            counts[child.tag] += 1
            coordinate_tree(child, path + f"/{child.tag}[{counts[child.tag]}]", depth + 1)
    coordinate_tree(article, "/article")
    ids = {normalized(n).removeprefix("PMC") for n in article.findall("./front/article-meta/article-id") if n.get("pub-id-type") in {"pmc", "pmcid"}}
    if not re.fullmatch(r"PMC\d+", pmcid) or pmcid.removeprefix("PMC") not in ids:
        raise ValueError("Article identifier mismatch")
    permissions = article.findall("./front/article-meta/permissions")
    notices = " ".join(normalized(n) for n in permissions)
    license_nodes = [n for p in permissions for n in p.findall(".//license")]
    urls = [n.get(XLINK) or n.get("href") for n in license_nodes]
    urls += [n.get(XLINK) or n.get("href") for p in permissions for n in p.findall(".//ext-link")]
    # Some authoritative JATS notices encode the canonical license as plain
    # text rather than an href. Preserve the notice and verify its exact URL.
    urls += re.findall(r"https?://(?:www\.)?creativecommons\.org/(?:licenses/[a-z-]+/[0-9.]+/?|publicdomain/zero/1\.0/?)", notices)
    identifiers = {license_id(u) for u in urls if u and license_id(u)}
    unrecognized = any((n.get(XLINK) or n.get("href")) and not license_id(n.get(XLINK) or n.get("href")) for n in license_nodes)
    reason, track = None, "default"
    if len(identifiers) > 1:
        reason = "license_conflict"
    elif not identifiers or unrecognized:
        reason = "unknown_or_ambiguous_license"
    identity = next(iter(identifiers), None)
    if identity and ("-NC" in identity or "-ND" in identity):
        reason = reason or "noncommercial_or_no_derivatives_excluded"
    if re.search(r"all rights reserved|no derivatives|non.commercial", notices, re.I) and identity and "-NC" not in identity and "-ND" not in identity:
        reason = "license_conflict_notice"
    # Ancillary reuse restrictions cannot be overridden by a familiar badge.
    extra_rights = " ".join(normalized(n) for n in article.findall(".//custom-meta-group"))
    if re.search(r"(?:AI|artificial intelligence|machine learning).{0,120}(?:prohibit|not permitted|not allowed)|(?:prohibit|not permitted|not allowed).{0,120}(?:AI training|artificial intelligence|machine learning)", notices + " " + extra_rights, re.I):
        reason = "additional_ai_reuse_restriction"
    if any(re.search(r"retract|withdraw|correct|concern", n.get("related-article-type", ""), re.I) for n in article.findall(".//related-article")):
        reason = "related_editorial_notice_requires_review"
    if re.search(r"retract|withdraw|correct|concern", article.get("article-type", ""), re.I):
        reason = "article_editorial_notice_requires_review"
    if reason:
        track = "excluded"
    elif identity and "-SA" in identity:
        track = "conditional"
        reason = "sharealike_obligations_pending"
    assets, retain, detached = [], True, set()
    for parent in list(article.iter()):
        if id(parent) in detached:
            continue
        for child in list(parent):
            if child.tag in {"fig", "table-wrap", "supplementary-material", "media", "boxed-text", "graphic", "inline-graphic"}:
                own = {license_id(n.get(XLINK) or n.get("href") or "") for n in child.findall(".//permissions/license")}
                if own != {identity} or track != "default":
                    retain = False
                    assets.append(child.tag + ":" + child.get("id", "unnumbered"))
                    detached.update(id(n) for n in child.iter())
                    parent.remove(child)
    # Prose paragraphs with local third-party credit are withheld as well.
    for parent in list(article.iter()):
        for child in list(parent):
            if child.tag == "p" and re.search(r"reproduced (?:from|with)|reprinted (?:from|with)|copyright permission|used with permission", normalized(child), re.I):
                retain = False
                assets.append("credited_paragraph:" + child.get("id", "unnumbered"))
                parent.remove(child)
    sections = []
    def walk(node, coordinate, headings):
        local_heading = normalized(node.find("title"))
        headings = headings + [local_heading] if local_heading else headings
        counts = Counter()
        for child in node:
            counts[child.tag] += 1
            child_path = original_coordinates.get(id(child), coordinate + f"/{child.tag}[{counts[child.tag]}]")
            child_path = child_path.replace("/article/body[1]/", "/article/body/")
            if child.tag == "p":
                value = normalized(child)
                if value:
                    sections.append({"heading": headings, "coordinate": child_path, "page": None, "text": value, "source_char_start": 0, "source_char_end": len(value)})
            elif child.tag == "table-wrap":
                table = child.find("table")
                if table is not None:
                    headers = [[normalized(cell) for cell in tr if cell.tag in {"th", "td"}] for tr in table.findall("./thead/tr")]
                    rows = [[normalized(cell) for cell in tr if cell.tag in {"th", "td"}] for tr in table.findall("./tbody/tr") or table.findall("./tr")]
                    value = "\n".join("\t".join(row) for row in headers + rows)
                    if value and headers and all(len(row) == len(headers[-1]) for row in rows):
                        sections.append({"heading": headings, "coordinate": child_path + "/table[1]", "page": None, "text": value, "source_char_start": 0, "source_char_end": len(value), "kind": "table", "table": {"headers": headers, "rows": rows, "caption": normalized(child.find("caption")), "footnotes": normalized(child.find("table-wrap-foot"))}})
            elif child.tag in {"sec", "list", "list-item", "statement"}:
                walk(child, child_path, headings)
    body = article.find("body")
    if body is None:
        raise ValueError("No article body")
    walk(body, "/article/body", [])
    if not sections:
        raise ValueError("No eligible article-body prose")
    return {"track": track, "reason": reason, "license": identity, "license_url": next((u for u in urls if u and license_id(u) == identity), None), "license_notices": notices, "license_evidence_xml": "\n".join(ET.tostring(n, encoding="unicode") for n in permissions), "retain_original": retain, "omitted_assets": assets, "sections": sections, "sanitized_xml": ET.tostring(article, encoding="utf-8"), "title": normalized(article.find("./front/article-meta/title-group/article-title")), "references": [normalized(n) for n in article.findall("./back/ref-list/ref")], "authors": extract_authors(article)}


def deduplicate(rows):
    parent = {r["id"]: r["id"] for r in rows}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    seen = {}
    for row in rows:
        for field in ("doi", "pmcid", "text_hash", "raw_sha256"):
            value = row.get(field)
            if value:
                key = (field, str(value).casefold())
                if key in seen:
                    parent[find(row["id"])] = find(seen[key])
                seen[key] = row["id"]
    # Compare near-identical normalized prose at document level; clinical shared
    # vocabulary alone is insufficient (minimum 1000 chars and 97% similarity).
    shingles = {}
    for row in rows:
        tokens = row.get("normalized_text", "").split()
        shingles[row["id"]] = set(zip(*(tokens[i:] for i in range(5)))) if len(tokens) >= 5 else set()
    for i, a in enumerate(rows):
        for b in rows[:i]:
            at, bt = a.get("normalized_text", ""), b.get("normalized_text", "")
            sa, sb = shingles[a["id"]], shingles[b["id"]]
            plausible = bool(sa and sb) and len(sa & sb) / len(sa | sb) >= .75
            if plausible and min(len(at), len(bt)) >= 1000 and min(len(at), len(bt)) / max(len(at), len(bt)) > .9 and SequenceMatcher(None, at, bt, autojunk=True).ratio() >= .97:
                parent[find(a["id"])] = find(b["id"])
    members = defaultdict(list)
    for row in rows:
        members[find(row["id"])].append(row)
    for family in members.values():
        winner = min(r["id"] for r in family)
        fid = "family-" + sha(winner.encode())[:16]
        split = "evaluation_holdout" if int(sha(fid.encode())[:8], 16) % 10 == 0 else "training_candidate"
        for row in family:
            row.update(version_family_id=fid, split=split, duplicate_of=None if row["id"] == winner else winner)
    return rows


def snapshot_valid(doc, output):
    raw = checked_bytes(safe_path(output, doc["stored_document_path"]), doc["stored_sha256"])
    if raw is None:
        return False
    extracted_path = safe_path(output, doc["extracted_path"])
    if not extracted_path.is_file():
        return False
    if doc.get("extracted_sha256") and checked_bytes(extracted_path, doc["extracted_sha256"]) is None:
        return False
    return True


def topics(config):
    source = json.loads(safe_path(ROOT, config["taxonomy"]).read_text(encoding="utf-8"))
    groups = []
    for specialty in source["specialties"]:
        identity = ALIASES.get(specialty["id"], specialty["id"])
        if identity not in CANONICAL:
            # Older editorial taxonomy IDs are mapped using the specialty name.
            text = specialty["title"].casefold()
            identity = next((k for k in CANONICAL if k != "foundations" and (k.replace("_", " ") in text or (k == "endodontics" and "endodont" in text) or (k == "oral_surgery" and "surgery" in text) or (k == "oral_medicine" and "radiology" in text) or (k == "oral_pathology" and "pathology" in text) or (k == "pediatric_dentistry" and "pedo" in text))), identity)
        if identity not in CANONICAL:
            raise ValueError(f"Unknown specialty taxonomy: {identity}")
        groups.append([{**t, "specialty_id": identity, "specialty": CANONICAL[identity], "scope_status": "provisional_topic_map_over_verified_2017_national_base"} for t in specialty["topics"]])
    groups.append([{"id": "FOUNDATION-" + k, "title": title, "query": q, "specialty_id": "foundations", "specialty": CANONICAL["foundations"], "scope_status": "provisional_shared_foundation_map"} for k, title, q in FOUNDATIONS])
    # First one topic per specialty, then fill topic gaps round-robin.
    return [group[i] for i in range(max(map(len, groups))) for group in groups if i < len(group)]


def query_for(topic):
    base = topic["query"]
    if topic["specialty_id"] == "pediatric_dentistry":
        base = f"({base}) OR (pedodontics AND ({base}))"
    query = f"({base}) AND OPEN_ACCESS:Y AND PUB_TYPE:review"
    if topic.get("require_title_anchors"):
        generic = {"oral", "dental", "dentistry", "and", "of", "the", "in", "health"}
        words = [w for w in re.findall(r"[a-z]+", topic["title"].lower()) if w not in generic]
        if words:
            query += " AND (" + " OR ".join("TITLE:" + w for w in words) + ")"
    return query


def search_url(topic, config):
    return API + "search?" + urllib.parse.urlencode({"query": query_for(topic), "format": "json", "pageSize": config["page_size"], "resultType": "core", "cursorMark": "*"})


def candidate_reason(row):
    if not re.fullmatch(r"PMC\d+", row.get("pmcid", "")):
        return "missing_valid_pmc_identifier"
    if row.get("isOpenAccess") != "Y":
        return "not_authorized_open_access_subset"
    if row.get("commentCorrectionList") or re.search(r"retract\w*|withdraw\w*|corrigendum|erratum|expression of concern", row.get("title", ""), re.I):
        return "editorial_notice_requires_review"
    publication = " ".join(row.get("pubTypeList", {}).get("pubType", [])).casefold()
    if "preprint" in publication:
        return "preprint_not_in_initial_review_track"
    license_hint = str(row.get("license", "")).casefold()
    if "nc" in license_hint or "nd" in license_hint:
        return "authoritative_metadata_nc_nd_exclusion"
    return None


def relevance(title, topic):
    stop = {"and", "oral", "dental", "dentistry", "tooth", "teeth", "health", "of", "in", "the"}
    anchors = {w[:6] for w in re.findall(r"[a-z]+", topic["title"].casefold()) if w not in stop}
    present = {w[:6] for w in re.findall(r"[a-z]+", title.casefold())}
    if topic.get("specialty_id") != "foundations" and not re.search(r"\b(?:dent\w*|oral|tooth|teeth|caries|endodont\w*|periodont\w*|orthodont\w*|prosthodont\w*|craniofacial|odontogen\w*|gingiv\w*|pulp\w*|mandib\w*|maxill\w*|occlus\w*|salivar\w*|palatal|mucosal)\b", title, re.I):
        return False
    return bool(anchors & present)


def resource_type(title):
    for pattern, label in [(r"consensus", "consensus_statement_title_indicated"), (r"umbrella review", "umbrella_review_title_indicated"), (r"systematic review|meta.analysis", "systematic_review_title_indicated"), (r"narrative review", "narrative_review_title_indicated")]:
        if re.search(pattern, title, re.I):
            return label
    if re.search(r"cohort study|cross.sectional|case.control|randomized controlled trial|case series|cephalometric analysis", title, re.I):
        return "primary_study_title_indicated"
    return "journal_review_design_unresolved"


def make_document(row, topic, inspected, raw, output, config):
    snapshot = sha(raw)
    identity = row["pmcid"].lower() + "-" + snapshot[:12]
    prose = "\n\n".join(s["text"] for s in inspected["sections"])
    text_norm = re.sub(r"\W+", " ", prose.casefold()).strip()
    flags = ["clinical_appraisal_pending", "editorial_notice_checks_partial", "human_population_not_independently_verified"]
    if inspected["omitted_assets"]:
        flags += ["assets_omitted", "table_coverage_unavailable"]
    if "�" in prose:
        flags.append("replacement_character_detected")
    quality = len(prose) >= config["minimum_prose_characters"] and "�" not in prose
    path = safe_path(output, ("raw/" if inspected["retain_original"] else "extracted/rights_screened_jats/") + identity + ".xml")
    atomic_bytes(path, raw if inspected["retain_original"] else inspected["sanitized_xml"], immutable=True)
    extracted_path = safe_path(output, "extracted/" + identity + ".json")
    json_write(extracted_path, {"id": identity, "sections": inspected["sections"], "references_separate": inspected["references"], "omitted_assets_notice": "Assets lacking independent compatible rights evidence omitted; original withheld when affected.", "extraction_method": "defusedxml-JATS-prose-v1", "original_sha256": snapshot})
    rights_path = safe_path(output, "rights_evidence/" + identity + ".json")
    source_url = f"https://europepmc.org/articles/{row['pmcid']}"
    attribution = "; ".join(inspected["authors"] or [row.get("authorString") or "Author metadata unavailable"]) + ". " + inspected["title"] + ". " + source_url + ". " + inspected["license"]
    evidence = {"pmcid": row["pmcid"], "source_url": source_url, "rights_evidence_url": API + row["pmcid"] + "/fullTextXML", "access_date": now(), "license": inspected["license"], "license_url": inspected["license_url"], "exact_notice": inspected["license_notices"], "permissions_xml": inspected["license_evidence_xml"], "article_sha256": snapshot, "omitted_assets": inspected["omitted_assets"], "asset_policy": config["assets"], "original_retained": inspected["retain_original"], "attribution": attribution, "source_review": "automated_rights_and_extraction_screen", "qualified_clinical_review": "pending"}
    json_write(rights_path, evidence)
    allowed = {"decision": "eligible_under_declared_conservative_policy", "evidence": str(rights_path.relative_to(output)), "conditions": "preserve attribution, individual license, omission notices and provenance"}
    uses = {k: dict(allowed) for k in ("automated_retrieval", "local_storage_eligible_prose", "text_extraction", "rag", "redistribution_eligible_prose")}
    uses["original_storage"] = {"decision": "eligible" if inspected["retain_original"] else "withheld", "reason": "asset-specific compatible rights evidence required"}
    uses["training"] = {"decision": "candidate_only" if quality else "withheld_quality", "reason": "rights screen is not training validation; clinical review and intended use review pending"}
    uses["derivative_examples"] = {"decision": "pending_not_generated", "reason": "synthetic examples optional; independent expert review required"}
    return {"id": identity, "title": inspected["title"], "authors": inspected["authors"] or None, "publication_date": row.get("firstPublicationDate"), "year": row.get("pubYear"), "journal": row.get("journalInfo", {}).get("journal", {}).get("title"), "publisher": None, "pmcid": row["pmcid"], "pmid": row.get("id") if row.get("source") == "MED" else None, "doi": row.get("doi"), "canonical_url": source_url, "download_url": API + row["pmcid"] + "/fullTextXML", "version": snapshot[:12], "retrieved_at": now(), "media_type": "application/xml", "original_byte_count": len(raw), "raw_sha256": snapshot, "stored_sha256": sha(path.read_bytes()), "original_retained": inspected["retain_original"], "original_path": str(path.relative_to(output)) if inspected["retain_original"] else None, "stored_document_path": str(path.relative_to(output)), "extracted_path": str(extracted_path.relative_to(output)), "rights_evidence_path": str(rights_path.relative_to(output)), "specialties": [topic["specialty_id"]], "shared_topic_labels": [topic["title"]] if topic["specialty_id"] == "foundations" else [], "curriculum_topic_ids": [topic["id"]], "facet_labels": [k for k, pattern in FACETS.items() if re.search(pattern, prose, re.I)], "facet_status": "automated_text_mentions_not_competency_assessment", "resource_type": "journal_review", "publication_types": row.get("pubTypeList", {}).get("pubType", []), "evidence_design": "review_design_unappraised", "language": row.get("language") or None, "audience": "MDS educational research", "population_context": "not_independently_appraised", "license": inspected["license"], "license_url": inspected["license_url"], "rights_evidence_date": now(), "attribution": attribution, "exclusions": inspected["omitted_assets"], "eligibility": uses, "editorial_checks": {"source": "EuropePMC_core_commentCorrectionList_and_JATS_related_article", "checked_at": now(), "status": "no_notice_in_checked_fields_publisher_check_unresolved", "supersession": "unresolved"}, "quality_flags": flags, "quality_pass": quality, "extraction_method": "defusedxml-JATS-prose-v1", "review_state": {"source": "automated_screen_only", "clinical": "pending", "faculty": "pending"}, "source_set_version": config["version"], "text_hash": sha(text_norm.encode()), "normalized_text": text_norm, "status": "STAGED"}


def export_report(state, config, output, topic_list):
    docs = deduplicate(list(state["documents"].values()))
    for doc in docs:
        doc["resource_type"] = resource_type(doc["title"])
        if doc["resource_type"] == "primary_study_title_indicated":
            doc["evidence_design"] = "primary_study_title_indicated_methods_unappraised"
            doc["quality_flags"] = sorted(set(doc["quality_flags"] + ["discovery_review_filter_does_not_guarantee_study_design"]))
        if not snapshot_valid(doc, output):
            doc["quality_pass"] = False
            doc["quality_flags"] = sorted(set(doc["quality_flags"] + ["snapshot_checksum_failure_or_missing"]))
    public = [{k: v for k, v in d.items() if k != "normalized_text"} for d in docs]
    jsonl_write(output / "manifests/catalogue.jsonl", public)
    json_write(output / "manifests/license_attribution.json", [{"id": d["id"], "license": d["license"], "attribution": d["attribution"], "rights_evidence_path": d["rights_evidence_path"], "exclusions": d["exclusions"], "eligibility": d["eligibility"]} for d in public])
    stream = io.StringIO(newline="")
    fields = ["id", "title", "pmcid", "doi", "canonical_url", "license", "specialties", "curriculum_topic_ids", "original_retained", "original_path", "quality_pass", "split", "eligibility"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for doc in public:
        writer.writerow({k: json.dumps(doc[k], ensure_ascii=False) if isinstance(doc.get(k), (dict, list)) else doc.get(k) for k in fields})
    atomic_bytes(output / "manifests/catalogue.csv", stream.getvalue().encode("utf-8-sig"))
    chunks, candidates, heldout = [], [], []
    for doc in docs:
        if doc["duplicate_of"] or not doc["quality_pass"]:
            continue
        extracted = json.loads(safe_path(output, doc["extracted_path"]).read_text(encoding="utf-8"))
        doc_chunks = []
        for number, section in enumerate(extracted["sections"], 1):
            # Keep exact paragraph support; long paragraphs split at exact offsets.
            unit_size = len(section["text"]) if section.get("kind") == "table" else 2200
            for start in range(0, len(section["text"]), max(1, unit_size)):
                exact = section["text"][start:start + unit_size]
                chunk = {"chunk_id": f'{doc["id"]}:p{number}:{start}', "document_id": doc["id"], "version_family_id": doc["version_family_id"], "parent_id": doc["id"] + ":" + section["coordinate"], "section_id": section["coordinate"], "section": " > ".join(section["heading"]), "text": exact, "heading_hierarchy": section["heading"], "coordinate": section["coordinate"], "source_char_start": start, "source_char_end": start + len(exact), "page": None, "specialties": doc["specialties"], "topic_ids": doc["curriculum_topic_ids"], "facet_labels": doc["facet_labels"], "source_url": doc["canonical_url"], "license": doc["license"], "attribution": doc["attribution"], "exclusions": doc["exclusions"], "clinical_review": "pending", "status": "STAGED", "split": doc["split"]}
                doc_chunks.append(chunk)
                if section.get("kind") == "table":
                    chunk["table"] = section["table"]
                    chunk["kind"] = "table"
        if doc["split"] == "evaluation_holdout":
            heldout.extend(doc_chunks)
        else:
            chunks.extend(doc_chunks)
            candidates.append({"document_id": doc["id"], "version_family_id": doc["version_family_id"], "text": "\n\n".join(s["text"] for s in extracted["sections"]), "license": doc["license"], "attribution": doc["attribution"], "source_url": doc["canonical_url"], "exclusions": doc["exclusions"], "eligibility": "rights_screened_candidate_not_validated_training_data", "clinical_review": "pending", "status": "STAGED", "split": doc["split"]})
    jsonl_write(output / "rag_chunks/staged_rag.jsonl", chunks)
    jsonl_write(output / "training_candidates/rights_screened_candidates.jsonl", candidates)
    jsonl_write(output / "evaluation_holdout/source_chunks.jsonl", heldout)
    jsonl_write(output / "metadata_only_exclusions/exclusions.jsonl", [d for d in state["decisions"] if d["status"] in {"excluded", "conditional", "failed"}])
    jsonl_write(output / "manifests/decisions.jsonl", state["decisions"])
    jsonl_write(output / "manifests/searches.jsonl", state["searches"])
    coverage = []
    for topic in topic_list:
        associated = [d for d in docs if topic["id"] in d["curriculum_topic_ids"] and not d["duplicate_of"]]
        for facet in FACETS:
            hits = [d["id"] for d in associated if facet in d["facet_labels"]]
            coverage.append({"topic_id": topic["id"], "topic": topic["title"], "specialty": topic["specialty_id"], "facet": facet, "documents": hits, "status": "partial_material_review_pending" if hits else "missing_material", "curriculum_status": topic["scope_status"], "official_syllabus_section": CANONICAL[topic["specialty_id"]] if topic["specialty_id"] != "foundations" else "Applied basic sciences; research methods", "mapping_status": "provisional_topic_and_facet_association_not_line_by_line_syllabus_reconciliation", "qualified_clinical_review": "pending"})
    jsonl_write(output / "curriculum/topic_facet_matrix.jsonl", coverage)
    json_write(output / "curriculum/national_scope.json", {"base_url": "https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf", "status": "official_2017_base_verified_by_project_curriculum_registry", "current_consolidated": "amendment_reconciliation_pending", "university_overlay": "not_requested_national_only", "syllabus_rights": "scope_citation_only_no_full_text_export", "canonical_specialties": CANONICAL, "topics": topic_list})
    counts = {"discovered_candidate_records": sum(s.get("candidate_count", 0) for s in state["searches"]), "rights_inspected_xml": state.get("rights_inspected_xml", 0), "rights_verified_default": len(docs), "downloaded_authorized_originals_retained": sum(d["original_retained"] for d in docs), "originals_withheld_assets": sum(not d["original_retained"] for d in docs), "extracted": len(docs), "deduplicated_unique_families": sum(not d["duplicate_of"] for d in docs), "rag_exported_documents": len({c["document_id"] for c in chunks}), "rag_chunks": len(chunks), "training_candidate_documents": len(candidates), "evaluation_holdout_documents": len({c["document_id"] for c in heldout}), "rejected_or_metadata_quarantined": sum(d["status"] == "excluded" for d in state["decisions"]), "conditional_metadata_only": sum(d["status"] == "conditional" for d in state["decisions"]), "failures": len(state["failures"]), "clinical_review_pending": len(docs), "faculty_reviewed": 0}
    summary = {"status": "STAGED", "generated_at": now(), "counts": counts, "by_specialty": dict(Counter(s for d in docs if not d["duplicate_of"] for s in d["specialties"])), "by_license": dict(Counter(d["license"] for d in docs)), "by_resource_type": dict(Counter(d["resource_type"] for d in docs)), "usage": state.get("usage", {}), "limits": config, "stop_reason": state.get("stop_reason"), "disk_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()), "source_gaps": ["Initial source family Europe PMC JATS, review-focused queries; open textbooks/chapters, authoritative guidelines, licensed atlases and deliberate balanced primary-study collection remain gaps", "Tables, figures, captions and supplements without independent compatible asset license evidence omitted", "No PDF/OCR files in this source pack; no OCR validation claimed", "Current national amendments and fine-grained syllabus mapping pending reconciliation", "Clinical evidence appraisal, applicability and independent faculty review pending"], "priority_next_topics": [{"topic_id": t["id"], "title": t["title"], "specialty": t["specialty_id"]} for t in topic_list if not any(t["id"] in d["curriculum_topic_ids"] for d in docs)], "checks": ["pmcid identity", "authoritative JATS license URLs/notices", "NC/ND/unknown/conflicts exclusion", "asset omission", "XML entity protection", "checksum and version immutable storage", "exact paragraph coordinates", "core/JATS editorial notice screening; publisher checks unresolved", "document/version and normalized near-duplicate split grouping"], "failures": state["failures"]}
    json_write(output / "reports/checkpoint.json", summary)
    card = f'''# Aster staged MDS open corpus\n\nGenerated {summary["generated_at"]}. National scope only. **STAGED**: no application index imports, training, uploads or publication.\n\n{json.dumps(counts, indent=2)}\n\n## Sources and permissions\n\nEurope PMC REST OA JATS only. CC0/CC BY compatible versions admitted; CC BY-SA metadata held conditional; NC/ND/unknown/conflicting statements excluded. Exact per-item notices, URLs, dates and attribution in rights_evidence. Articles inspected transiently for rights; rejected XML never retained. Raw originals stored only where no unresolved assets. Sanitized JATS is a derivative, not an original. Asset and credited-paragraph omissions accompany every derivative. No blanket dataset license supersedes item licenses.\n\n## Quality and intended use\n\nEducational research retrieval and future rights-screened training candidacy. Automated source and extraction screening does not assess medical correctness. Every item awaits independent qualified clinical/faculty review. Review type, populations, methods, conflicts and limitations need individual appraisal. Older papers are not current guidance. No synthetic examples generated. No identifiable patient records deliberately collected.\n\n## Curriculum and gaps\n\nOfficial 2017 national base cited for scope; current consolidated amendments and fine mapping pending. Editorial topic labels are provisional associations. No university overlay. Source discovery emphasizes indexed journal reviews, with title-indicated primary studies distinguished because review-index metadata can be inconsistent. Foundation chapters, current official guidelines, licensed atlases, eligible tables, OCR and deliberate primary-study balance remain gaps. Topic/facet matrix distinguishes partial association from missing cells.\n\n## Splits\n\nDocument/version-family and near-duplicate splits. Evaluation source chunks are withheld from staged RAG and training candidates, with no benchmark answers generated. RAG and training candidates share training-split documents, explicitly; no source-unseen claim.\n\n## Reproduce\n\nRun `.venv/Scripts/python.exe -m scripts.mds_open_collect --dry-run`, then without dry-run. Offline `--stage report` rebuilds exports/report. Dependencies: Python 3.13 and defusedxml==0.7.1 from project requirements. Resumes checksum-verified originals/sanitized versions and immutable search caches. Interrupted downloads restart bounded item fetch; no partial original is retained. Request/byte/time caps are per invocation and recorded; document cap applies to accumulated admitted versions. No archives downloaded.\n\nBudget and actual usage: {json.dumps(summary["usage"])}. Stop: {summary["stop_reason"]}. Disk at report generation: {summary["disk_bytes"]} bytes. Failure details in reports/checkpoint.json.\n'''
    atomic_bytes(output / "README.md", card.encode())
    atomic_bytes(output / "reports/data_card.md", card.encode())
    return summary


def collect(config, dry_run=False, stage="all"):
    output = safe_path(ROOT, config["output"])
    topic_list = topics(config)
    if dry_run:
        plan = {"status": "dry_run_no_network_or_writes", "stages": STAGES, "budget": config, "topic_count": len(topic_list), "queries_first_round": [{"topic": t["id"], "query": query_for(t)} for t in topic_list[:10]], "source_api": API, "university_overlay": "not_requested_national_only"}
        print(json.dumps(plan, indent=2))
        return plan
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / "manifests/state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"documents": {}, "searches": [], "decisions": [], "failures": [], "rights_inspected_xml": 0}
    if stage in {"deduplicate", "quality-check", "export", "report"}:
        return export_report(state, config, output, topic_list)
    client = Client(Budget(config), config)
    schedule = topic_list
    if config.get("gap_fill"):
        missing = [t for t in topic_list if not any(t["id"] in d["curriculum_topic_ids"] for d in state["documents"].values())]
        specialty_counts = Counter(s for d in state["documents"].values() for s in d["specialties"])
        schedule = sorted(missing, key=lambda t: (specialty_counts[t["specialty_id"]], t["id"]))
        schedule = [{**t, "require_title_anchors": True} for t in schedule]
    attempted = {(d["topic_id"], d.get("pmcid")) for d in state["decisions"]}
    searches_done = set(state.get("completed_topics", [d["topic_id"] for d in state["decisions"]]))
    if config.get("gap_fill"):
        searches_done = set()
    state["stop_reason"] = "topic_schedule_complete"
    try:
        for topic in schedule:
            if len(state["documents"]) >= config["max_documents"]:
                state["stop_reason"] = "document_budget_reached"
                break
            client.budget.check_time()
            if topic["id"] in searches_done:
                continue
            query = query_for(topic)
            url = search_url(topic, config)
            cache = output / "search_cache" / (sha(url.encode()) + ".json")
            cache_hash = cache.with_suffix(".sha256")
            try:
                cached = checked_bytes(cache, cache_hash.read_text().strip()) if cache_hash.exists() else None
                raw_search = cached or client.fetch(url, "json")
                result = json.loads(raw_search)
                if not cached:
                    atomic_bytes(cache, raw_search, immutable=True)
                    atomic_bytes(cache_hash, sha(raw_search).encode(), immutable=True)
                rows = result.get("resultList", {}).get("result", [])
                search = {"topic_id": topic["id"], "specialty": topic["specialty_id"], "query": query, "api": "EuropePMC_REST", "url": url, "date": now(), "filters": {"open_access": True, "publication_type": "review", "date_cutoff": None}, "pagination": {"cursor": "*", "next": result.get("nextCursorMark"), "page_size": config["page_size"], "pages_fetched": 1}, "hit_count": result.get("hitCount"), "candidate_count": len(rows), "snapshot_path": str(cache.relative_to(output)), "snapshot_sha256": sha(raw_search), "status": "discovered"}
                state["searches"].append(search)
                if stage == "discover":
                    continue
                admitted = 0
                for row in rows[:config["candidates_per_topic"]]:
                    pmcid = row.get("pmcid")
                    if (topic["id"], pmcid) in attempted:
                        continue
                    decision = {"topic_id": topic["id"], "specialty": topic["specialty_id"], "pmcid": pmcid, "title": row.get("title"), "doi": row.get("doi"), "canonical_url": f"https://europepmc.org/articles/{pmcid}" if pmcid else None, "checked_at": now(), "original_retained": False}
                    reason = candidate_reason(row)
                    if not reason and not relevance(row.get("title", ""), topic):
                        reason = "no_specific_topic_title_anchor"
                    existing = next((d for d in state["documents"].values() if d["pmcid"] == pmcid), None)
                    if existing and not reason:
                        existing["specialties"] = sorted(set(existing["specialties"] + [topic["specialty_id"]]))
                        existing["curriculum_topic_ids"] = sorted(set(existing["curriculum_topic_ids"] + [topic["id"]]))
                        if topic["specialty_id"] == "foundations":
                            existing["shared_topic_labels"] = sorted(set(existing["shared_topic_labels"] + [topic["title"]]))
                        state["decisions"].append({**decision, "status": "associated_existing", "document_id": existing["id"]})
                        admitted += 1
                    elif reason:
                        state["decisions"].append({**decision, "status": "excluded", "reason": reason})
                    else:
                        try:
                            raw = client.fetch(API + pmcid + "/fullTextXML", "xml")
                            state["rights_inspected_xml"] += 1
                            inspected = inspect_xml(raw, pmcid)
                            if row.get("license"):
                                hint = str(row["license"]).lower().replace("-", "").replace(" ", "")
                                verified = (inspected["license"] or "").lower().replace("-", "")
                                if hint.startswith("cc") and not verified.startswith(hint):
                                    inspected.update(track="excluded", reason="discovery_authoritative_license_conflict")
                            if inspected["track"] != "default":
                                state["decisions"].append({**decision, "status": inspected["track"], "reason": inspected["reason"], "license": inspected["license"], "rights_evidence_url": API + pmcid + "/fullTextXML", "license_notice": inspected["license_notices"], "original_sha256": sha(raw), "fulltext_discarded": True})
                            else:
                                doc = make_document(row, topic, inspected, raw, output, config)
                                doc["extracted_sha256"] = sha(safe_path(output, doc["extracted_path"]).read_bytes())
                                state["documents"][doc["id"]] = doc
                                state["decisions"].append({**decision, "status": "admitted", "document_id": doc["id"], "license": doc["license"], "original_retained": doc["original_retained"]})
                                admitted += 1
                        except BudgetStop:
                            raise
                        except (ValueError, OSError, http.client.HTTPException) as exc:
                            failure = {**decision, "status": "failed", "stage": "verify_download_extract", "reason": type(exc).__name__ + ":" + str(exc)[:240]}
                            state["decisions"].append(failure)
                            state["failures"].append(failure)
                    attempted.add((topic["id"], pmcid))
                    if admitted >= config["documents_per_topic"]:
                        break
            except BudgetStop:
                raise
            except (ValueError, OSError, http.client.HTTPException) as exc:
                state["failures"].append({"topic_id": topic["id"], "stage": "discover", "reason": type(exc).__name__ + ":" + str(exc)[:240]})
            state["usage"] = client.budget.usage()
            if stage != "discover":
                state["completed_topics"] = sorted(set(state.get("completed_topics", [])) | searches_done | {topic["id"]})
            json_write(state_path, state)
            print(f'{topic["specialty_id"]} {topic["id"]}: {len(state["documents"])} admitted; {client.budget.requests} requests', flush=True)
    except BudgetStop as exc:
        state["stop_reason"] = str(exc)
    finally:
        usage = client.budget.usage()
        state.setdefault("runs", []).append({"started_at": now(), "usage": usage, "stage": stage, "stop_reason": state["stop_reason"]})
        state["usage"] = {"latest_run": usage, "cumulative_requests": sum(r["usage"]["requests"] for r in state["runs"]), "cumulative_bytes_received": sum(r["usage"]["bytes_received"] for r in state["runs"]), "cumulative_elapsed_seconds": round(sum(r["usage"]["elapsed_seconds"] for r in state["runs"]), 2)}
        json_write(state_path, state)
    summary = export_report(state, config, output, topic_list)
    print(json.dumps(summary["counts"], indent=2), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/mds_open_collection.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stage", choices=["all"] + STAGES, default="all", help="discover performs metadata-only discovery; verify/download/extract perform gated acquisition; later stages rebuild offline")
    args = parser.parse_args()
    config = json.loads(safe_path(ROOT, args.config).read_text(encoding="utf-8"))
    for field in ("max_documents", "max_bytes", "max_seconds", "max_requests", "per_host_requests", "max_file_bytes", "page_size", "candidates_per_topic", "documents_per_topic"):
        if not isinstance(config[field], int) or config[field] <= 0:
            parser.error(f"{field} must be positive")
    collect(config, args.dry_run, args.stage)


if __name__ == "__main__":
    main()
