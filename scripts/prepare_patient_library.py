"""Acquire bounded licensed patient references and bind developer-prepared notes.

Refresh into a new version only. Changed medical text requires a new manual
source comparison; this script never certifies medicine or silently rebinds it.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from backend.app.services.patient_information import OGL
from backend.app.services.retrieval import Reference

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "toothache": (
        "symptoms/toothache",
        ["Causes of toothache", "Non-urgent advice:", "Immediate action required:"],
    ),
    "tooth-decay": ("conditions/tooth-decay", ["Symptoms of tooth decay", "Non-urgent advice:"]),
    "headache": (
        "symptoms/headaches",
        ["What can cause headaches", "When and where to get medical help"],
    ),
    "fever-adult": (
        "symptoms/fever-in-adults",
        ["What is a high temperature?", "Causes of a high temperature", "Urgent advice:"],
    ),
    "fever-child": (
        "symptoms/fever-in-children",
        [
            "Checking a high temperature",
            "Causes of a high temperature in children",
            "Urgent advice:",
            "Immediate action required:",
        ],
    ),
    "sore-throat": (
        "symptoms/sore-throat",
        [
            "Sore throat symptoms",
            "Causes of sore throats",
            "Non-urgent advice: See a GP",
            "Urgent advice:",
            "Immediate action required:",
        ],
    ),
    "abdominal-pain": (
        "symptoms/stomach-ache",
        [
            "Common causes of stomach ache",
            "Urgent advice:",
            "Immediate action required:",
            "Other causes of stomach ache",
        ],
    ),
    "breathing": ("symptoms/shortness-of-breath", ["Immediate action required:"]),
}
NOTES = {
    "toothache": [
        (
            "meaning",
            "Toothache means pain in or around a tooth. It is a symptom, rather than a diagnosis.",
            ["tooth-decay"],
            [],
        ),
        (
            "possible_causes",
            "Possible causes include tooth decay, a cracked or damaged tooth, a loose or broken filling, gum disease, grinding, sensitive teeth, or an infection such as a dental abscess. Several different problems can cause similar pain.",
            ["toothache"],
            [],
        ),
        (
            "uncertainty",
            "Pain alone does not show which cause applies. A dentist needs to examine the tooth and gums; an aching tooth does not definitely mean an abscess.",
            ["toothache", "tooth-decay"],
            [],
        ),
        (
            "professional_followup",
            "Arrange dental assessment for tooth pain, especially if it lasts more than two days, or comes with pain when biting, red gums, a bad taste, fever, or a swollen cheek or jaw. These signs need assessment rather than a diagnosis from chat.",
            ["toothache", "tooth-decay"],
            [],
        ),
        (
            "warning_signs",
            "Seek emergency assessment if the area around the eye or neck is swollen, or if swelling in the mouth or neck makes breathing, swallowing or speaking difficult. Contact the local emergency service or nearest emergency department; do not wait for this app.",
            ["toothache"],
            [],
        ),
        (
            "specific_context",
            "Cold-triggered pain can occur with sensitive teeth. Tooth decay is one possible cause of sensitivity to hot, cold or sweet foods and drinks. This pattern alone does not identify the cause; a dentist can assess it.",
            ["toothache", "tooth-decay"],
            ["cold_trigger"],
        ),
        (
            "specific_context",
            "Pain when biting is a reason for dental assessment. It does not, on its own, distinguish decay, tooth damage, gum problems or infection.",
            ["toothache"],
            ["biting_pain"],
        ),
        (
            "specific_context",
            "Yes, gum disease is among the possible causes of tooth pain. An examination is needed to distinguish it from problems in the tooth itself.",
            ["toothache"],
            ["gum_cause"],
        ),
    ],
    "headache": [
        (
            "meaning",
            "A headache means pain in the head. Many headaches settle, but their pattern and accompanying symptoms matter.",
            ["headache"],
            [],
        ),
        (
            "possible_causes",
            "Possible causes include a cold or flu, stress, dehydration, irregular meals, eyesight problems, alcohol and overuse of painkillers. Some severe headaches are associated with migraine or cluster headache; the symptom alone does not identify the cause.",
            ["headache"],
            [],
        ),
        (
            "uncertainty",
            "A headache can have several causes. General information cannot establish the cause of a particular person's headache or rule out a serious problem.",
            ["headache"],
            [],
        ),
        (
            "professional_followup",
            "Seek medical assessment if headaches recur, worsen or do not improve. Headache with vision or eye problems, vomiting, or pain triggered by coughing or exercise needs urgent medical advice. A child's worsening headache or headache that wakes them at night also needs urgent advice.",
            ["headache"],
            [],
        ),
        (
            "warning_signs",
            "Emergency warning signs include a sudden extremely painful headache, weakness or numbness, difficulty speaking or walking, loss of vision, a seizure, confusion or drowsiness, or headache after a recent head injury. A very high temperature with a stiff neck or sensitivity to light also needs emergency assessment.",
            ["headache"],
            [],
        ),
    ],
    "fever": [
        (
            "meaning",
            "Fever means a raised body temperature. In adults and children, a temperature of 38°C or above is generally considered high. Age and accompanying symptoms matter; a temperature reading alone does not show the cause.",
            ["fever-adult", "fever-child"],
            [],
        ),
        (
            "possible_causes",
            "Fever often occurs while the body fights an infection, such as a cold or flu. In children it can also accompany other childhood illnesses or vaccinations. Some fevers have more serious causes.",
            ["fever-adult", "fever-child"],
            [],
        ),
        (
            "uncertainty",
            "Fever alone does not identify the infection or another cause. This explanation does not assume the person's age, medical history or severity.",
            ["fever-adult", "fever-child"],
            [],
        ),
        (
            "professional_followup",
            "Seek medical advice if fever is worsening or not improving. Children need assessment when fever lasts five days or more, they are dehydrated, or they are not their usual self and there is concern. A baby's exact age changes when assessment is needed.",
            ["fever-adult", "fever-child"],
            [],
        ),
        (
            "warning_signs",
            "Severe breathing difficulty needs emergency help. A feverish child with a stiff neck, a rash that does not fade under pressure, confusion or difficulty waking needs emergency assessment. Babies under three months with a temperature of 38°C or more, and babies aged three to six months with 39°C or more, need urgent medical assessment.",
            ["breathing", "fever-child"],
            [],
        ),
    ],
    "sore_throat": [
        (
            "meaning",
            "A sore throat may feel painful, dry or scratchy, often especially when swallowing. It may also come with a mild cough or swollen neck glands.",
            ["sore-throat"],
            [],
        ),
        (
            "possible_causes",
            "Sore throats are usually caused by viruses such as cold or flu, or irritation from smoking. Bacteria can sometimes cause them. Other possible causes include laryngitis, tonsillitis, strep throat or glandular fever.",
            ["sore-throat"],
            [],
        ),
        (
            "uncertainty",
            "These causes can produce similar symptoms. A sore throat alone does not establish whether the cause is bacterial, and this chat cannot select an antibiotic.",
            ["sore-throat"],
            [],
        ),
        (
            "professional_followup",
            "Seek medical advice if a sore throat does not improve after a week, recurs, or a child under five needs help. A very high temperature, dehydration or a weakened immune system needs urgent medical advice.",
            ["sore-throat"],
            [],
        ),
        (
            "warning_signs",
            "Difficulty breathing, inability to swallow, drooling, a high-pitched breathing sound, or severe symptoms getting worse quickly need emergency help. Contact the local emergency service or nearest emergency department.",
            ["sore-throat"],
            [],
        ),
    ],
    "abdominal_pain": [
        (
            "meaning",
            "Abdominal pain means pain in the belly or tummy. Its location, duration and associated symptoms can matter, but pain alone does not establish a diagnosis.",
            ["abdominal-pain"],
            [],
        ),
        (
            "possible_causes",
            "Common possible causes include trapped wind, indigestion, constipation, a stomach infection or food poisoning. Other causes can require medical assessment; the examples are not a diagnosis or an exhaustive list.",
            ["abdominal-pain"],
            [],
        ),
        (
            "uncertainty",
            "Do not self-diagnose from the location or pattern of pain. Several conditions can cause similar symptoms, and a clinician needs to assess concerning pain.",
            ["abdominal-pain"],
            [],
        ),
        (
            "professional_followup",
            "Seek prompt medical advice for worsening, persistent or recurring pain, or pain during pregnancy. Unexplained weight loss, swallowing problems, painful urination, unusual bleeding or ongoing diarrhoea also need medical advice.",
            ["abdominal-pain"],
            [],
        ),
        (
            "warning_signs",
            "Sudden or severe abdominal pain, pain when the abdomen is touched, vomiting blood or material like coffee grounds, bloody or black sticky stools, inability to pass urine, stool or gas, chest pain, breathing difficulty or collapse need emergency assessment.",
            ["abdominal-pain"],
            [],
        ),
    ],
}


def selected_text(html, headings):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    if not main:
        raise ValueError("Patient page has no main content")
    blocks = []
    for heading in main.find_all(["h2", "h3"]):
        if any(heading.get_text(" ", strip=True).startswith(name) for name in headings):
            container = heading.find_parent("section") or heading.parent
            for ignored in container.find_all(["script", "style", "svg", "img", "video", "iframe"]):
                ignored.decompose()
            text = container.get_text("\n", strip=True)
            if text not in blocks:
                blocks.append(text)
    text = "\n\n".join(blocks)
    if not text or len(text) > 4000:
        raise ValueError("Selected patient sections empty or exceed intact unit capacity")
    full = main.get_text(" ", strip=True)
    import re

    def date(label):
        match = re.search(label + r"\s*(\d{1,2} \w+ \d{4})", full)
        return datetime.strptime(match[1], "%d %B %Y").date().isoformat() if match else None

    return text, date("Page last reviewed:"), date("Next review due:")


def build(output, version, initialize=False):
    if output.exists():
        raise ValueError("Use a new patient release directory")
    bindings_path = ROOT / "configs/patient_source_bindings.json"
    if initialize == bindings_path.exists():
        raise ValueError(
            "Initialize only once; changed sources require explicit source reappraisal"
        )
    expected = json.loads(bindings_path.read_text(encoding="utf-8")) if not initialize else {}
    output.mkdir(parents=True)
    raw = output / "raw"
    raw.mkdir()
    copied = datetime.now(timezone.utc).date().isoformat()
    records, register, bindings = {}, [], {}
    permission_bindings = {}
    with httpx.Client(
        timeout=35,
        follow_redirects=True,
        headers={"User-Agent": "Aster-local-educational-reference-acquisition/1.0"},
    ) as client:
        for name, url in {
            "terms": "https://www.nhs.uk/our-policies/terms-and-conditions/",
            "exclusions": "https://www.nhs.uk/our-policies/terms-and-conditions/content-not-licensed-for-re-use/",
            "ogl": OGL,
        }.items():
            response = client.get(url)
            response.raise_for_status()
            permission_main = BeautifulSoup(response.content.decode("utf-8"), "html.parser").find(
                "main"
            )
            if permission_main is None:
                raise ValueError("Permission page has no main text; manual reappraisal required")
            permission_bindings[name] = hashlib.sha256(
                permission_main.get_text(" ", strip=True).encode()
            ).hexdigest()
            (raw / (name + ".html")).write_bytes(response.content)
        if not initialize and expected.get("_permissions") != permission_bindings:
            raise ValueError("Source permission wording changed; manual reappraisal required")
        bindings["_permissions"] = permission_bindings
        for slug, (path, headings) in SOURCES.items():
            url = "https://www.nhs.uk/" + path + "/"
            response = client.get(url)
            response.raise_for_status()
            if str(response.url) != url:
                raise ValueError("Patient source redirected; manual identity review required")
            (raw / (slug + ".html")).write_bytes(response.content)
            html = response.content.decode("utf-8")
            text, reviewed, due = selected_text(html, headings)
            binding = {
                "selected_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "publisher_review_date": reviewed,
                "next_review_due": due,
            }
            if not initialize and expected.get(slug) != binding:
                raise ValueError(
                    "Patient source changed: " + slug + "; review paired notes before rebuilding"
                )
            bindings[slug] = binding
            raw_hash = hashlib.sha256(response.content).hexdigest()
            basis = {
                "type": "open_license",
                "approved_host": "www.nhs.uk",
                "license": "OGL-3.0",
                "license_url": OGL,
                "terms_url": "https://www.nhs.uk/our-policies/terms-and-conditions/",
                "snapshot_sha256": raw_hash,
                "clinical_review": False,
            }
            record = Reference(
                source_id="patient-" + slug,
                title=BeautifulSoup(html, "html.parser").find("h1").get_text(" ", strip=True),
                url=url,
                publisher="NHS website (original reference)",
                jurisdiction="UK",
                section="Patient information: selected complete sections",
                source_date=reviewed,
                retrieved_date=copied,
                snapshot_id=version,
                text=text,
                topics=[slug],
                keywords=[slug],
                source_type="patient_information",
                permission_basis=basis,
            )
            record.chunk_id = record.stable_id()
            records[slug] = record
            register.append(
                {
                    "source_id": record.source_id,
                    "url": url,
                    "authority": "National public-sector patient-information publisher",
                    "raw_path": "raw/" + slug + ".html",
                    "raw_sha256": raw_hash,
                    "copied_date": copied,
                    "publisher_review_date": reviewed,
                    "next_review_due": due,
                    "clinical_review": False,
                    "permission_basis": basis,
                    "scope": "UK patient guidance; adapted care routes use local services without assuming country",
                    "original_attribution": "Information from the NHS website, as at "
                    + datetime.fromisoformat(copied).strftime("%d%m%y"),
                }
            )
    units = []
    for subject, notes in NOTES.items():
        for i, (role, text, slugs, facets) in enumerate(notes):
            ids = [records[s].chunk_id for s in slugs]
            units.append(
                {
                    "id": subject + "-" + str(i),
                    "subject": subject,
                    "audience": "patient",
                    "intent": "symptom_information",
                    "role": role,
                    "text": text,
                    "citation_ids": ids,
                    "source_hashes": {
                        records[s].chunk_id: records[s].content_hash() for s in slugs
                    },
                    "population": "all_ages",
                    "facets": facets,
                    "review_status": "developer_reviewed",
                    "reviewer": "Developer source comparison; independent medical reviewer not available",
                    "clinical_review": False,
                    "conflict_status": "clear",
                    "appraisal_limitations": "Not an automatic semantic proof or independent medical assessment",
                }
            )
    (output / "records.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in records.values()) + "\n", encoding="utf-8"
    )
    (output / "sources.json").write_text(
        json.dumps({"sources": register}, indent=2) + "\n", encoding="utf-8"
    )
    (output / "units.json").write_text(
        json.dumps({"units": units, "clinical_review": False}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    files = {
        p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output.rglob("*")
        if p.is_file()
    }
    manifest = {
        "schema_version": 1,
        "version": version,
        "files": files,
        "copied_date": copied,
        "maximum_age_days": 7,
        "clinical_review": False,
        "faculty_review": "pending",
        "usage": "Local patient-information pilot; source terms and OGL obligations apply separately from MIT code",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if initialize:
        bindings_path.write_text(json.dumps(bindings, indent=2) + "\n", encoding="utf-8")
    return {
        "release": str(output),
        "sources": len(records),
        "units": len(units),
        "copied": copied,
        "clinical_review": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--initialize-bindings", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.version, args.initialize_bindings), indent=2))
