"""Acquire official Indian references for a review-only, original-paraphrase library.

The catalogue is bibliographic/formulation data, never prescribing guidance.
PowerShell uses the Windows certificate trust store; no TLS verification bypass.
Run with the bundled document Python runtime (pypdf, cryptography, pdfplumber)
located using load_workspace_dependencies; the application venv is not modified.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/references/raw/v2/india"
DATE = "2026-10-07"
SOURCES = {
    "hypertension": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1778941063_hypertensioninadults_final.pdf",
    "asthma": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1725952329_pulmonology_asthma.pdf",
    "diabetes-type-2": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1726567245_diabetes_mellitus_type_2.pdf",
    "hypothyroidism": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1726567243_hypothyroidism.pdf",
    "acute-kidney-injury": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1784807239_acutekidneyinjury-updated.pdf",
    "chronic-kidney-disease": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1784807344_chronickidneydisease-updated.pdf",
    "acute-rhinosinusitis": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1725952292_ent_acute_rhinosinusitis.pdf",
    "chronic-rhinosinusitis": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1725952351_ent_chronic_rhinosinusitis.pdf",
    "pharyngitis": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1725952349_ent_pharyngitis_and_sore_throat.pdf",
    "headache": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1725952344_neurology_headache.pdf",
    "dengue": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1725952338_paediatrics_dengue_fever.pdf",
    "diarrhea": "https://www.icmr.gov.in/icmrobject/uploads/STWs/1725952338_paediatrics_diarrhea.pdf",
    "calpol": "https://india-pharma.gsk.com/media/6355/calpol-tablets-oral-suspension-and-paediatric-drops.pdf",
    "augmentin-duo-tablets": "https://india-pharma.gsk.com/media/6335/augmentin-duo-tablets.pdf",
    "ceftum": "https://india-pharma.gsk.com/media/6357/ceftum-tablets.pdf",
    "eltroxin": "https://india-pharma.gsk.com/media/6368/eltroxin-tablets.pdf",
    "zentel": "https://india-pharma.gsk.com/media/6419/zentel.pdf",
    "nlem2022": "https://www.nppa.gov.in/storage/uploads/pdf/nlem-2022pdf-0cd1d2b28855bf30128875ab19fc5304.pdf",
    "nlem2022-report": "https://www.icmr.gov.in/icmrobject/custom_data/1720338777_report_nlem_2022_f_website.pdf",
    "nlem2022-list": "https://qps.nhsrcindia.org/sites/default/files/2022-09/nlem2022.pdf",
}

# Original, deliberately brief annotations. Edition dates below are printed on
# the documents; a month-only date is not converted into a fabricated day.
WORKFLOWS = [
    (
        "hypertension",
        "Hypertension in adults",
        "May 2026",
        ["hypertension", "hypertension in adults"],
        [
            (
                "assessment",
                "Assessment and monitoring",
                "The May 2026 Indian workflow bases hypertension diagnosis on measured blood pressure, generally on different clinic visits. It assesses cardiovascular risk and recommends checking diabetes, kidney function, urine albumin and lipids. Salt reduction, physical activity, weight management and avoiding tobacco are part of care. Drug selection depends on comorbidities, frailty, tolerance and follow-up measurements.",
                ["hypertension", "blood pressure", "cardiovascular risk"],
                ["hypertension", "pressure", "creatinine", "albumin", "lipids"],
            ),
            (
                "urgent",
                "Severe pressure and urgent assessment",
                "Very high blood pressure accompanied by chest pain, breathlessness, visual disturbance, confusion or sudden neurological symptoms requires emergency assessment for organ injury. The workflow distinguishes this from severe readings without acute organ damage. Medication adherence and adverse effects need review at every visit; combining two renin-angiotensin system blockers increases harm.",
                ["hypertension red flags", "blood pressure medication safety"],
                ["emergency", "breathlessness", "confusion", "adherence", "kidney"],
            ),
        ],
    ),
    (
        "asthma",
        "Asthma",
        "October 2019",
        ["asthma"],
        [
            (
                "assessment",
                "Symptoms, diagnosis and follow-up",
                "This October 2019 Indian workflow describes episodic wheeze, breathlessness, cough and chest tightness as features suggesting asthma. Atopy, triggers and family history support assessment; spirometry with bronchodilator reversibility can help when available. Alternative causes need consideration. Inhaler technique, adherence, triggers and changes in symptom control are reviewed during follow-up. Its historical treatment algorithm needs comparison with current clinical guidance.",
                ["asthma", "spirometry", "inhaler technique"],
                ["wheeze", "spirometry", "inhaler", "triggers", "control"],
            ),
            (
                "urgent",
                "Severe exacerbation warning features",
                "Inability to finish sentences, a silent chest, marked respiratory effort or low oxygen saturation indicate severe illness requiring admission. Altered consciousness, cyanosis, hypotension or bradycardia are life-threatening features requiring urgent transfer to a centre with intensive care. This note is educational and does not supply an individual inhaler or steroid regimen.",
                ["asthma exacerbation", "asthma red flags"],
                ["silent", "cyanosis", "hypotension", "oxygen", "emergency"],
            ),
        ],
    ),
    (
        "diabetes-type-2",
        "Diabetes mellitus type 2",
        "July 2022",
        ["diabetes mellitus type 2", "type 2 diabetes"],
        [
            (
                "assessment",
                "Recognition and investigations",
                "The July 2022 workflow notes that type 2 diabetes may be asymptomatic or cause excessive urination, thirst, recurrent infections, blurred vision and weight loss. Diagnosis uses validated plasma glucose or HbA1c criteria. Assessment includes blood pressure, cardiovascular risk, kidney function, urine albumin, foot sensation and eye examination. Screening considers age, body size and additional risk factors.",
                ["type 2 diabetes", "HbA1c", "diabetes investigations"],
                ["glucose", "hba1c", "albumin", "foot", "retina"],
            ),
            (
                "follow-up",
                "Monitoring and specialist referral",
                "Lifestyle measures and clinician-selected medication accompany follow-up glucose and HbA1c testing. Targets are adjusted for age and significant comorbidity. The workflow includes recurring foot, eye and kidney assessments and referral for uncontrolled hyperglycaemia, abnormal renal function or cardiovascular disease. Pregnancy screening is a separate pathway; these adult educational notes do not prescribe diabetes treatment.",
                ["diabetes monitoring", "diabetes complications", "diabetes referral"],
                ["monitoring", "hyperglycaemia", "kidney", "pregnancy", "referral"],
            ),
        ],
    ),
    (
        "hypothyroidism",
        "Hypothyroidism",
        "July 2022",
        ["hypothyroidism"],
        [
            (
                "assessment",
                "Thyroid tests and clinical features",
                "Fatigue, cold intolerance, constipation, dry skin, weight gain and slowed pulse can raise suspicion, but thyroid blood tests are needed. The July 2022 workflow distinguishes elevated TSH with low thyroid hormone in overt primary hypothyroidism from elevated TSH with normal hormone in subclinical disease. Central hypothyroidism can have low thyroid hormone despite normal or low TSH.",
                ["hypothyroidism", "thyroid function tests", "TSH"],
                ["tsh", "thyroxine", "fatigue", "constipation", "central"],
            ),
            (
                "follow-up",
                "Replacement and follow-up considerations",
                "Replacement and monitoring differ between primary, central and congenital hypothyroidism. Central disease requires evaluation and treatment of coexisting adrenal insufficiency before thyroid replacement to avoid adrenal crisis. Older people and those with coronary disease need cautious initiation. The workflow follows TSH in primary disease and thyroid hormone levels in central disease. It does not justify a personal levothyroxine dose.",
                ["hypothyroidism monitoring", "adrenal insufficiency", "thyroid replacement"],
                ["adrenal", "replacement", "coronary", "monitoring", "congenital"],
            ),
        ],
    ),
    (
        "acute-kidney-injury",
        "Acute kidney injury",
        "July 2026",
        ["acute kidney injury", "AKI"],
        [
            (
                "assessment",
                "Recognition and reversible causes",
                "The July 2026 workflow identifies acute kidney injury through changes in creatinine or reduced urine output after excluding obstruction. It reviews volume loss, infection, toxins, nephrotoxic medicines and pregnancy complications. Assessment distinguishes reduced perfusion, intrinsic kidney injury and outflow obstruction. Urine studies, electrolytes, acid-base status and kidney imaging help identify cause and complications.",
                ["acute kidney injury", "creatinine", "kidney investigations"],
                ["aki", "creatinine", "urine", "obstruction", "nephrotoxic"],
            ),
            (
                "urgent",
                "Complications and referral",
                "Fluid overload, dangerous potassium elevation, refractory acidosis and uraemic complications may require dialysis assessment. Unexplained injury, sepsis, other organ involvement, complicated pregnancy and transplant status are referral triggers. Medication review and correction of reversible causes are central. Follow-up is needed after recovery because kidney injury can have lasting consequences.",
                ["acute kidney injury red flags", "dialysis", "hyperkalemia"],
                ["dialysis", "potassium", "sepsis", "acidosis", "transplant"],
            ),
        ],
    ),
    (
        "chronic-kidney-disease",
        "Chronic kidney disease",
        "July 2026",
        ["chronic kidney disease", "CKD"],
        [
            (
                "assessment",
                "Persistent kidney abnormalities",
                "The July 2026 workflow defines chronic kidney disease as kidney structural or functional abnormalities persisting beyond three months with health implications. Assessment includes estimated filtration rate, urine protein, kidney imaging and complications such as anaemia or mineral imbalance. Diabetes, hypertension, prior kidney injury and nephrotoxic exposure are risk clues. Reversible contributors still need investigation.",
                ["chronic kidney disease", "eGFR", "urine protein"],
                ["ckd", "egfr", "albumin", "anaemia", "creatinine"],
            ),
            (
                "follow-up",
                "Monitoring, medicines and referral",
                "Care addresses cardiovascular risk, glucose, blood pressure, nutrition and vaccination while avoiding nephrotoxic medicines and unproven supplements. Kidney-protective therapies require appropriate patient selection and monitoring. Newly diagnosed disease, rapid progression or new complications warrant nephrology assessment. Renal replacement and conservative-care decisions use symptoms, complications and shared discussion; an eGFR result alone is not a dialysis prescription.",
                [
                    "chronic kidney disease monitoring",
                    "kidney medicine safety",
                    "nephrology referral",
                ],
                ["monitoring", "nephrology", "dialysis", "nutrition", "nephrotoxic"],
            ),
        ],
    ),
    (
        "acute-rhinosinusitis",
        "Acute rhinosinusitis",
        "October 2019",
        ["acute rhinosinusitis"],
        [
            (
                "assessment",
                "Symptoms and examination",
                "The October 2019 workflow assesses nasal blockage or discharge with facial pain or reduced smell, duration and possible dental, allergic or anatomical contributors. Unilateral symptoms, bleeding, crusting or an unusual odour require alternative diagnoses to be considered. Non-resolving or worsening illness may need endoscopy, microbiology and imaging. This historical educational pathway requires current clinical interpretation.",
                ["acute rhinosinusitis", "sinusitis assessment"],
                ["sinusitis", "nasal", "facial", "dental", "endoscopy"],
            ),
            (
                "urgent",
                "Orbital and intracranial warning features",
                "Periorbital swelling, displaced eye position, double vision, restricted eye movement, reduced vision or altered consciousness raise concern for complications and referral. Facial sensory loss or dark/discoloured nasal or palatal tissue may suggest invasive fungal disease, especially with diabetes or immunocompromise. Saline care and medicines in the original workflow depend on clinical assessment; this note does not select an antibiotic.",
                ["sinusitis red flags", "invasive fungal sinusitis"],
                ["orbital", "vision", "fungal", "diabetes", "referral"],
            ),
        ],
    ),
    (
        "chronic-rhinosinusitis",
        "Chronic rhinosinusitis",
        "October 2019",
        ["chronic rhinosinusitis", "CRS"],
        [
            (
                "assessment",
                "Persistent symptoms and contributing factors",
                "The October 2019 workflow considers chronic rhinosinusitis when nasal obstruction or discharge, facial pain or reduced smell persist beyond twelve weeks. It distinguishes disease with and without nasal polyps. Assessment considers allergy, asthma, smoking, irritants, structural disease and medicines that cause congestion. Persistent symptoms may warrant nasal endoscopy and sinus imaging.",
                ["chronic rhinosinusitis", "nasal polyps"],
                ["polyps", "congestion", "allergy", "endoscopy", "asthma"],
            ),
            (
                "safety",
                "Treatment technique and warning signs",
                "The workflow emphasises saline irrigation and correct nasal spray technique. Prolonged topical decongestant use can cause rebound congestion; these agents also have cardiovascular concerns. Eye swelling or movement abnormalities, reduced vision, fever with stiff neck or altered consciousness, and frontal swelling require assessment for complications. The source is historical and does not establish current antibiotic or surgical selection for an individual.",
                ["nasal decongestant safety", "sinusitis complications"],
                ["rebound", "decongestant", "vision", "meningitis", "irrigation"],
            ),
        ],
    ),
    (
        "pharyngitis",
        "Pharyngitis and sore throat",
        "October 2019",
        ["pharyngitis", "sore throat"],
        [
            (
                "assessment",
                "Infectious and non-infectious causes",
                "The October 2019 workflow distinguishes possible streptococcal infection from viral features such as rhinitis or conjunctivitis, and from non-infectious contributors such as reflux or smoking. Clinical scoring, throat culture and antigen testing can support assessment. Hydration and examination for abscess, toxicity or airway compromise matter before treatment decisions. It does not support antibiotics for every sore throat.",
                ["pharyngitis", "sore throat", "streptococcal testing"],
                ["throat", "streptococcus", "culture", "viral", "hydration"],
            ),
            (
                "urgent",
                "Airway and complication warning features",
                "Drooling, breathing difficulty, a muffled voice, unilateral tonsillar enlargement or a membrane spreading beyond the tonsil need urgent clinical assessment for serious causes. Generalised lymphadenopathy can suggest mononucleosis or another diagnosis. The workflow also recognises systemic complications of streptococcal infection. Recurrent significant tonsillitis may require specialist evaluation.",
                ["sore throat red flags", "airway compromise"],
                ["drooling", "airway", "abscess", "diphtheria", "tonsillitis"],
            ),
        ],
    ),
    (
        "headache",
        "Headache",
        "October 2019",
        ["headache"],
        [
            (
                "assessment",
                "Primary and secondary headache assessment",
                "The October 2019 headache workflow distinguishes migraine, tension-type and autonomic headache patterns from secondary disease. History, neurological findings and atypical features guide imaging and referral. Migraine can involve visual aura, light or sound sensitivity and nausea. Sleep, food habits and identifiable triggers are discussed. The source provides a historical clinician pathway rather than personal analgesic advice.",
                ["headache", "migraine", "headache assessment"],
                ["migraine", "aura", "imaging", "neurological", "triggers"],
            ),
            (
                "urgent",
                "Dangerous headache features",
                "Sudden maximal-intensity headache, the first or worst headache, focal neurological signs, fever with neck stiffness, altered consciousness or progressive headache with seizures require urgent assessment. New severe headache during pregnancy or postpartum, or in a person with malignancy or immunosuppression, also raises concern. These features may indicate bleeding, infection, venous thrombosis or other serious disease.",
                ["headache red flags", "thunderclap headache"],
                ["thunderclap", "stiffness", "seizures", "pregnancy", "emergency"],
            ),
        ],
    ),
    (
        "dengue",
        "Dengue fever in children",
        "October 2019",
        ["dengue fever", "dengue"],
        [
            (
                "assessment",
                "Recognition and clinical monitoring",
                "The paediatric October 2019 workflow assesses fever with compatible symptoms and residence in or travel to an endemic area. Blood counts, haematocrit and appropriate dengue tests support clinical evaluation. It distinguishes dengue without warning signs, dengue with warning signs and severe disease. The source advises avoiding NSAIDs for fever and monitoring clinical state alongside laboratory trends.",
                ["dengue", "dengue tests", "paediatric dengue"],
                ["dengue", "haematocrit", "platelets", "ns1", "fever"],
            ),
            (
                "urgent",
                "Warning signs and severe disease",
                "Persistent vomiting, abdominal pain, mucosal bleeding, fluid accumulation, reduced urine output, cold extremities or restlessness warrant prompt assessment. Respiratory distress, severe bleeding, shock or impaired consciousness indicate severe disease and urgent referral. Fluid and transfusion decisions require monitored clinical care; an isolated platelet result does not provide a personal treatment plan.",
                ["dengue warning signs", "dengue shock"],
                ["shock", "bleeding", "vomiting", "urine", "emergency"],
            ),
        ],
    ),
    (
        "diarrhea",
        "Acute diarrhea in children",
        "October 2019",
        ["acute diarrhea", "diarrhea"],
        [
            (
                "assessment",
                "Dehydration and feeding assessment",
                "The October 2019 paediatric workflow assesses duration, blood in stool, vomiting, nutrition and dehydration. Oral rehydration, continued breastfeeding and age-appropriate feeding are central. Preparation must follow the packet's water-volume instructions. Zinc is included in the source's childhood management pathway. Persistent diarrhoea or dysentery needs additional assessment rather than assuming uncomplicated gastroenteritis.",
                ["acute diarrhea", "oral rehydration", "dehydration"],
                ["diarrhea", "dehydration", "ors", "feeding", "zinc"],
            ),
            (
                "urgent",
                "Referral and return warning signs",
                "Poor drinking, repeated vomiting, increasing watery stools, fever or blood in stool require reassessment. Severe dehydration, severe malnutrition, important electrolyte disturbances or systemic infection warrant hospital referral. The workflow uses distinct plans for different dehydration severity. It does not provide an individual fluid volume or antibiotic regimen.",
                ["diarrhea danger signs", "paediatric dehydration"],
                ["vomiting", "blood", "malnutrition", "electrolytes", "referral"],
            ),
        ],
    ),
]

LABELS = [
    (
        "calpol",
        "CALPOL tablets, oral suspension and paediatric drops: India prescribing information",
        "paracetamol",
        "2025-06-11",
        "CAL/PI/IN/2025/02",
        [
            "Calpol",
            "Calpol 500",
            "Calpol 650",
            "Calpol 500+",
            "Calpol 650+",
            "Calpol 120",
            "Calpol 250",
            "Calpol Paediatric Drops",
        ],
        [
            "uncoated tablet",
            "fast-release tablet",
            "paediatric oral suspension",
            "oral drops (suspension)",
        ],
        ["500 mg/tablet", "650 mg/tablet", "120 mg/5 mL", "250 mg/5 mL", "100 mg/mL"],
        [
            (
                "identity",
                "Product identity and use",
                "This Indian CALPOL label covers paracetamol tablets, paediatric suspensions and drops. The indication is mild-to-moderate pain and fever. The verified concentrations differ substantially between liquids; a brand name alone does not identify the preparation. Tablet age restrictions and kidney or liver impairment require review of the exact label. This document does not cover CALPOL T or CALPOL 500 suspension.",
                ["paracetamol", "Calpol", "medicine formulation"],
                ["paracetamol", "calpol", "fever", "pain", "concentration"],
            ),
            (
                "safety",
                "Overdose and safety",
                "Concurrent paracetamol-containing products can produce overdose and serious liver injury. Suspected overdose requires immediate medical assessment even without symptoms. The label identifies hypersensitivity and severe skin reactions, and cautions about liver disease, malnutrition, heavy alcohol use and certain drug combinations. Regular prolonged use can affect coumarin anticoagulation; flucloxacillin coadministration has a metabolic-acidosis warning in susceptible patients. These are selected warnings, not a complete safety screen.",
                ["paracetamol overdose", "paracetamol interactions", "Calpol warnings"],
                ["overdose", "liver", "warfarin", "flucloxacillin", "rash"],
            ),
        ],
    ),
    (
        "augmentin-duo-tablets",
        "AUGMENTIN 625 / 1 g DUO tablets: India prescribing information",
        "amoxicillin + clavulanic acid",
        "2025-10-16",
        "AUG-TAB/PI/IN/2025/01",
        ["Augmentin 625 Duo", "Augmentin 1g Duo"],
        ["film-coated tablet"],
        [
            "amoxicillin 500 mg + clavulanic acid 125 mg/tablet",
            "amoxicillin 875 mg + clavulanic acid 125 mg/tablet",
        ],
        [
            (
                "identity",
                "Exact combination and label scope",
                "The Indian AUGMENTIN DUO tablet label identifies amoxycillin with clavulanic acid in two tablet compositions. It describes selected susceptible bacterial infections, including respiratory, urinary, skin, dental and other sites, with local antibiotic guidelines and susceptibility data informing selection. These tablets are not recommended for children twelve years or younger. This reference does not identify suspensions, ES or injectable AUGMENTIN products.",
                ["amoxicillin clavulanic acid", "Augmentin Duo", "antibiotic stewardship"],
                ["amoxicillin", "amoxycillin", "clavulanic", "augmentin", "susceptibility"],
            ),
            (
                "safety",
                "Allergy, liver and renal considerations",
                "Contraindications include beta-lactam hypersensitivity and previous amoxicillin-clavulanate-associated jaundice or liver dysfunction. Severe allergy, serious skin reactions and antibiotic-associated colitis need clinical attention. Renal function affects selection and dosing; the higher-strength tablet has additional renal restrictions. The label directs whole-tablet use at the start of a meal. A complete interaction and patient-factor review is needed before prescribing.",
                ["Augmentin contraindications", "penicillin allergy", "antibiotic renal safety"],
                ["allergy", "liver", "renal", "colitis", "tablet"],
            ),
        ],
    ),
    (
        "ceftum",
        "CEFTUM tablets: India prescribing information",
        "cefuroxime axetil",
        "2026-07-24",
        "CEF-CL/PI/IN/2026/01",
        ["Ceftum", "Ceftum Tablets 250", "Ceftum Tablets 500"],
        ["film-coated tablet"],
        [
            "cefuroxime 250 mg/tablet as cefuroxime axetil",
            "cefuroxime 500 mg/tablet as cefuroxime axetil",
        ],
        [
            (
                "identity",
                "Oral product and bacterial susceptibility",
                "The Indian CEFTUM tablet label covers cefuroxime axetil, the oral prodrug of cefuroxime, in two strengths. It describes susceptible bacterial respiratory, urinary, skin and selected genital infections and requires local prescribing guidance and susceptibility data. Oral tablets are distinct from injectable cefuroxime sodium. They should be taken after food and swallowed whole; patients unable to swallow whole tablets need another clinical option.",
                ["cefuroxime axetil", "Ceftum", "oral antibiotic"],
                ["cefuroxime", "axetil", "ceftum", "susceptibility", "tablet"],
            ),
            (
                "safety",
                "Allergy, diarrhoea and kidney function",
                "Known cephalosporin allergy is a contraindication, and prior penicillin or other beta-lactam allergy warrants care for cross-sensitivity. Serious allergy and prolonged or significant diarrhoea during or after antibiotic exposure require assessment. Kidney impairment can require dose adjustment. Medicines lowering gastric acidity can reduce bioavailability. This selected summary does not substitute for the full label or a clinician's benefit-risk review.",
                ["Ceftum warnings", "cephalosporin allergy", "cefuroxime renal safety"],
                ["allergy", "colitis", "renal", "diarrhoea", "antacid"],
            ),
        ],
    ),
    (
        "eltroxin",
        "ELTROXIN tablets: India prescribing information",
        "levothyroxine sodium",
        "2026-07-10",
        "ELT/PI/IN/2026/02",
        ["Eltroxin", "Thyroxine Sodium", "Levothyroxine Sodium"],
        ["uncoated tablet"],
        [
            "12.5 mcg/tablet",
            "25 mcg/tablet",
            "37.5 mcg/tablet",
            "50 mcg/tablet",
            "62.5 mcg/tablet",
            "75 mcg/tablet",
            "88 mcg/tablet",
            "100 mcg/tablet",
            "125 mcg/tablet",
            "150 mcg/tablet",
        ],
        [
            (
                "identity",
                "Thyroid replacement product",
                "The Indian ELTROXIN label identifies thyroxine sodium tablets for hypothyroidism. Laboratory tests and clinical examination determine individual replacement needs; older people or those with coronary disease need particular caution. The label directs whole-tablet administration before breakfast and does not support crushing because of insufficient data. Tablets without a score line must not be halved. Not all listed presentations may be marketed in India.",
                ["levothyroxine sodium", "Eltroxin", "hypothyroidism replacement"],
                ["eltroxin", "thyroxine", "levothyroxine", "tsh", "tablet"],
            ),
            (
                "safety",
                "Contraindications and over-replacement",
                "Contraindications include untreated thyrotoxicosis, untreated adrenal or pituitary insufficiency and certain acute cardiac inflammatory or infarction states. Over-replacement can cause hyperthyroid symptoms and cardiac harm, and prolonged suppressive exposure can affect bone. Concurrent medicines and absorption effects require review. The label's formulation limitations are especially relevant in children unable to swallow tablets. This reference does not provide an individual thyroid dose.",
                ["Eltroxin contraindications", "thyroid medicine safety"],
                ["adrenal", "cardiac", "hyperthyroidism", "bone", "children"],
            ),
        ],
    ),
    (
        "zentel",
        "ZENTEL tablets and suspension: India prescribing information",
        "albendazole",
        "2026-07-08",
        "ZEN/PI/IN/2026/01",
        ["Zentel"],
        ["uncoated chewable tablet", "oral suspension"],
        ["400 mg/tablet", "400 mg/10 mL"],
        [
            (
                "identity",
                "Parasite-specific label scope",
                "The Indian ZENTEL label covers albendazole chewable tablets and suspension for specified intestinal and tissue parasite infections. It distinguishes short-course intestinal treatment from longer systemic-infection regimens. Neurocysticercosis and echinococcosis require condition-specific clinical management; a worming brand name alone does not justify those regimens. The suspension concentration and tablet composition must be checked separately.",
                ["albendazole", "Zentel", "anthelmintic"],
                ["albendazole", "zentel", "parasites", "echinococcosis", "neurocysticercosis"],
            ),
            (
                "safety",
                "Pregnancy, liver and blood-count considerations",
                "The label contraindicates use in pregnancy or suspected pregnancy and in hypersensitivity to its components. Systemic treatment requires liver-function and blood-count monitoring because liver abnormalities and marrow suppression can occur. Treating unrecognised neurocysticercosis can provoke neurological symptoms through parasite-related inflammation. Dizziness and gastrointestinal effects are also described. Selected warnings here are insufficient for an individual prescription or complete contraindication screen.",
                ["albendazole pregnancy", "Zentel warnings", "anthelmintic monitoring"],
                ["pregnancy", "liver", "blood", "seizures", "monitoring"],
            ),
        ],
    ),
]


def section_objects(sections):
    return [
        {"id": sid, "title": title, "text": body, "topics": topics, "keywords": keywords}
        for sid, title, body, topics, keywords in sections
    ]


def product_metadata(key):
    definitions = {
        "calpol": (
            "India GSK CALPOL paracetamol tablets, paediatric suspensions and drops",
            ["500mg", "650mg"],
            [
                ("Calpol 500", "uncoated tablet", "500 mg/tablet", "500mg"),
                ("Calpol 650", "uncoated tablet", "650 mg/tablet", "650mg"),
                ("Calpol 500+", "fast-release tablet with Optizorb", "500 mg/tablet", "500mg"),
                ("Calpol 650+", "uncoated tablet with Optizorb", "650 mg/tablet", "650mg"),
                ("Calpol 120", "paediatric oral suspension", "120 mg/5 mL", None),
                ("Calpol 250", "paediatric oral suspension", "250 mg/5 mL", None),
                ("Calpol Paediatric Drops", "oral drops (suspension)", "100 mg/mL", None),
            ],
        ),
        "augmentin-duo-tablets": (
            "India GSK AUGMENTIN 625 / 1 g DUO amoxicillin-clavulanic acid tablets",
            ["500mg+125mg", "875mg+125mg"],
            [
                (
                    "Augmentin 625 Duo",
                    "film-coated tablet",
                    "amoxicillin 500 mg + clavulanic acid 125 mg/tablet",
                    "500mg+125mg",
                ),
                (
                    "Augmentin 1g Duo",
                    "film-coated tablet",
                    "amoxicillin 875 mg + clavulanic acid 125 mg/tablet",
                    "875mg+125mg",
                ),
            ],
        ),
        "ceftum": (
            "India GSK CEFTUM oral cefuroxime axetil tablets",
            ["250mg", "500mg"],
            [
                (
                    "Ceftum Tablets 250",
                    "film-coated tablet",
                    "cefuroxime 250 mg/tablet as cefuroxime axetil",
                    "250mg",
                ),
                (
                    "Ceftum Tablets 500",
                    "film-coated tablet",
                    "cefuroxime 500 mg/tablet as cefuroxime axetil",
                    "500mg",
                ),
            ],
        ),
        "eltroxin": (
            "India GSK ELTROXIN thyroxine sodium oral tablets",
            [f"{strength}mcg" for strength in [12.5, 25, 37.5, 50, 62.5, 75, 88, 100, 125, 150]],
            [
                ("Eltroxin", "uncoated tablet", f"{strength} mcg/tablet", f"{strength}mcg")
                for strength in [12.5, 25, 37.5, 50, 62.5, 75, 88, 100, 125, 150]
            ],
        ),
        "zentel": (
            "India GSK ZENTEL albendazole chewable tablets and suspension",
            ["400mg"],
            [
                ("Zentel", "uncoated chewable tablet", "400 mg/tablet", "400mg"),
                ("Zentel", "oral suspension", "400 mg/10 mL", None),
            ],
        ),
    }
    identity, matches, products = definitions[key]
    return {
        "product_identity": identity,
        "match_strengths": matches,
        "products": [
            {
                "brand": brand,
                "formulation": form,
                "strength": strength,
                "route": "oral",
                "jurisdiction": "India",
                "match_strengths": [match] if match else [],
                "source_locator": "PDF sections 1-3: generic name, composition and dosage form",
            }
            for brand, form, strength, match in products
        ],
        "prescription_matching_limits": "Only verified solid-strength tokens are exposed for matching. Liquid concentration ratios remain source evidence only. Product identity, formulation, age, route and label context require independent review; a matching token does not endorse a prescription.",
    }


def build_documents():
    documents = []
    for key, title, edition, aliases, sections in WORKFLOWS:
        documents.append(
            {
                "id": f"india-icmr-{key}",
                "title": f"ICMR Standard Treatment Workflow: {title}",
                "url": SOURCES[key],
                "publisher": "Indian Council of Medical Research / Department of Health Research, Ministry of Health and Family Welfare",
                "jurisdiction": "India",
                "source_date": None,
                "retrieved_date": DATE,
                "version": f"Printed STW edition: {edition}; snapshot {DATE}",
                "terms": "Original brief educational paraphrase of a publicly accessible advisory government workflow. Source retains copyright; no open licence is asserted. Full raw snapshot is ignored audit evidence, not redistributed. Individual care remains with the treating clinician; historical editions need current clinical interpretation.",
                "clinical_review": False,
                "source_type": "education",
                "entity": None,
                "formulations": [],
                "strengths": [],
                "routes": [],
                "aliases": aliases,
                "sections": section_objects(sections),
                **snapshot_metadata(key),
            }
        )
    for (
        key,
        title,
        entity,
        source_date,
        version,
        aliases,
        formulations,
        strengths,
        sections,
    ) in LABELS:
        documents.append(
            {
                "id": f"india-gsk-{key}",
                "title": title,
                "url": SOURCES[key],
                "publisher": "GlaxoSmithKline Pharmaceuticals Limited, India",
                "jurisdiction": "India",
                "source_date": source_date,
                "retrieved_date": DATE,
                "version": version,
                "terms": "Original brief paraphrase of publicly accessible GSK India prescribing information. GSK retains copyright and trademarks; no redistribution/open licence is asserted. Source is marked for registered medical practitioners, hospitals or laboratories. Full label retained only as ignored audit evidence. Selected educational warnings are incomplete and do not constitute prescribing guidance.",
                "clinical_review": False,
                "source_type": "drug_label",
                "entity": entity,
                "formulations": formulations,
                "strengths": strengths,
                "routes": ["oral"],
                "aliases": aliases,
                "sections": section_objects(sections),
                **snapshot_metadata(key),
                **product_metadata(key),
            }
        )
    for doc in documents:
        assert sum(len(s["text"].split()) for s in doc["sections"]) <= 180, doc["id"]
    output = ROOT / "data/knowledge_v2/india.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"documents": documents}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return documents


def snapshot_metadata(key):
    path = RAW / f"{key}.pdf"
    return {
        "raw_snapshot_path": path.relative_to(ROOT).as_posix(),
        "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def normal_name(text):
    text = re.sub(r"\([ABC]\)", "", text)
    text = re.sub(r"\s*\+\s*", " + ", text)
    return re.sub(r"\s+", " ", text.replace("*", "").replace("\n", " ")).strip()


def formulation_lines(text):
    """Preserve numeric source facts and join visual line wrapping, not infer doses."""
    starts = re.compile(
        r"^(?:Tablet|Capsule|Injection|Powder|Oral|Eye|Ear|Cream|Ointment|Pessary|Inhalation|Respirator|Suppository|Nasal|Sublingual|Modified|Topical|Liquid|Gel|Solution|Dry Syrup|Sachet|Effervescent|Conventional|Transdermal|Lotion|As licensed|As Licensed|Dispersible|Vaginal|Implant|Contains|Soluble|Lyophilized|Strips|Strip|Spray|Granules|Emulsion|Suspension|Concentrate|Patch|Rectal|Intravenous|Water|Soft|Chewable)\b",
        re.I,
    )
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if starts.match(line) or not lines:
            lines.append(line)
        else:
            lines[-1] += " " + line
    return lines


def build_catalogue():
    import pdfplumber

    key = "nlem2022-list"
    path = RAW / f"{key}.pdf"
    pdf = PdfReader(path)
    entries = []
    for page_idx in range(85, 101):
        for line in pdf.pages[page_idx].extract_text(extraction_mode="layout").splitlines():
            match = re.match(r"^\s*(\d+)\.\s+(.+?)\s*$", line)
            if not match:
                continue
            number, source_name = match.groups()
            entries.append(
                {
                    "name": normal_name(source_name),
                    "source_name": source_name,
                    "alphabetical_number": int(number),
                    "alphabetical_page": page_idx + 1,
                    "formulations": [],
                    "strengths": [],
                    "section": "Alphabetical list of medicines in NLEM 2022",
                    "entry_number": None,
                    "page": page_idx + 1,
                    "listings": [],
                }
            )
    assert [e["alphabetical_number"] for e in entries] == list(range(1, 385))
    # Parse only actual four-column drug rows. Repeated therapeutic entries and
    # their formulation-specific care levels remain separate evidence listings.
    listings = []
    active = None
    with pdfplumber.open(path) as tables_pdf:
        for page_idx in range(3, 84):
            for table in tables_pdf.pages[page_idx].extract_tables():
                if not table or max(len(row) for row in table) < 4:
                    continue
                for row in table:
                    if len(row) < 4:
                        continue
                    number = (row[0] or "").strip()
                    name = row[1]
                    level = row[2]
                    forms = "\n".join(v for v in row[3:] if v)
                    if re.fullmatch(r"\d+(?:\.\d+)+\.?", number) and name and forms:
                        active = {
                            "name": normal_name(name),
                            "source_name": re.sub(r"\s+", " ", name).strip(),
                            "entry_number": number.rstrip("."),
                            "section": number.rstrip(".").rsplit(".", 1)[0],
                            "page": page_idx + 1,
                            "source_formulation_text": forms,
                            "formulations": formulation_lines(forms),
                            "care_levels": re.sub(r"\s+", "", level or ""),
                        }
                        listings.append(active)
                    elif (
                        not number
                        and not name
                        and forms
                        and active
                        and re.fullmatch(r"[PST,\s]+", level or "")
                    ):
                        # A split care-level cell is part of the preceding drug.
                        active["source_formulation_text"] += "\n" + forms
                        active["formulations"].extend(formulation_lines(forms))
                        active.setdefault("additional_care_level_rows", []).append(
                            {
                                "care_levels": re.sub(r"\s+", "", level),
                                "page": page_idx + 1,
                                "formulations": formulation_lines(forms),
                            }
                        )
    by_name = {}
    for listing in listings:
        by_name.setdefault(listing["name"].casefold(), []).append(listing)
    for entry in entries:
        matches = by_name.get(entry["name"].casefold(), [])
        entry["listings"] = [
            {k: v for k, v in m.items() if k not in ("name", "source_name")} for m in matches
        ]
        if matches:
            entry["formulations"] = list(
                dict.fromkeys(f for m in matches for f in m["formulations"])
            )
            # A strength is retained together with its source formulation to avoid
            # detaching mixture components, concentrations, or release types.
            entry["strengths"] = [f for f in entry["formulations"] if re.search(r"\d", f)]
            entry["section"] = matches[0]["section"]
            entry["entry_number"] = matches[0]["entry_number"]
            entry["page"] = matches[0]["page"]
    source = {
        "url": SOURCES[key],
        "publisher": "Ministry of Health and Family Welfare, Government of India; official NHSRC copy",
        "jurisdiction": "India",
        "version": "National List of Essential Medicines 2022; original signed list, 135 PDF pages",
        "source_date": "2022-09-13",
        "retrieved_date": DATE,
        "terms": "Factual catalogue transcription of generic names and source formulation cells from the publicly accessible official NLEM 2022 list. No open licence asserted. Raw PDF retained only as ignored audit evidence. Clinical prose, indications and prescribing recommendations are not reproduced.",
        **snapshot_metadata(key),
    }
    catalogue = {
        "source": source,
        "scope": "Catalogue only. A NLEM listing or formulation does not prove a product's indication, safety, contraindications, current availability, approval status or constitute a prescription. No branded product aliases are inferred from NLEM.",
        "page_basis": "All page values are one-based PDF page positions, including the cover; printed page numbers are normally one lower.",
        "extraction_notes": "Names preserve official source spelling; component letters A/B/C and footnote asterisks are removed only in name, while source_name retains them. Exact-name matches attach extracted therapeutic-table cells. No fuzzy name matching; unresolved rows remain listed separately. Empty formulation fields mean extraction unavailable, not absence of an approved formulation. Strengths retain whole formulation strings to avoid losing component or concentration context. Formulation extraction is audit-only and not clinically reviewed.",
        "clinical_review": False,
        "coverage": {
            "alphabetical_entries": len(entries),
            "therapeutic_listings_extracted": len(listings),
            "entries_with_formulations": sum(bool(e["formulations"]) for e in entries),
            "complete_formulation_coverage_asserted": False,
        },
        "entries": entries,
        "unmatched_therapeutic_listings": [
            m
            for m in listings
            if m["name"].casefold() not in {e["name"].casefold() for e in entries}
        ],
    }
    output = ROOT / "data/knowledge_v2/india_catalog.json"
    output.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return catalogue


def acquire(item):
    key, url = item
    path = RAW / f"{key}.pdf"
    if not path.exists():
        command = f"Invoke-WebRequest -Uri '{url}' -OutFile '{path.as_posix()}'"
        subprocess.run(
            ["pwsh", "-NoProfile", "-Command", command],
            check=True,
            capture_output=True,
            timeout=120,
        )
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"Not a PDF: {key}")
    pdf = PdfReader(path)
    body = "\n\n".join(
        f"[PDF page {i + 1}]\n{page.extract_text()}" for i, page in enumerate(pdf.pages)
    )
    (RAW / f"{key}.txt").write_text(body, encoding="utf-8")
    print(key, len(pdf.pages), len(data), flush=True)
    return {
        "id": key,
        "url": url,
        "raw_snapshot_path": path.relative_to(ROOT).as_posix(),
        "raw_sha256": hashlib.sha256(data).hexdigest(),
        "pages": len(pdf.pages),
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        entries = list(pool.map(acquire, SOURCES.items()))
    (RAW / "manifest.json").write_text(
        json.dumps({"retrieved_date": DATE, "sources": entries}, indent=2), encoding="utf-8"
    )
    documents = build_documents()
    catalogue = build_catalogue()
    print(json.dumps({"documents": len(documents), "catalogue": catalogue["coverage"]}), flush=True)


if __name__ == "__main__":
    main()
