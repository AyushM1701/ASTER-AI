"""Evidence unit and source document records shared by every provider."""
import hashlib
import re
import time
import unicodedata

CONTENT_CLASSES = {"patient", "professional", "drug_label", "research"}
ACCESS_LEVELS = {"full_text", "abstract", "metadata"}

# Licences allowed in the default (redistributable, commercial-compatible) edition.
DEFAULT_EDITION_LICENSES = {
    "CC0-1.0", "CC-BY-4.0", "CC-BY-3.0", "CC-BY-2.0", "CC-BY-2.5", "CC-BY-SA-4.0", "CC-BY-SA-3.0",
    "US-Government-Public-Domain", "CDC-public-domain", "NIMH-public-domain",
    "NIDDK-copyright-free", "MedlinePlus-public-domain", "MedlinePlus-genetics-public-domain",
}
# Licences that permit noncommercial redistribution only; isolated into the NC pack.
NONCOMMERCIAL_LICENSES = {
    "CC-BY-NC-4.0", "CC-BY-NC-3.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-SA-3.0", "CC-BY-NC-SA-3.0-IGO",
}
# No-derivatives licences: chunking/indexing is an adaptation risk; excluded.
EXCLUDED_LICENSES = {"CC-BY-ND-4.0", "CC-BY-NC-ND-4.0", "CC-BY-NC-ND-3.0"}


def today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def normalize_license(raw):
    """Map provider licence strings/URLs to SPDX-like identifiers. Unknown -> None."""
    if not raw:
        return None
    text = raw.strip().lower()
    if "publicdomain/zero" in text or text in {"cc0", "cc0 1.0", "cc0-1.0"}:
        return "CC0-1.0"
    match = re.search(r"licenses/(by(?:-nc)?(?:-sa)?(?:-nd)?)/(\d\.\d)(?:/igo)?", text)
    if match:
        return "CC-" + match.group(1).upper() + "-" + match.group(2) + ("-IGO" if "/igo" in text else "")
    words = re.sub(r"[^a-z0-9]+", " ", text).split()
    if words[:1] == ["cc"]:
        parts = [w for w in words[1:] if w in {"by", "nc", "sa", "nd"}]
        version = next((w for w in words if re.fullmatch(r"\d\d?", w)), None)
        if parts and parts[0] == "by":
            version = {"4": "4.0", "3": "3.0", "2": "2.0", "40": "4.0", "30": "3.0"}.get(version or "4", "4.0")
            return "CC-" + "-".join(p.upper() for p in parts) + "-" + version
    return None


def edition_for(license_id):
    if license_id in DEFAULT_EDITION_LICENSES:
        return "default"
    if license_id in NONCOMMERCIAL_LICENSES:
        return "noncommercial"
    return None


def clean_text(text):
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace(" ", " ").replace(" ", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unit_id(doc_id, location, text):
    return hashlib.sha256(f"{doc_id}|{location}|{sha256_text(text)}".encode()).hexdigest()[:24]


def chunk_paragraphs(paragraphs, *, target=1100, hard=1800):
    """Group paragraphs within one section; never cross section boundaries.

    Long paragraphs are split on sentence boundaries. Returns list of (start_index, text).
    """
    out, buffer, start = [], [], 0
    size = 0
    for index, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        if len(para) > hard:
            if buffer:
                out.append((start, "\n".join(buffer)))
                buffer, size = [], 0
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", para)
            piece = ""
            for sentence in sentences:
                if piece and len(piece) + len(sentence) > target:
                    out.append((index, piece.strip()))
                    piece = ""
                piece += sentence + " "
            if piece.strip():
                out.append((index, piece.strip()))
            start = index + 1
            continue
        if buffer and size + len(para) > target:
            out.append((start, "\n".join(buffer)))
            buffer, size = [], 0
        if not buffer:
            start = index
        buffer.append(para)
        size += len(para)
    if buffer:
        out.append((start, "\n".join(buffer)))
    return out


def make_unit(doc, *, section_path, paragraph, text, kind="text", reliability="structured", extra=None):
    text = clean_text(text)
    location = " > ".join(section_path) + f" ¶{paragraph}"
    unit = {
        "unit_id": unit_id(doc["doc_id"], location, text),
        "doc_id": doc["doc_id"],
        "section": " > ".join(section_path) or doc.get("title", ""),
        "location": {"section_path": list(section_path), "paragraph": paragraph, "page": None},
        "kind": kind,
        "text": text,
        "text_sha256": sha256_text(text),
        "extraction_reliability": reliability,
    }
    if extra:
        unit.update(extra)
    return unit
