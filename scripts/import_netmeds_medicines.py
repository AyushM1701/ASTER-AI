"""Import user-attested Netmeds monographs without summarizing or approving medicine use.

The immutable CSV is the source of truth. Offsets refer to its whitespace-normalized
drug_content, not to UTF-8 byte positions. Retail text is for lexical retrieval only;
it must be excluded from the MiniLM dense index by the release builder. No release
is built or activated here. Unrecognized/unsplittable source units are explicitly
excluded and audited rather than guessed or silently truncated.
"""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data/references/raw/v2/kaggle_drowsyng/medicines.csv"
OUTPUT_PATH = ROOT / "data/knowledge_v2/netmeds_user_approved_documents.json"
AUDIT_PATH = ROOT / "data/knowledge_v2/netmeds_import_audit.json"
USER_STATEMENT = "it is verified and has the license, use it for aster's clinical library"
RETRIEVED_DATE = "2026-10-07"
MAX_CHARS = 1450
FORM_NAMES = r"tablet|capsule|injection|suspension|solution|syrup|drops|cream|gel|ointment|spray|powder|lotion|inhaler|sachet|patch|suppository|soap|shampoo|expectorant"

MARKERS = re.compile(
    r"INTRODUCTION ABOUT |INTRODUCTION|USES OF |"
    r"HOW [A-Z0-9][A-Z0-9 .&%/()'\-+]{0,180}? WORKS|"
    r"DIRECTIONS FOR USE|SIDE EFFECTS OF |HOW TO MANAGE SIDE EFFECTS|"
    r"WARNING & PRECAUTIONS|INTERACTIONS|SYNOPSIS|MORE INFORMATION|"
    r"FAQs ABOUT |REFERENCES|AUTHOR DETAILS|USEFUL DIAGNOSTIC TESTS"
)
EXCLUDE = {
    "DIRECTIONS FOR USE": "direct_directions_or_self_treatment",
    "HOW TO MANAGE SIDE EFFECTS": "direct_directions_or_self_treatment",
    "FAQs ABOUT": "direct_directions_or_self_treatment",
    "MORE INFORMATION": "storage_or_product_management",
    "REFERENCES": "bibliography_not_independent_source_verification",
    "AUTHOR DETAILS": "author_metadata_not_clinical_approval",
    "USEFUL DIAGNOSTIC TESTS": "diagnostic_test_list_not_independent_guidance",
}
SUBHEADINGS = {
    "WARNING & PRECAUTIONS": re.compile(
        r"PREGNANCY|BREASTFEEDING|DRIVING AND USING MACHINES|ALCOHOL|"
        r"KIDNEY|LIVER|ALLERGY|HEART DISEASE|LUNG DISEASE|OTHERS"
    ),
    "SIDE EFFECTS OF": re.compile(r"(?<![A-Z])(?:UNCOMMON|COMMON|RARE|SERIOUS)(?![a-z])"),
    "INTERACTIONS": re.compile(r"A\. Drug-Drug interactions:|B\. Drug-Food interactions:|Overdosage:"),
}


def normalize_source(text):
    """Normalize whitespace only; do not repair corruption, spelling, or medical claims."""
    return " ".join((text or "").split())


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pack_free_name(name):
    """Candidate only: it becomes an alias only after an exact source-text match."""
    return re.sub(r"\s+\d+(?:\.\d+)?\s*(?:['’]s|s|ml|gm|g|kg|litre|liter)(?:\s*\([^)]*\))?$", "", name, flags=re.I).strip()


def _name_without_strength_unit(name):
    return normalize_source(re.sub(r"(?<=\d)\s*(?:mg|mcg|ug|iu)(?=\s|$)", "", name, flags=re.I)).casefold()


def verified_headline(text, product_name=None):
    if not text.startswith("INTRODUCTION ABOUT "):
        return None
    tail = text[len("INTRODUCTION ABOUT "):]
    candidates = []
    # Most scraped headings and the first prose product name are concatenated.
    # A repeated uppercase name is evidence in the source, not a guessed alias.
    for length in range(5, min(200, len(tail) // 2) + 1):
        name = tail[:length].strip()
        if not name or not any(c.isalpha() for c in name) or name != name.upper():
            continue
        rest = tail[length:].lstrip()
        if rest.startswith(name) and (len(rest) == len(name) or not rest[len(name)].isalnum()):
            candidates.append(name)
    if candidates:
        return max(candidates, key=len)
    # An uppercase heading may be followed by a mixed-case prose product name.
    # Accept that boundary only when the CSV pack-free name independently starts
    # the following prose and matches the heading, allowing an explicit unit.
    if product_name:
        match = re.match(r"^([A-Z0-9][A-Z0-9 .&%/()'\-+]{4,199})(?=[A-Z][a-z])", tail)
        if match:
            headline = match[1].strip()
            product = pack_free_name(product_name)
            body = tail[match.end():]
            if body.casefold().startswith(product.casefold()) and _name_without_strength_unit(headline) == _name_without_strength_unit(product):
                return headline
    return None


def verified_aliases(name, text, headline):
    aliases = [headline] if headline else []
    candidate = pack_free_name(name)
    if candidate != name and text.startswith("INTRODUCTION"):
        for match in re.finditer(re.escape(candidate), text[:1000], re.I):
            end = match.end()
            if end < len(text) and text[end].isalnum():
                continue
            before = match.start()
            starts_prose = headline and before == len("INTRODUCTION ABOUT ") + len(headline)
            if before == 0 or not text[before - 1].isalnum() or starts_prose:
                literal = text[before:end]
                if literal.casefold() not in {a.casefold() for a in aliases}:
                    aliases.append(literal)
                break
    # Only the explicitly named final dosage form is optional. Variant tokens
    # such as LS/JUNIOR/PLUS/CR and every strength token remain in the alias.
    for alias in list(aliases):
        brand = re.sub(r"\s+(?:" + FORM_NAMES + r")s?$", "", alias, flags=re.I).strip()
        if brand != alias and len(brand) >= 3 and brand.casefold() not in {a.casefold() for a in aliases}:
            aliases.append(brand)
    return aliases


def source_sections(text, headline):
    matches = list(MARKERS.finditer(text))
    # Recognized headings must start the description: otherwise do not accidentally
    # treat the middle of commercial/FAQ prose as an independently delimited section.
    if not matches or matches[0].start() != 0:
        return [], "unrecognized_source_layout"
    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        while end > start and text[end - 1].isspace():
            end -= 1
        kind = match.group().strip()
        header_end = match.end()
        if headline and kind in {"INTRODUCTION ABOUT", "USES OF", "SIDE EFFECTS OF", "FAQs ABOUT"}:
            if text.startswith(headline, header_end):
                header_end += len(headline)
        title = text[start:header_end].strip()
        body_start = header_end
        while body_start < end and text[body_start].isspace():
            body_start += 1
        sections.append(dict(start=start, end=end, body_start=body_start,
                             header_end=header_end, title=title, kind=kind, product_headline=headline))
    return sections, None


def _sentence_ranges(text, start, end):
    """Whole sentences only, including trailing conditional/qualification clauses."""
    ranges = []
    cursor = start
    for match in re.finditer(r"[.!?](?:[\"')\]]*)(?=\s+[A-Z]|$)", text[start:end]):
        boundary = start + match.end()
        # Abbreviations and list numbering do not end a sentence.
        preceding = text[max(cursor, boundary - 8):boundary]
        if re.search(r"(?:\bEx|\bDr|\bi\.e|\be\.g|\bet al|\b[A-Z])\.$", preceding):
            continue
        if boundary > cursor:
            ranges.append([cursor, boundary])
        cursor = boundary
        while cursor < end and text[cursor].isspace():
            cursor += 1
    if cursor < end:
        ranges.append([cursor, end])
    return ranges


def _subunits(text, section):
    pattern = SUBHEADINGS.get(section["kind"])
    if pattern is None:
        return [(section["body_start"], section["end"], None)]
    matches = []
    product_ranges = []
    if section.get("product_headline"):
        product_ranges = [(m.start(), m.end()) for m in re.finditer(
            re.escape(section["product_headline"]), text[section["body_start"]:section["end"]])]
        product_ranges = [(a + section["body_start"], b + section["body_start"]) for a, b in product_ranges]
    for match in pattern.finditer(text, section["body_start"], section["end"]):
        if any(a <= match.start() < b for a, b in product_ranges):
            continue
        # Reject matching uppercase letters embedded inside a product name.
        if match.start() > section["body_start"] and not text[match.start() - 1].isspace():
            continue
        matches.append(match)
    if not matches:
        return [(section["body_start"], section["end"], None)]
    units = []
    if matches[0].start() > section["body_start"]:
        units.append((section["body_start"], matches[0].start(), None))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else section["end"]
        while end > match.end() and text[end - 1].isspace():
            end -= 1
        units.append((match.end(), end, [match.start(), match.end()]))
    return units


def chunk_section(text, section, max_chars):
    """Return verbatim source spans; context overlaps never truncate a sentence.

    Short sections remain contiguous. Long sections split by explicit subheading
    and complete sentences, repeat the section/subheading and first sentence for
    context, and overlap the preceding sentence when it fits. Units that cannot
    satisfy the limit without splitting a qualification are explicitly excluded.
    """
    if section["end"] - section["start"] <= max_chars:
        return [dict(text=text[section["start"]:section["end"]],
                     source_spans=[[section["start"], section["end"]]])], []
    chunks, exclusions = [], []
    header = [section["start"], section["header_end"]]
    for start, end, subheading in _subunits(text, section):
        context = [header] + ([subheading] if subheading else [])
        sentences = _sentence_ranges(text, start, end)
        if not sentences:
            exclusions.append(dict(start=start, end=end, reason="empty_source_unit"))
            continue
        lead = sentences[0]
        base = context + [lead]
        if len(" ".join(text[a:b] for a, b in base)) > max_chars:
            exclusions.append(dict(start=subheading[0] if subheading else start,
                                   end=end, reason="unsplittable_qualified_unit_over_limit"))
            continue
        current, previous = list(base), None
        for sentence in sentences[1:]:
            candidate = current + [sentence]
            if len(" ".join(text[a:b] for a, b in candidate)) <= max_chars:
                current = candidate
                previous = sentence
                continue
            chunks.append(dict(text=" ".join(text[a:b] for a, b in current), source_spans=current))
            current = list(base)
            if previous and previous != lead:
                candidate = current + [previous, sentence]
                if len(" ".join(text[a:b] for a, b in candidate)) <= max_chars:
                    current.append(previous)
            if len(" ".join(text[a:b] for a, b in current + [sentence])) > max_chars:
                # The entire qualified subunit is withheld if an individual sentence
                # cannot fit with its lead-in. No partially served list remains.
                chunks = [c for c in chunks if not any(a == start for a, _ in c["source_spans"])]
                exclusions.append(dict(start=subheading[0] if subheading else start,
                                       end=end, reason="unsplittable_qualified_unit_over_limit"))
                current = []
                break
            current.append(sentence)
            previous = sentence
        if current:
            chunks.append(dict(text=" ".join(text[a:b] for a, b in current), source_spans=current))
    if not chunks:
        exclusions.append(dict(start=section["start"], end=section["header_end"],
                               reason="source_header_without_served_body"))
    return chunks, exclusions


def product_fields(name, headline):
    forms = re.findall(r"\b(" + FORM_NAMES + r")s?\b", name, re.I)
    formulations = list(dict.fromkeys(f.lower() for f in forms))
    first_form = re.search(r"\b(?:" + "|".join(re.escape(f) for f in formulations) + r")s?\b", name, re.I) if formulations else None
    # A terminal 5ml/15gm is pack size. Strength is explicit before the dosage form
    # or a percentage/concentration; do not read ingredients or synopsis into it.
    strengths = []
    for match in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(mg|mcg|ug|g|gm|iu|units|%)(?:\s*/\s*(\d+(?:\.\d+)?\s*)?(ml|g|gm))?(?![a-z])", name, re.I):
        if first_form and match.start() >= first_form.start() and not (match.group(4) or match.group(2) == "%"):
            continue
        strengths.append(re.sub(r"\s+", "", match.group()).lower().replace("gm", "g").replace("ug", "mcg"))
    strengths = list(dict.fromkeys(strengths))
    routes = []
    for pattern, route in [(r"\b(?:eye|ophthalmic)\b", "ophthalmic"), (r"\b(?:ear|otic)\b", "otic"),
                           (r"\b(?:nasal|intranasal)\b", "nasal"), (r"\b(?:oral)\b", "oral"),
                           (r"\b(?:vaginal)\b", "vaginal"), (r"\b(?:rectal)\b", "rectal"),
                           (r"\b(?:topical|cutaneous)\b", "topical"),
                           (r"\b(?:intravenous|iv)\b", "intravenous"), (r"\b(?:intramuscular|im)\b", "intramuscular")]:
        if re.search(pattern, name, re.I):
            routes.append(route)
    return dict(entity=name, product_identity=name, aliases=[headline] if headline else [],
                formulations=formulations, strengths=strengths, label_strengths=strengths,
                routes=routes, products=[dict(name=name, brand=headline or name,
                formulation=formulations[0] if len(formulations) == 1 else "", route=routes[0] if len(routes) == 1 else "",
                match_strengths=strengths, ingredients=[])])


def source_date(text):
    matches = re.findall(r"Last updated on (\d{1,2} [A-Za-z]{3,9} \d{4})(?=\s*\||\s*$)", text)
    if len(set(matches)) != 1:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(matches[0], fmt).date().isoformat()
        except ValueError:
            pass
    return None


def import_rows(rows, snapshot_sha256, user_statement, max_chars=MAX_CHARS, raw_snapshot_path=None):
    if not user_statement.strip():
        raise ValueError("Record the exact user permission statement")
    if not 200 <= max_chars <= 1450:
        raise ValueError("Source chunks must fit the 1450-character answer claim budget")
    documents, warnings, excluded, rejected = [], [], [], []
    counts = Counter()
    seen_names, seen_urls = set(), set()
    for row_number, row in enumerate(rows, start=2):
        counts["input_rows"] += 1
        name, url = row.get("med_name", ""), row.get("med_url", "")
        key = dict(row_number=row_number, med_name=name, med_url=url)
        parts = urlsplit(url)
        reason = None
        if None in row or not name.strip():
            reason = "malformed_csv_row_or_missing_product_name"
        elif parts.scheme != "https" or parts.hostname != "www.netmeds.com" or parts.username or parts.password or parts.port:
            reason = "unapproved_product_url"
        elif name.casefold() in seen_names or url in seen_urls:
            reason = "duplicate_product_identity"
        if reason:
            rejected.append({**key, "reason": reason})
            continue
        seen_names.add(name.casefold())
        seen_urls.add(url)
        text = normalize_source(row.get("drug_content", ""))
        generic = normalize_source(row.get("generic_name", ""))
        headline = verified_headline(text, name)
        metadata = product_fields(name, headline)
        metadata["aliases"] = verified_aliases(name, text, headline)
        if not metadata["strengths"] and headline and _name_without_strength_unit(headline) == _name_without_strength_unit(pack_free_name(name)):
            explicit = product_fields(headline, headline)["strengths"]
            if explicit:
                metadata["strengths"] = explicit
                metadata["label_strengths"] = explicit
                metadata["products"][0]["match_strengths"] = explicit
                metadata["strength_evidence"] = "INTRODUCTION headline: " + headline
        source_id = "netmeds-" + hashlib.sha256(url.encode()).hexdigest()[:24]
        limitations = []
        if not text:
            counts["missing_description"] += 1
            limitations.append("Description: not provided in the CSV; no clinical monograph is available for this product.")
        if not generic:
            counts["missing_generic"] += 1
            limitations.append("Generic name: not provided in the CSV; no ingredient identity is inferred.")
        if text and not headline:
            warnings.append({**key, "code": "no_verified_intro_heading_alias"})
        if "\ufffd" in text:
            warnings.append({**key, "code": "source_replacement_character_preserved", "count": text.count("\ufffd")})
        date = source_date(text)
        if "Last updated" in text and date is None:
            warnings.append({**key, "code": "unparsed_source_date"})
        identity_lines = ["CSV product name: " + name]
        if generic:
            identity_lines.append("CSV generic field (retailer supplied): " + generic)
        if row.get("drug_manufacturer", "").strip():
            identity_lines.append("CSV manufacturer field: " + normalize_source(row["drug_manufacturer"]))
        identity_lines.extend(limitations)
        identity_lines.append("Secondary retailer source; user-attested permission; no qualified clinical review is asserted.")
        identity = "\n".join(identity_lines)
        if len(identity) > max_chars:
            rejected.append({**key, "reason": "identity_fields_over_limit"})
            continue
        doc = dict(id=source_id, title=name + " — Netmeds retailer monograph", url=url,
                   publisher="Netmeds via Kaggle (secondary retail monograph)", jurisdiction="India",
                   source_date=date, retrieved_date=RETRIEVED_DATE, version="kaggle-v1-" + snapshot_sha256[:16],
                   raw_snapshot_path=raw_snapshot_path or "data/references/raw/v2/kaggle_drowsyng/medicines.csv",
                   raw_sha256=snapshot_sha256, source_type="retailer_monograph", clinical_review=False,
                   terms="User attests verified/licensed use: Apache-2.0 dataset declaration plus Netmeds upstream permission attestation; not independently verified.",
                   permission_basis=dict(type="user_attested", user_statement=user_statement,
                        dataset_ref="drowsyng/medicines-dataset", snapshot_sha256=snapshot_sha256,
                        approved_host="www.netmeds.com", asserted_verification=True, asserted_license=True,
                        clinical_review=False), **metadata,
                   dataset_row_number=row_number, generic_name_raw=row.get("generic_name", ""),
                   description_sha256=hashlib.sha256(text.encode()).hexdigest(),
                   limitations=limitations, sections=[])
        topics = [name] + ([headline] if headline else [])
        keywords = list(dict.fromkeys(re.findall(r"[a-z0-9]+", name.casefold()))) or ["product"]
        doc["sections"].append(dict(id="identity", title="Product identity (CSV fields)", text=identity,
                                    topics=topics, keywords=keywords, source_fields=["med_name", "generic_name", "drug_manufacturer"]))
        sections, extraction_error = source_sections(text, headline) if text else ([], None)
        if extraction_error:
            excluded.append({**key, "title": "Unrecognized description", "start": 0, "end": len(text), "reason": extraction_error})
            warnings.append({**key, "code": extraction_error})
        for number, section in enumerate(sections, start=1):
            counts["recognized_source_sections"] += 1
            if section["kind"] in EXCLUDE:
                excluded.append({**key, "title": section["title"], "start": section["start"],
                                 "end": section["end"], "reason": EXCLUDE[section["kind"]]})
                continue
            chunks, omitted = chunk_section(text, section, max_chars)
            for item in omitted:
                excluded.append({**key, "title": section["title"], **item})
                warnings.append({**key, "code": item["reason"], "section": section["title"]})
            for part, chunk in enumerate(chunks, start=1):
                if len(chunk["text"]) < 10:
                    excluded.append({**key, "title": section["title"], "start": section["start"], "end": section["end"], "reason": "source_text_under_reference_minimum"})
                    continue
                doc["sections"].append(dict(id=f"source-{number}-part-{part}",
                    title=section["title"] + (f" (part {part})" if len(chunks) > 1 else ""),
                    topics=topics, keywords=keywords, **chunk))
        # Overlap may produce identical text from repeated source sentences. Keep
        # one copy per document because release lineage rejects duplicate text.
        unique, hashes = [], {}
        for section in doc["sections"]:
            digest = hashlib.sha256(section["text"].encode()).hexdigest()
            if digest in hashes:
                warnings.append({**key, "code": "duplicate_chunk_text_consolidated", "section": section["title"]})
                if section.get("source_spans"):
                    hashes[digest].setdefault("equivalent_source_spans", []).append(section["source_spans"])
                continue
            hashes[digest] = section
            unique.append(section)
        doc["sections"] = unique
        counts["documents"] += 1
        counts["served_sections"] += len(unique)
        counts["clinical_source_chunks"] += len(unique) - 1
        counts["identity_only_documents"] += len(unique) == 1
        counts["documents_with_verified_alias"] += bool(metadata["aliases"])
        counts["documents_with_source_date"] += bool(date)
        documents.append(doc)
    counts["rejected_rows"] = len(rejected)
    counts["excluded_source_units"] = len(excluded)
    counts["extraction_warnings"] = len(warnings)
    audit = dict(snapshot_sha256=snapshot_sha256, retrieved_date=RETRIEVED_DATE,
                 normalization="Whitespace only; source spelling, corruption and qualifications preserved.",
                 offsets="Python character offsets [start,end) in whitespace-normalized CSV drug_content.",
                 max_chunk_characters=max_chars,
                 dense_embedding_policy="retailer_monograph is excluded from dense embeddings; exact-product lexical retrieval",
                 permission_basis=documents[0]["permission_basis"] if documents else None,
                 counts=dict(counts), exclusion_counts=dict(Counter(e["reason"] for e in excluded)),
                 warning_counts=dict(Counter(w["code"] for w in warnings)),
                 sections_by_source_heading=dict(Counter(s["title"].split(" (part ")[0] for d in documents for s in d["sections"])),
                 sample_aliases=[dict(product=d["entity"], aliases=d["aliases"], routes=d["routes"], strengths=d["strengths"]) for d in documents if d["aliases"]][:20],
                 rejected_rows=rejected, warnings=warnings, excluded_sections=excluded)
    return documents, audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--audit", type=Path, default=AUDIT_PATH)
    parser.add_argument("--user-statement", default=USER_STATEMENT)
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS)
    args = parser.parse_args(argv)
    csv.field_size_limit(10_000_000)
    digest = sha256_file(args.csv)
    resolved = args.csv.resolve()
    raw_path = resolved.relative_to(ROOT).as_posix() if resolved.is_relative_to(ROOT) else str(resolved)
    with args.csv.open(newline="", encoding="utf-8-sig") as handle:
        documents, audit = import_rows(csv.DictReader(handle), digest, args.user_statement,
                                       args.max_chars, raw_snapshot_path=raw_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(dataset_ref="drowsyng/medicines-dataset", import_status="user_attested_source_permission",
                   clinical_review=False, documents=documents)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    audit.update(documents_path=str(args.output), documents_sha256=sha256_file(args.output),
                 importer_sha256=sha256_file(__file__))
    args.audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(counts=audit["counts"], documents_sha256=audit["documents_sha256"],
                          exclusion_counts=audit["exclusion_counts"], warning_counts=audit["warning_counts"]), indent=2))


if __name__ == "__main__":
    main()
