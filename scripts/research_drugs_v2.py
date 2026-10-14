"""Acquire official DailyMed SPL snapshots for the v2 research corpus.

This research helper fetches source material only. Editorial paraphrases are
reviewed separately; DailyMed inclusion does not imply FDA approval.
"""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/references/raw/v2/drugs"
NS = {"h": "urn:hl7-org:v3"}
TARGETS = [
    ("acetaminophen", "ACETAMINOPHEN", "ACETAMINOPHEN TABLET"),
    ("amoxicillin", "AMOXICILLIN", "AMOXICILLIN CAPSULE"),
    ("metformin hydrochloride", "METFORMIN HYDROCHLORIDE", "METFORMIN HYDROCHLORIDE TABLET"),
    ("lisinopril", "LISINOPRIL", "LISINOPRIL TABLET"),
    ("amlodipine besylate", "AMLODIPINE BESYLATE", "AMLODIPINE BESYLATE TABLET"),
    ("losartan potassium", "LOSARTAN POTASSIUM", "LOSARTAN POTASSIUM TABLET"),
    ("hydrochlorothiazide", "HYDROCHLOROTHIAZIDE", "HYDROCHLOROTHIAZIDE TABLET"),
    ("insulin glargine", "LANTUS", "LANTUS (INSULIN GLARGINE)"),
    ("atorvastatin calcium", "ATORVASTATIN CALCIUM", "ATORVASTATIN CALCIUM TABLET"),
    ("azithromycin", "AZITHROMYCIN", "AZITHROMYCIN TABLET"),
    ("doxycycline hyclate", "DOXYCYCLINE HYCLATE", "DOXYCYCLINE HYCLATE CAPSULE"),
    ("cephalexin", "CEPHALEXIN", "CEPHALEXIN CAPSULE"),
    ("ciprofloxacin hydrochloride", "CIPROFLOXACIN", "CIPROFLOXACIN TABLET"),
    (
        "nitrofurantoin monohydrate/macrocrystals",
        "NITROFURANTOIN",
        "NITROFURANTOIN MONOHYDRATE/MACROCRYSTALS CAPSULE",
    ),
    ("ibuprofen", "IBUPROFEN", "IBUPROFEN TABLET"),
    ("naproxen", "NAPROXEN", "NAPROXEN TABLET"),
    ("diclofenac sodium", "DICLOFENAC SODIUM", "DICLOFENAC SODIUM TABLET, DELAYED RELEASE"),
    ("cetirizine hydrochloride", "CETIRIZINE HYDROCHLORIDE", "CETIRIZINE HYDROCHLORIDE TABLET"),
    ("loratadine", "LORATADINE", "LORATADINE TABLET"),
    ("omeprazole", "OMEPRAZOLE", "OMEPRAZOLE CAPSULE, DELAYED RELEASE"),
    ("pantoprazole sodium", "PANTOPRAZOLE SODIUM", "PANTOPRAZOLE SODIUM TABLET, DELAYED RELEASE"),
    ("famotidine", "FAMOTIDINE", "FAMOTIDINE TABLET"),
    ("albuterol sulfate", "ALBUTEROL SULFATE", "ALBUTEROL SULFATE AEROSOL, METERED"),
    ("budesonide", "PULMICORT", "PULMICORT RESPULES (BUDESONIDE) SUSPENSION"),
    ("montelukast sodium", "MONTELUKAST SODIUM", "MONTELUKAST SODIUM TABLET"),
    ("levothyroxine sodium", "LEVOTHYROXINE SODIUM", "LEVOTHYROXINE SODIUM TABLET"),
    ("sertraline hydrochloride", "SERTRALINE HYDROCHLORIDE", "SERTRALINE HYDROCHLORIDE TABLET"),
    ("fluoxetine hydrochloride", "FLUOXETINE", "FLUOXETINE CAPSULE"),
    ("ondansetron hydrochloride", "ONDANSETRON", "ONDANSETRON TABLET"),
    ("prednisone", "PREDNISONE", "PREDNISONE TABLET"),
    ("acetaminophen", "ACETAMINOPHEN 500 MG", "ACETAMINOPHEN 500 MG"),
]


def clean(node):
    return re.sub(r"\s+", " ", " ".join(node.itertext())).strip() if node is not None else ""


def fetch(target):
    entity, query, prefix = target
    listing_url = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
    result = requests.get(listing_url, params={"drug_name": query, "pagesize": 100}, timeout=60)
    result.raise_for_status()
    candidates = result.json()["data"]
    chosen = next((item for item in candidates if item["title"].startswith(prefix)), None)
    if not chosen:
        return {
            "entity": entity,
            "error": "No prefix match",
            "titles": [i["title"] for i in candidates[:15]],
        }
    setid = chosen["setid"]
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    source = response.content
    tree = ET.fromstring(source)
    slug = re.sub(r"[^a-z0-9]+", "-", entity).strip("-")
    path = RAW / f"{slug}-{setid}.xml"
    path.write_bytes(source)
    products = []
    for product in tree.findall(".//h:subject/h:manufacturedProduct/h:manufacturedProduct", NS):
        ingredients = []
        for ingredient in product.findall("h:ingredient", NS):
            if ingredient.get("classCode") not in {"ACTIB", "ACTIM", "ACTIR"}:
                continue
            quantity = ingredient.find("h:quantity", NS)
            num = quantity.find("h:numerator", NS) if quantity is not None else None
            den = quantity.find("h:denominator", NS) if quantity is not None else None
            strength = (
                (num.get("value", "") + " " + num.get("unit", "")).strip()
                if num is not None
                else ""
            )
            if den is not None:
                strength += " / " + (den.get("value", "") + " " + den.get("unit", "")).strip()
            ingredients.append(
                {
                    "ingredient": clean(ingredient.find("h:ingredientSubstance/h:name", NS)),
                    "strength": strength,
                }
            )
        products.append(
            {
                "name": clean(product.find("h:name", NS)),
                "form": product.find("h:formCode", NS).get("displayName"),
                "ingredients": ingredients,
            }
        )
    routes = sorted(
        {
            node.get("displayName")
            for node in tree.findall(".//h:routeCode", NS)
            if node.get("displayName")
        }
    )
    sections = []
    for section in tree.findall(".//h:section", NS):
        code = section.find("h:code", NS)
        name = code.get("displayName", "") if code is not None else ""
        title = clean(section.find("h:title", NS))
        if any(
            term in (name + " " + title).lower()
            for term in [
                "indication",
                "purpose",
                "warning",
                "contraindication",
                "do not use",
                "active ingredient",
                "dosage forms",
                "description",
            ]
        ):
            sections.append(
                {
                    "code": code.get("code") if code is not None else None,
                    "title": title or name,
                    "text": " ".join(clean(node) for node in section.findall(".//h:text", NS)),
                }
            )
    date = tree.find("h:effectiveTime", NS).get("value", "")
    return {
        "entity": entity,
        "listing": chosen,
        "url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}",
        "source_date": f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) >= 8 else None,
        "version": tree.find("h:versionNumber", NS).get("value"),
        "labeler": clean(
            tree.find("h:author/h:assignedEntity/h:representedOrganization/h:name", NS)
        ),
        "raw_snapshot_path": path.relative_to(ROOT).as_posix(),
        "raw_sha256": hashlib.sha256(source).hexdigest(),
        "products": products,
        "routes": routes,
        "sections": sections,
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(fetch, TARGETS))
    (RAW / "research_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    for record in records:
        print(
            record["entity"],
            record.get("error") or record["listing"]["title"],
            record.get("products", []),
            record.get("routes", []),
        )
    (RAW / "review_excerpts.txt").write_text(
        "\n\n".join(
            record["entity"]
            + "\n"
            + "\n".join(s["title"] + ": " + s["text"][:5500] for s in record.get("sections", []))
            for record in records
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
