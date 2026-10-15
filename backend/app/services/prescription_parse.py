"""Parse transcribed prescription lines into reviewable fields.

Values are copied exactly as written (``candidate_value``); a separate
``normalized`` hint helps reading (e.g. BD -> twice daily). Nothing is inferred:
a field that cannot be located in the written text stays unreadable/unspecified.
"""
import re

FIELD_KINDS = ["medicine_name", "ingredient", "strength", "formulation", "dose", "route", "frequency", "duration", "instructions"]
FORMULATIONS = {
    "tab": "tablet", "tabs": "tablet", "tablet": "tablet", "tablets": "tablet", "cap": "capsule", "caps": "capsule",
    "capsule": "capsule", "capsules": "capsule", "syp": "syrup", "syr": "syrup", "syrup": "syrup", "susp": "suspension",
    "suspension": "suspension", "inj": "injection", "injection": "injection", "oint": "ointment", "ointment": "ointment",
    "gel": "gel", "cream": "cream", "drops": "drops", "drop": "drops", "gtt": "drops", "mouthwash": "mouthwash",
    "mouth wash": "mouthwash", "rinse": "rinse", "inhaler": "inhaler", "sachet": "sachet", "lotion": "lotion",
    "spray": "spray", "paste": "paste", "lozenge": "lozenge", "powder": "powder",
}
FREQUENCIES = {
    "od": "once daily", "qd": "once daily", "bd": "twice daily", "bid": "twice daily", "tds": "three times daily",
    "tid": "three times daily", "qid": "four times daily", "qds": "four times daily", "hs": "at bedtime",
    "sos": "when required", "prn": "when required", "stat": "immediately, once", "qhs": "at bedtime",
}
ROUTES = {"po": "by mouth", "oral": "by mouth", "orally": "by mouth", "iv": "intravenous", "im": "intramuscular",
          "sc": "subcutaneous", "sl": "under the tongue", "topical": "on the skin/mucosa", "local": "local application",
          "inhaled": "inhaled", "by mouth": "by mouth"}
UNIT = r"(?:mg|mcg|µg|g|gm|ml|mL|%|iu|IU|units?)"
STRENGTH = re.compile(rf"\b\d+(?:\.\d+)?\s*{UNIT}(?:\s*/\s*\d*(?:\.\d+)?\s*(?:ml|mL|g|tab))?(?![A-Za-z])", re.I)
FREQ = re.compile(r"\b(?:od|qd|bd|bid|tds|tid|qid|qds|hs|qhs|sos|prn|stat)\b|\b[0-2½]\s*-\s*[0-2½]\s*-\s*[0-2½](?:\s*-\s*[0-2½])?\b|"
                  r"\b(?:once|twice|thrice|one time|two times|three times|four times)\s+(?:a\s+)?(?:daily|a day|per day|weekly)\b|"
                  r"\bevery\s+\d+\s*(?:hours?|hrs?|h)\b|\bq\s?\d+\s?h\b", re.I)
DURATION = re.compile(r"(?:\bx\s*|\bfor\s+)?\b\d+\s*(?:days?|d|weeks?|wks?|w|months?|mths?)\b", re.I)
DOSE = re.compile(r"\b(?:\d+(?:\.\d+)?|½|one|two|half)\s*(?:tabs?|tablets?|caps?|capsules?|puffs?|drops?|sachets?|teaspoons?|tsp)\b|"
                  r"\b\d+(?:\.\d+)?\s*ml\b(?=\s+(?:od|bd|tds|tid|qid|once|twice|thrice|every|\d-\d))", re.I)
INSTRUCTIONS = re.compile(r"\b(?:before|after|with)\s+(?:food|meals?|breakfast|lunch|dinner|water|milk)\b|\bat\s+bedtime\b|"
                          r"\bempty stomach\b|\bdo not (?:chew|crush|swallow)\b|\bswish and spit\b|\bapply\b[^,;]{0,40}", re.I)
LABELLED = re.compile(r"^\s*([A-Za-z ]+)\s*:\s*(.*)$")
LABELS = {"medicine": "medicine_name", "medicine name": "medicine_name", "drug": "medicine_name", "strength": "strength",
          "formulation": "formulation", "form": "formulation", "dose": "dose", "route": "route", "frequency": "frequency",
          "duration": "duration", "instructions": "instructions", "directions": "instructions"}
PREFIX = re.compile(r"^\s*(?:\d+[.)]\s*)?(?:rx\s*[:.]?\s*)?(" + "|".join(sorted(map(re.escape, FORMULATIONS), key=len, reverse=True)) + r")\b\.?\s*", re.I)
UNREADABLE = re.compile(r"\[?unreadable\]?|\?\?+", re.I)


def _found(pattern, text):
    match = pattern.search(text)
    return (match.group(0).strip(" ,;"), match.span()) if match else (None, None)


def parse_line(line):
    """Return {kind: written value} for one medicine line, or None if not a medicine line."""
    text = " ".join(line.split())
    if not text or UNREADABLE.fullmatch(text):
        return None
    prefix = PREFIX.match(text)
    strength, s_span = _found(STRENGTH, text)
    if not prefix and not strength:
        return None
    values = {}
    rest = text[prefix.end():] if prefix else text
    if prefix:
        values["formulation"] = prefix.group(1)
    if strength:
        values["strength"] = strength
    name_part = rest
    if strength:
        index = rest.find(strength)
        name_part = rest[:index] if index > 0 else rest
    name_part = re.split(r"\b(?:od|bd|tds|qid|sos|x\s*\d|for\s+\d)\b", name_part, flags=re.I)[0]
    name = re.sub(r"[^A-Za-z0-9 +\-/()]", " ", name_part).strip(" -/")
    name = " ".join(w for w in name.split() if not re.fullmatch(r"\d+(?:\.\d+)?", w))
    if name and not UNREADABLE.search(name_part) and re.search(r"[A-Za-z]{3,}", name):
        values["medicine_name"] = name
    after = text[s_span[1]:] if strength else rest
    for kind, pattern in (("dose", DOSE), ("frequency", FREQ), ("duration", DURATION), ("instructions", INSTRUCTIONS)):
        value, _ = _found(pattern, after if kind != "instructions" else text)
        if value:
            values[kind] = value
    route = re.search(r"\b(?:po|iv|im|sc|sl|oral(?:ly)?|topical|inhaled|by mouth)\b", after, re.I)
    if route:
        values["route"] = route.group(0)
    if "formulation" not in values:
        form = re.search(r"\b(" + "|".join(sorted(map(re.escape, FORMULATIONS), key=len, reverse=True)) + r")\b", text, re.I)
        if form:
            values["formulation"] = form.group(1)
    return values if "medicine_name" in values or "strength" in values else None


def normalized(kind, value):
    if not value:
        return None
    key = value.casefold().strip(" .")
    if kind == "formulation":
        return FORMULATIONS.get(key)
    if kind == "frequency":
        if key in FREQUENCIES:
            return FREQUENCIES[key]
        pattern = re.fullmatch(r"([0-2½])\s*-\s*([0-2½])\s*-\s*([0-2½])", key)
        if pattern:
            return f"morning {pattern.group(1)}, afternoon {pattern.group(2)}, night {pattern.group(3)} (as written)"
    if kind == "route":
        return ROUTES.get(key)
    return None


def parse_prescription(raw_text):
    """Group lines into medicines. Labelled sheets ('Medicine: X') are supported."""
    groups, labelled = [], {}
    for line in raw_text.splitlines():
        match = LABELLED.match(line)
        if match and match.group(1).strip().casefold() in LABELS:
            kind = LABELS[match.group(1).strip().casefold()]
            value = match.group(2).strip()
            if kind == "medicine_name" and "medicine_name" in labelled:
                groups.append(labelled)
                labelled = {}
            labelled[kind] = (None if not value or UNREADABLE.search(value) else value, line)
            continue
        parsed = parse_line(line)
        if parsed:
            if labelled:
                groups.append(labelled)
                labelled = {}
            groups.append({k: (v, line) for k, v in parsed.items()})
    if labelled:
        groups.append(labelled)
    return groups[:10]
