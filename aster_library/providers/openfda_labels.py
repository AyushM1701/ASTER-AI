"""US drug labels (SPL text) from openFDA, CC0 1.0 (https://open.fda.gov/terms/).

Each label keeps its jurisdiction (US), product type, generic/brand names,
route, dosage form/strength text and the DailyMed set id for provenance.
Repackager copies (``original_packager_product_ndc`` present) are skipped in
favour of the originating labeler. US labels never establish identity with
Indian brands or Indian prescribing guidance.
"""
import json
import re
from pathlib import Path

from aster_library.common import ROOT, WORK, log, register
from aster_library.model import chunk_paragraphs, clean_text, make_unit, today
from aster_library.net import FetchError

API = "https://api.fda.gov/drug/label.json"
TERMS = "https://open.fda.gov/terms/"
SECTIONS = [
    ("boxed_warning", "Boxed warning"),
    ("indications_and_usage", "Indications and usage"),
    ("purpose", "Purpose"),
    ("dosage_and_administration", "Dosage and administration"),
    ("dosage_forms_and_strengths", "Dosage forms and strengths"),
    ("contraindications", "Contraindications"),
    ("do_not_use", "Do not use"),
    ("warnings_and_cautions", "Warnings and precautions"),
    ("warnings", "Warnings"),
    ("precautions", "Precautions"),
    ("ask_doctor", "Ask a doctor before use"),
    ("stop_use", "Stop use"),
    ("adverse_reactions", "Adverse reactions"),
    ("drug_interactions", "Drug interactions"),
    ("use_in_specific_populations", "Use in specific populations"),
    ("pregnancy", "Pregnancy"),
    ("pediatric_use", "Pediatric use"),
    ("geriatric_use", "Geriatric use"),
    ("overdosage", "Overdosage"),
    ("description", "Description"),
    ("mechanism_of_action", "Mechanism of action"),
    ("clinical_pharmacology", "Clinical pharmacology"),
    ("pharmacokinetics", "Pharmacokinetics"),
    ("information_for_patients", "Patient counseling information"),
]


def split_label_text(text):
    text = clean_text(text)
    # Labels often concatenate numbered subsections: split before "5.1 Title".
    parts = re.split(r"\s(?=\d{1,2}\.\d{1,2}\s+[A-Z])", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


# Same salt/hydrate list as backend.app.services.grounded.SALT_WORDS (same active moiety), plus "anhydrous".
SALT_WORDS = re.compile(r"\b(?:hydrochloride|hcl|hydrobromide|sodium|potassium|calcium|magnesium|sulfate|sulphate|"
                        r"maleate|mesylate|besylate|besilate|tartrate|citrate|phosphate|succinate|fumarate|acetate|"
                        r"trihydrate|monohydrate|dihydrate|bromide|nitrate|bitartrate|tromethamine|medoxomil|"
                        r"etexilate|acetonide|propionate|dipropionate|valerate|anhydrous)\b", re.I)


def same_ingredient(label_name, generic):
    """Exact generic name, or the same single ingredient with only a salt/hydrate word added
    ("METFORMIN HYDROCHLORIDE" for metformin). Combination products never match."""
    name, wanted = " ".join(label_name.casefold().split()), " ".join(generic.casefold().split())
    return name == wanted or " ".join(SALT_WORDS.sub(" ", name).split()) == wanted


def choose(results, generic):
    scored = []
    for result in results:
        openfda = result.get("openfda", {})
        names = openfda.get("generic_name", [])
        if not names:
            continue
        exact = any(same_ingredient(n, generic) for n in names)
        repackaged = bool(openfda.get("original_packager_product_ndc"))
        sections = sum(1 for key, _ in SECTIONS if result.get(key))
        scored.append((exact, not repackaged, sections, result.get("effective_time", ""), result))
    scored.sort(key=lambda row: row[:4], reverse=True)
    chosen, routes = [], set()
    for exact, original, sections, _, result in scored:
        if not exact or sections < 3:
            continue
        route = tuple(result.get("openfda", {}).get("route", []))
        if route in routes:
            continue
        routes.add(route)
        chosen.append(result)
        if len(chosen) >= 2:
            break
    return chosen


@register("openfda")
def acquire(client, refresh=False):
    out_dir = WORK / "openfda"
    out_dir.mkdir(parents=True, exist_ok=True)
    generics = json.loads((ROOT / "configs/library/drug_list.json").read_text(encoding="utf-8"))["generics"]
    terms, _ = client.get(TERMS)
    (out_dir / "terms-snapshot.html").write_bytes(terms)
    docs, misses = [], []
    for generic in generics:
        query = f'openfda.generic_name:"{generic}"'
        try:
            data = client.get_json(API, {"search": query, "limit": 50})
        except FetchError as exc:
            misses.append({"generic": generic, "reason": str(exc)[:200]})
            continue
        chosen = choose(data.get("results", []), generic)
        if not chosen:
            misses.append({"generic": generic, "reason": "no single-ingredient label with enough sections"})
            continue
        for result in chosen:
            openfda = result.get("openfda", {})
            set_id = result.get("set_id")
            doc = {
                "doc_id": f"openfda:{set_id}", "provider": "openfda",
                "title": f"{generic.title()} — US product label ({', '.join(openfda.get('route', []) or ['route not stated'])})",
                "url": f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={set_id}",
                "publisher": "; ".join(openfda.get("manufacturer_name", [])) or "Labeler not stated",
                "jurisdiction": "US", "content_class": "drug_label", "evidence_type": "drug_label",
                "published": (result.get("effective_time") or "")[:8], "version": f"SPL version {result.get('version')}",
                "acquired": today(), "license": "CC0-1.0", "license_url": TERMS,
                "attribution": "U.S. FDA drug labeling via openFDA (CC0); DailyMed set id " + str(set_id),
                "acquisition_endpoint": f"{API}?search={query}",
                "identifiers": {"setid": set_id, "spl_id": result.get("id")},
                "drug": {
                    "generic_name": openfda.get("generic_name", []), "brand_name": openfda.get("brand_name", []),
                    "substance_name": openfda.get("substance_name", []), "route": openfda.get("route", []),
                    "product_type": openfda.get("product_type", []), "rxcui": openfda.get("rxcui", [])[:10],
                    "dosage_forms_and_strengths": clean_text(" ".join(result.get("dosage_forms_and_strengths", [])))[:600] or None,
                    "jurisdiction_note": "US labeling for the named US product; not evidence about Indian brands, strengths or local prescribing guidance.",
                },
                "access": "full_text", "publication_status": "published",
            }
            units = []
            for key, title in SECTIONS:
                for entry in result.get(key, []) or []:
                    for i, text in chunk_paragraphs(split_label_text(entry), target=1000):
                        units.append(make_unit(doc, section_path=[title], paragraph=i, text=text))
            if units:
                docs.append({"status": "acquired", "doc": doc, "units": units})
    with (out_dir / "docs.jsonl").open("w", encoding="utf-8") as out:
        for item in docs:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")
    (out_dir / "misses.json").write_text(json.dumps(misses, indent=1), encoding="utf-8")
    (out_dir / "state.json").write_text(json.dumps({"last_run": today(), "labels": len(docs), "generics": len(generics),
                                                    "missed": len(misses)}, indent=2), encoding="utf-8")
    log(f"openfda: {len(docs)} labels for {len(generics)} generics; {len(misses)} missed")


def load(work=WORK):
    path = Path(work) / "openfda" / "docs.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
