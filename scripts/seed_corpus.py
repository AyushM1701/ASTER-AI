"""Write the small, explicitly curated educational starter corpus, never patient data."""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.retrieval import Reference  # noqa: E402

DATE = "2026-10-06"

# These original short notes were checked against the linked official pages.
# They are paraphrases, not clinical guidelines or medically reviewed advice.
SOURCES = [
    (
        "asthma",
        "Asthma: overview",
        "https://www.nhlbi.nih.gov/health/asthma",
        ["asthma"],
        ["definition", "airway", "breathing", "chronic", "what"],
        "Asthma involves persistent airway inflammation. The airways can narrow in response "
        "to triggers, making breathing harder. It is a long-term condition; symptom patterns "
        "and severity differ between people. A clinician assesses symptoms and lung function "
        "to establish a diagnosis and care plan.",
    ),
    (
        "blood-pressure",
        "High blood pressure: overview",
        "https://www.nhlbi.nih.gov/health/high-blood-pressure",
        ["blood pressure", "hypertension", "systolic", "diastolic"],
        ["numbers", "meaning", "what", "measurement"],
        "Blood pressure describes the force that circulating blood places on artery walls. "
        "The systolic number represents pressure during a heartbeat; the diastolic number "
        "represents pressure as the heart relaxes. Persistently elevated pressure can damage "
        "the heart and blood vessels. A single reading is not a complete clinical assessment.",
    ),
    (
        "sleep-apnea",
        "Sleep apnea: overview",
        "https://www.nhlbi.nih.gov/health/sleep-apnea",
        ["sleep apnea", "sleep apnoea"],
        ["sleep", "breathing", "obstructive", "central", "what"],
        "Sleep apnea involves repeated interruptions of breathing during sleep. In obstructive "
        "sleep apnea, the upper airway becomes blocked. In central sleep apnea, the brain does "
        "not send the usual signals controlling breathing. Sleep studies help clinicians "
        "evaluate the condition. Snoring alone cannot establish the diagnosis.",
    ),
    (
        "diabetes",
        "Diabetes: overview",
        "https://www.niddk.nih.gov/health-information/diabetes/overview/what-is-diabetes",
        ["diabetes", "insulin", "blood glucose"],
        ["type", "glucose", "insulin", "what", "definition"],
        "Diabetes involves blood glucose remaining too high. Insulin helps glucose enter "
        "cells. In type 1 diabetes, the body makes little or no insulin. In type 2 diabetes, "
        "insulin action and production are insufficient to maintain usual glucose levels. "
        "Over time, high glucose can harm organs including the kidneys, eyes, and heart.",
    ),
    (
        "pneumonia",
        "Pneumonia: overview",
        "https://www.nhlbi.nih.gov/health/pneumonia",
        ["pneumonia"],
        ["infection", "lung", "causes", "what", "symptoms"],
        "Pneumonia is a lung infection caused by organisms such as bacteria, viruses, or "
        "fungi. Infected air sacs may accumulate fluid or pus. Symptoms can include cough, "
        "fever, chills, and difficulty breathing. History, examination, and appropriate "
        "tests contribute to diagnosis; an experimental image score alone cannot diagnose it.",
    ),
    (
        "anemia",
        "Anemia: overview",
        "https://www.nhlbi.nih.gov/health/anemia",
        ["anemia", "anaemia", "hemoglobin", "haemoglobin"],
        ["blood", "cells", "oxygen", "what", "fatigue"],
        "Anemia involves too few healthy red blood cells to adequately carry oxygen. It can "
        "cause fatigue or weakness, with several possible underlying causes. Iron deficiency "
        "is one type, but not every anemia is caused by low iron. Clinical history and "
        "laboratory testing help distinguish the cause before selecting treatment.",
    ),
    (
        "copd",
        "COPD: overview",
        "https://www.nhlbi.nih.gov/health/copd",
        ["copd", "chronic obstructive pulmonary disease"],
        ["lung", "airflow", "what", "definition"],
        "Chronic obstructive pulmonary disease describes lung conditions that limit airflow "
        "and make breathing difficult. Emphysema and chronic bronchitis are common components. "
        "Tobacco smoke is an important risk factor, but other exposures and inherited "
        "factors can contribute. Lung function testing is part of clinical assessment.",
    ),
    (
        "pleura",
        "Pleural disorders: overview",
        "https://www.nhlbi.nih.gov/health/pleural-disorders",
        ["pleural", "effusion", "pneumothorax"],
        ["fluid", "air", "lung", "term", "what"],
        "The pleura consists of membranes around the lungs and inside the chest. A pleural "
        "effusion is extra fluid in the space between these membranes. A pneumothorax "
        "involves air in that space. These terms describe different processes; a research "
        "model score does not establish whether either is present.",
    ),
    (
        "metformin-label",
        "Metformin hydrochloride tablets: US reference label",
        "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1a7f7ef3-a94b-4ff6-a9f2-f5de4a99c7f6",
        ["metformin", "metformin hydrochloride"],
        ["purpose", "what", "diabetes", "medicine"],
        "This US label describes metformin hydrochloride immediate-release tablets as a "
        "prescription medicine used alongside diet and exercise for glucose control in "
        "type 2 diabetes. It includes contraindications and a serious lactic-acidosis "
        "warning. This general description does not establish suitability, dosing, or "
        "instructions for an individual or a different local product.",
    ),
]


def main():
    records, register = [], []
    for source_id, title, url, topics, keywords, text in SOURCES:
        record = dict(
            source_id=source_id,
            title=title,
            url=url,
            publisher="NLM DailyMed" if source_id.endswith("label") else "NIH",
            jurisdiction="US",
            section="Overview (developer-curated paraphrase)",
            source_date=None,
            retrieved_date=DATE,
            snapshot_id="starter-2026-10-06",
            text=text,
            topics=topics,
            keywords=keywords,
        )
        if source_id == "metformin-label":
            record.update(
                source_type="drug_label",
                entity="metformin hydrochloride",
                formulations=["tablet", "immediate-release tablet", "immediate release tablet"],
                strengths=["500mg", "850mg", "1000mg"],
            )
        records.append(record)
        register.append(
            dict(
                source_id=source_id,
                title=title,
                url=url,
                publisher=record["publisher"],
                jurisdiction="US",
                language="en",
                approval="developer_reviewed",
                clinical_review=False,
                retrieved_date=DATE,
                terms="Original brief paraphrase; linked primary reference retained. "
                "NHLBI attribution and use policy applies to NHLBI material.",
                local_path="data/references/normalized/seed.jsonl",
                checksum=Reference.model_validate(record).content_hash(),
                checksum_format="sha256-canonical-record-v1",
            )
        )
    folder = ROOT / "data/references/normalized"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "seed.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    (ROOT / "configs").mkdir(exist_ok=True)
    (ROOT / "configs/sources.yaml").write_text(
        yaml.safe_dump({"sources": register}, sort_keys=False), encoding="utf-8"
    )
    print(f"Wrote {len(records)} curated reference notes. No clinical review claimed.")


if __name__ == "__main__":
    main()
