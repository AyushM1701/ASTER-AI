"""Acquire official-source snapshots for original v2 educational topic notes.

No production corpus or application state is modified. The source annotations in
this script are original paraphrases, not clinical review or treatment guidance.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/references/raw/v2/topics"
OUTPUT = ROOT / "data/knowledge_v2/topics.json"
DATE = "2026-10-07"

SOURCES = [
    ("asthma", "Asthma", "asthma.html"),
    ("copd", "Chronic obstructive pulmonary disease (COPD)", "copd.html"),
    ("pneumonia", "Pneumonia", "pneumonia.html"),
    ("acute-bronchitis", "Acute bronchitis", "acutebronchitis.html"),
    ("sleep-apnea", "Sleep apnea", "sleepapnea.html"),
    ("hypertension", "High blood pressure", "highbloodpressure.html"),
    ("coronary-artery-disease", "Coronary artery disease", "coronaryarterydisease.html"),
    ("heart-failure", "Heart failure", "heartfailure.html"),
    ("arrhythmia", "Arrhythmia", "arrhythmia.html"),
    ("stroke", "Stroke", "stroke.html"),
    ("diabetes", "Diabetes", "diabetes.html"),
    ("hypothyroidism", "Hypothyroidism", "hypothyroidism.html"),
    ("hyperthyroidism", "Hyperthyroidism", "hyperthyroidism.html"),
    ("chronic-kidney-disease", "Chronic kidney disease", "chronickidneydisease.html"),
    ("kidney-stones", "Kidney stones", "kidneystones.html"),
    ("urinary-tract-infection", "Urinary tract infection", "urinarytractinfections.html"),
    ("gerd", "Gastroesophageal reflux disease (GERD)", "gerd.html"),
    ("irritable-bowel-syndrome", "Irritable bowel syndrome", "irritablebowelsyndrome.html"),
    ("constipation", "Constipation", "constipation.html"),
    ("diarrhea", "Diarrhea", "diarrhea.html"),
    ("gastroenteritis", "Viral gastroenteritis", "gastroenteritis.html"),
    ("gallstones", "Gallstones", "gallstones.html"),
    ("pancreatitis", "Pancreatitis", "pancreatitis.html"),
    ("hepatitis", "Hepatitis", "hepatitis.html"),
    ("migraine", "Migraine", "migraine.html"),
    ("epilepsy", "Epilepsy", "epilepsy.html"),
    ("peripheral-neuropathy", "Peripheral neuropathy", "peripheralnervedisorders.html"),
    ("eczema", "Eczema", "eczema.html"),
    ("cellulitis", "Cellulitis", "cellulitis.html"),
    ("shingles", "Shingles", "shingles.html"),
    ("anemia", "Anemia", "anemia.html"),
    ("cbc", "Complete blood count (CBC)", "lab-tests/complete-blood-count-cbc/"),
    ("hemoglobin", "Hemoglobin test", "lab-tests/hemoglobin-test/"),
    ("hba1c", "Hemoglobin A1C (HbA1c) test", "lab-tests/hemoglobin-a1c-hba1c-test/"),
    ("creatinine", "Creatinine test", "lab-tests/creatinine-test/"),
    ("bun", "Blood urea nitrogen (BUN) test", "lab-tests/bun-blood-urea-nitrogen/"),
    (
        "egfr",
        "Estimated glomerular filtration rate (eGFR) and GFR tests",
        "lab-tests/glomerular-filtration-rate-gfr-test/",
    ),
    ("electrolytes", "Electrolyte panel", "lab-tests/electrolyte-panel/"),
    ("liver-function", "Liver function tests", "lab-tests/liver-function-tests/"),
    ("ecg", "Electrocardiogram (ECG)", "lab-tests/electrocardiogram/"),
    ("chest-xray", "Chest X-ray", "https://www.nhlbi.nih.gov/health/lung-tests"),
    ("atelectasis", "Atelectasis", "https://www.nhlbi.nih.gov/health/ventilator/risks"),
    (
        "pleural-effusion",
        "Pleural effusion",
        "https://www.nhlbi.nih.gov/health/pleural-disorders/types",
    ),
    ("pulmonary-edema", "Pulmonary edema", "https://www.nhlbi.nih.gov/health/ventilator/risks"),
    ("pneumothorax", "Pneumothorax", "https://www.nhlbi.nih.gov/health/pleural-disorders/types"),
    (
        "prescription-label",
        "Prescription labeling terminology",
        "https://www.fda.gov/drugs/fdas-labeling-resources-human-prescription-drugs/frequently-asked-questions-about-labeling-prescription-medicines",
    ),
]

# Each note contains aliases, two independently understandable short sections,
# search keywords, and section titles. These were checked against the snapshots.
NOTES = {
    "asthma": (
        ["asthma", "asthma attack", "asthma flare-up"],
        "Asthma is a long-term lung disease affecting the airways that carry air into and out of the lungs. Inflammation and narrowing can make breathing difficult. A worsening episode is called an asthma attack or flare-up. Its exact cause is unknown; genes and environmental exposures probably both contribute.",
        "Asthma can cause wheezing, cough, chest tightness, and shortness of breath. Symptoms and triggers differ between people. Assessment can include medical history, examination, and lung function tests such as spirometry. Some attacks become life-threatening; the name of a symptom alone does not establish an asthma diagnosis.",
        ["airway", "inflammation", "wheezing", "cough", "spirometry", "triggers"],
        "What asthma means",
        "Symptoms and assessment",
    ),
    "copd": (
        ["COPD", "chronic obstructive pulmonary disease", "emphysema", "chronic bronchitis"],
        "COPD is a group of lung diseases that limit airflow and usually worsen over time. It commonly includes emphysema, which damages air sacs, and chronic bronchitis, which inflames airways and increases mucus. Long-term exposure to lung irritants is a common cause; tobacco smoke is the main cause in the United States.",
        "COPD symptoms can include persistent cough, mucus, wheezing, chest tightness, and breathlessness during activity. Early disease may produce few symptoms. Evaluation considers smoking and other exposures, medical history, and tests such as lung function testing and chest imaging. Treatments may improve symptoms and slow progression, but there is no cure.",
        ["airflow", "air sacs", "mucus", "smoking", "breathlessness", "lung function"],
        "What COPD means",
        "Symptoms and assessment",
    ),
    "pneumonia": (
        ["pneumonia", "lung infection", "bronchopneumonia"],
        "Pneumonia is an infection of one or both lungs in which air sacs may fill with fluid or pus. Bacteria, viruses, or fungi can cause it; aspiration of food or fluid can also lead to pneumonia. Severity varies with the cause, age, and underlying health.",
        "Pneumonia may cause fever, chills, cough with mucus, shortness of breath, or pain with breathing. Older adults and people with weakened immunity may have less typical symptoms, including confusion. Clinicians use history and examination and may order chest imaging, blood tests, or oxygen measurements. Similar symptoms can occur with other respiratory illnesses.",
        ["infection", "air sacs", "fever", "cough", "aspiration", "oxygen", "chest x-ray"],
        "What pneumonia means",
        "Symptoms and assessment",
    ),
    "acute-bronchitis": (
        ["acute bronchitis", "bronchitis", "chest cold"],
        "Acute bronchitis is short-term inflammation of the bronchial tubes, the airways leading to the lungs. It often follows infection with viruses that also cause colds or influenza. Tobacco smoke, dust, fumes, and other irritants can contribute; bacteria cause it less often.",
        "Acute bronchitis commonly causes cough, often with mucus, and can cause wheezing, mild fever, chest tightness, or breathlessness. The cough can remain for weeks after the infection clears. Assessment includes questions about symptoms and listening to breathing; additional tests may be needed. Antibiotics do not treat bronchitis caused by a virus.",
        ["bronchi", "inflammation", "cough", "mucus", "virus", "antibiotics"],
        "What acute bronchitis means",
        "Symptoms and assessment",
    ),
    "sleep-apnea": (
        ["sleep apnea", "sleep apnoea", "obstructive sleep apnea", "obstructive sleep apnoea"],
        "Sleep apnea involves repeated pauses or very shallow breathing during sleep. The most common form, obstructive sleep apnea, occurs when the airway collapses or becomes blocked. Breathing may restart with a snort or choking sound. Loud snoring is common, but snoring by itself does not prove sleep apnea.",
        "Repeatedly interrupted sleep can cause daytime drowsiness and increase the risk of accidents. Factors associated with sleep apnea include excess weight, family history, and small airways. Enlarged tonsils or adenoids can contribute in children. Diagnosis combines medical and family history, physical examination, and results from a sleep study.",
        ["sleep", "snoring", "airway", "obstruction", "drowsiness", "sleep study"],
        "What sleep apnea means",
        "Effects and assessment",
    ),
    "hypertension": (
        ["high blood pressure", "hypertension", "systolic pressure", "diastolic pressure"],
        "Blood pressure is the force of blood against artery walls. Systolic pressure is measured while the heart pumps; diastolic pressure is measured while it rests between beats. Persistently high pressure can strain the heart and contribute to heart attack, stroke, heart failure, or kidney failure.",
        "High blood pressure usually causes no symptoms. A clinician checks it with a cuff and generally uses repeated readings at separate appointments to establish a diagnosis. Primary hypertension develops over time; secondary hypertension is related to another condition or certain medicines. Assessment in children takes age, height, and sex into account.",
        ["arteries", "pressure", "cuff", "systolic", "diastolic", "measurement"],
        "What blood pressure means",
        "Assessment and causes",
    ),
    "coronary-artery-disease": (
        ["coronary artery disease", "CAD", "coronary heart disease", "coronary atherosclerosis"],
        "Coronary artery disease affects vessels supplying blood and oxygen to heart muscle. Plaque buildup, called atherosclerosis, can narrow these vessels and reduce blood flow. Plaque includes cholesterol, fat, calcium, and other blood substances. Large coronary arteries or smaller heart vessels may be involved.",
        "Coronary artery disease may cause chest pressure or discomfort, breathlessness, or unusual fatigue; some people have no symptoms before a serious event. Assessment considers history, risk factors, examination, blood tests, and heart tests. Persistent chest discomfort or discomfort at rest requires emergency assessment because it can signal a heart attack.",
        ["plaque", "atherosclerosis", "heart muscle", "chest pain", "angina", "cholesterol"],
        "What coronary artery disease means",
        "Symptoms and assessment",
    ),
    "heart-failure": (
        ["heart failure", "congestive heart failure", "CHF"],
        "Heart failure means the heart cannot pump enough oxygen-rich blood for the body's needs. It does not mean the heart has stopped beating. The heart may pump weakly or be too stiff to fill properly. Conditions such as coronary artery disease, high blood pressure, valve disease, or arrhythmias can contribute.",
        "Heart failure symptoms can include breathlessness, fatigue, swelling, and weight gain from fluid buildup. Symptoms vary with the side of the heart affected and the severity. Assessment includes history, examination, and heart or blood tests; a BNP blood test may be used. Ongoing assessment guides care because the condition can worsen over time.",
        ["pumping", "oxygen", "fluid", "swelling", "edema", "oedema", "BNP", "fatigue"],
        "What heart failure means",
        "Symptoms and assessment",
    ),
    "arrhythmia": (
        ["arrhythmia", "irregular heartbeat", "tachycardia", "bradycardia"],
        "An arrhythmia is a problem with heart rate or rhythm related to the electrical signals controlling the heartbeat. A fast rate is called tachycardia and a slow rate bradycardia. Some rhythm changes are harmless, while others can impair pumping and become serious.",
        "Arrhythmias may cause no noticeable symptoms or may cause fluttering, pounding, dizziness, fainting, breathlessness, or chest discomfort. An electrocardiogram records the heart's electrical activity and is commonly used in assessment. Clinicians also consider history, examination, blood tests, and other heart tests. Chest pain or shortness of breath can require emergency evaluation.",
        ["rhythm", "electrical", "palpitations", "pulse", "ECG", "EKG", "fainting"],
        "What an arrhythmia means",
        "Symptoms and assessment",
    ),
    "stroke": (
        [
            "stroke",
            "cerebrovascular accident",
            "CVA",
            "ischemic stroke",
            "ischaemic stroke",
            "hemorrhagic stroke",
            "haemorrhagic stroke",
        ],
        "A stroke interrupts blood supply to part of the brain, depriving cells of oxygen and nutrients. An ischemic stroke results from a blocked blood vessel; a hemorrhagic stroke results from bleeding. Brain damage can develop rapidly. A transient ischemic attack produces temporary blockage and signals increased future stroke risk.",
        "Sudden one-sided weakness or numbness, speech difficulty, vision changes, loss of balance, or a severe unexplained headache can be stroke warning signs. Suspected stroke needs immediate emergency care. Assessment includes neurological examination and tests such as brain CT or MRI; heart tests may help identify related heart problems or clots.",
        ["brain", "blood flow", "weakness", "speech", "vision", "emergency", "CT", "MRI", "TIA"],
        "What stroke means",
        "Warning signs and assessment",
    ),
    "diabetes": (
        [
            "diabetes",
            "diabetes mellitus",
            "type 1 diabetes",
            "type 2 diabetes",
            "blood sugar",
            "blood glucose",
        ],
        "Diabetes is a condition in which blood glucose stays too high. Insulin normally helps glucose enter cells for energy. In type 1 diabetes, the immune system damages insulin-producing cells. In type 2 diabetes, cells respond poorly to insulin and insulin production may be insufficient. Gestational diabetes develops during pregnancy.",
        "Diabetes symptoms may include thirst, frequent urination, fatigue, blurred vision, or unexplained weight loss. Type 2 symptoms can develop slowly and be barely noticeable; gestational diabetes often has no symptoms. A clinician uses blood glucose tests to diagnose diabetes. Symptoms and diabetes type influence which tests and further assessment are appropriate.",
        ["glucose", "insulin", "pancreas", "thirst", "urination", "blood test", "pregnancy"],
        "What diabetes means",
        "Symptoms and assessment",
    ),
    "hypothyroidism": (
        ["hypothyroidism", "underactive thyroid", "Hashimoto disease", "Hashimoto's disease"],
        "Hypothyroidism occurs when the thyroid makes too little thyroid hormone for the body's needs. Many body functions then slow down. Hashimoto's disease, an autoimmune disorder, is a common cause. Other causes include thyroid inflammation, thyroid surgery or radiation, certain medicines, and some iodine or pituitary problems.",
        "Hypothyroidism can cause fatigue, weight gain, cold intolerance, constipation, dry skin, or a slower heart rate. Symptoms differ and can develop so slowly that they go unnoticed. Assessment combines medical history, examination, and thyroid blood tests such as TSH and thyroid hormones; other tests may be appropriate in some cases.",
        ["thyroid", "hormone", "TSH", "T4", "fatigue", "cold", "constipation"],
        "What hypothyroidism means",
        "Symptoms and assessment",
    ),
    "hyperthyroidism": (
        ["hyperthyroidism", "overactive thyroid", "Graves disease", "Graves' disease"],
        "Hyperthyroidism means the thyroid makes more thyroid hormone than the body needs. Graves' disease is the most common cause. Other causes include overactive thyroid nodules, thyroid inflammation releasing stored hormones, and excess iodine or thyroid medicine. Untreated disease can affect the heart, bones, muscles, or reproductive health.",
        "Hyperthyroidism may cause heat intolerance, weight loss, tremor, trouble sleeping, weakness, and a rapid or irregular heartbeat. Older adults may instead show less typical changes such as reduced appetite or withdrawal. Assessment includes history, examination, and thyroid blood tests; imaging or iodine-uptake tests may help clarify the cause.",
        ["thyroid", "hormone", "TSH", "T3", "T4", "tremor", "heat", "weight loss"],
        "What hyperthyroidism means",
        "Symptoms and assessment",
    ),
    "chronic-kidney-disease": (
        ["chronic kidney disease", "CKD", "kidney disease", "renal disease", "kidney function"],
        "Chronic kidney disease involves kidney damage that reduces normal blood filtering. Waste and extra fluid may accumulate, and other health problems can follow. Diabetes and high blood pressure are the most common causes. The kidneys also help balance body chemicals, control blood pressure, and produce hormones.",
        "Chronic kidney disease can progress for years with few or no symptoms. Blood and urine testing are needed to identify it. Care can slow progression but does not cure established disease, and some people develop kidney failure. Kidney function and urine findings need clinical interpretation together with the person's overall health.",
        ["kidneys", "filter", "waste", "urine", "blood test", "diabetes", "hypertension"],
        "What chronic kidney disease means",
        "Detection and limitations",
    ),
    "kidney-stones": (
        ["kidney stones", "renal stones", "nephrolithiasis"],
        "Kidney stones are solid pieces of material formed from substances in urine. Stones vary in size. Many pass through the urinary tract, but a stone can become stuck, block urine flow, and cause severe pain. A stone that does not pass may need a procedure or other treatment.",
        "Kidney stones may be associated with persistent back or side pain, blood in urine, vomiting, cloudy urine, or burning urination. Fever and chills are also signs needing medical assessment. Clinicians use urine tests, blood tests, and imaging to establish the diagnosis; these symptoms alone do not identify a stone.",
        ["urinary tract", "pain", "blood in urine", "imaging", "obstruction", "urine"],
        "What kidney stones mean",
        "Symptoms and assessment",
    ),
    "urinary-tract-infection": (
        ["urinary tract infection", "urinary tract infections", "UTI", "urine infection"],
        "The urinary system removes waste and extra water through the kidneys, ureters, bladder, and urethra. Urinary tract infections can occur in people of any age or sex. Risk is higher with diabetes, a urinary drainage catheter, or spinal cord injury; women are affected more often than men.",
        "A urinary tract infection may cause burning urination, frequent urges to urinate, lower abdominal pressure, or cloudy, reddish, or unpleasant-smelling urine. Fever or pain in the back or side may also occur. A clinician can use urine testing to assess suspected infection. Symptoms alone do not determine the diagnosis or appropriate treatment.",
        ["urine", "burning", "bladder", "kidney", "catheter", "urination", "urine test"],
        "What a urinary tract infection means",
        "Symptoms and assessment",
    ),
    "gerd": (
        [
            "GERD",
            "gastroesophageal reflux disease",
            "gastro-oesophageal reflux disease",
            "acid reflux",
            "heartburn",
        ],
        "Reflux happens when stomach contents move backward into the esophagus because the muscle at its lower end does not close properly. GERD is persistent reflux that causes troublesome symptoms or damages the esophageal lining. Occasional reflux is common. Obesity, pregnancy, smoking, or a hiatal hernia can increase risk.",
        "GERD can cause heartburn, a sour or food taste, cough, hoarseness, or swallowing difficulty; heartburn may be absent. Assessment starts with symptoms and history and may involve endoscopy or acid-monitoring tests. Chest pain with breathlessness or pain in the jaw or arm requires urgent medical evaluation because a heart problem is possible.",
        ["esophagus", "oesophagus", "reflux", "acid", "swallowing", "endoscopy", "pH"],
        "What GERD means",
        "Symptoms and assessment",
    ),
    "irritable-bowel-syndrome": (
        ["irritable bowel syndrome", "IBS"],
        "Irritable bowel syndrome affects the large intestine and causes abdominal cramps, bloating, and changes in bowel habits. Some people have constipation, some diarrhea, and others alternate between them. IBS can be uncomfortable but does not itself damage the intestines. Its exact cause is unknown.",
        "There is no single specific test for irritable bowel syndrome. A clinician may use blood or stool tests and, when appropriate, bowel imaging or endoscopy to look for other conditions. The pattern of symptoms and assessment for alternative causes matter; abdominal discomfort or a bowel change alone does not establish IBS.",
        ["colon", "cramps", "bloating", "constipation", "diarrhea", "diarrhoea", "stool"],
        "What IBS means",
        "Assessment and limitations",
    ),
    "constipation": (
        ["constipation", "hard stool", "infrequent bowel movements"],
        "Constipation can mean fewer than three bowel movements in a week, with stool that is hard, dry, or painful to pass. It is common and often short-lived. Having a bowel movement every day is not necessary for everyone; a change from the person's usual bowel habits is more useful context.",
        "Food fiber, fluids, physical activity, and making time for bowel movements can influence constipation. Medicines may contribute, so a clinician can review them when bowel habits change. The MedlinePlus summary advises using laxatives only with a healthcare provider's guidance. An educational description does not determine the cause of a particular episode.",
        ["bowel", "stool", "fiber", "fibre", "fluids", "medicines", "laxative"],
        "What constipation means",
        "Contributing factors and review",
    ),
    "diarrhea": (
        ["diarrhea", "diarrhoea", "loose stools", "watery stool"],
        "Diarrhea means loose, watery stools occurring repeatedly. Acute diarrhea lasts a short time; chronic diarrhea lasts at least four weeks and may recur. Causes include infections, contaminated food or water, medicines, food intolerance, digestive diseases, and irritable bowel syndrome. Sometimes no cause is identified.",
        "Diarrhea may occur with cramps, urgency, or fever. It can cause dehydration, especially in children, older adults, or people with weakened immunity. Blood or pus in stool, black tarry stool, severe pain, or signs of dehydration need medical assessment. The cause and duration guide any testing; the stool pattern alone does not identify a disease.",
        ["stool", "dehydration", "infection", "cramps", "food intolerance", "duration"],
        "What diarrhea means",
        "Associated symptoms and limitations",
    ),
    "gastroenteritis": (
        ["gastroenteritis", "viral gastroenteritis", "stomach flu"],
        "Gastroenteritis is inflammation of the stomach and intestinal lining. Viruses are a common cause, including norovirus and rotavirus, but bacteria, parasites, chemicals, or reactions to food or medicines can also cause it. The nickname 'stomach flu' is misleading: viral gastroenteritis is not caused by influenza viruses.",
        "Gastroenteritis typically causes diarrhea, vomiting, nausea, or abdominal cramps and sometimes fever. Dehydration or severe symptoms can occur, particularly in infants, older adults, or people with weakened immunity. Assessment includes symptoms, medical history, and examination, with stool testing in some cases. Persistent vomiting, blood in stool, or dehydration warrants medical assessment.",
        ["stomach", "intestine", "norovirus", "rotavirus", "vomiting", "dehydration", "diarrhoea"],
        "What gastroenteritis means",
        "Symptoms and assessment",
    ),
    "gallstones": (
        ["gallstones", "cholelithiasis", "gallbladder stones"],
        "Gallstones form when substances in bile harden. The gallbladder stores bile, which the liver makes to help digest fat. A stone can block a bile duct and cause a gallstone attack. Gallstones may also be discovered during imaging performed for another reason, without causing symptoms.",
        "A gallstone attack may cause abdominal or back pain, nausea, or vomiting, often after eating. Gallstones without symptoms usually do not need treatment. The significance of an imaging finding depends on whether it explains symptoms or affects bile flow; an educational definition alone does not select a treatment.",
        ["bile", "gallbladder", "duct", "abdominal pain", "imaging", "nausea"],
        "What gallstones mean",
        "Symptoms and incidental findings",
    ),
    "pancreatitis": (
        ["pancreatitis", "acute pancreatitis", "chronic pancreatitis"],
        "Pancreatitis is inflammation of the pancreas, a gland that produces digestive juices and the hormones insulin and glucagon. It occurs when digestive enzymes start damaging the pancreas itself. Acute pancreatitis begins suddenly; chronic pancreatitis causes lasting damage and tends to worsen. Both forms can have serious complications.",
        "Acute pancreatitis often results from gallstones and may cause severe upper abdominal pain, nausea, and vomiting. Heavy alcohol use is a common cause of chronic pancreatitis; inherited disorders, certain medicines, and other conditions can contribute. Chronic disease may cause weight loss or oily stools. These descriptions do not establish the cause in an individual.",
        ["pancreas", "enzymes", "abdominal pain", "gallstones", "alcohol", "oily stools"],
        "What pancreatitis means",
        "Causes and symptoms",
    ),
    "hepatitis": (
        ["hepatitis", "liver inflammation", "viral hepatitis", "jaundice"],
        "Hepatitis is inflammation of the liver that can impair its function. It may be short-term or persistent. Causes include hepatitis viruses, heavy alcohol use, some toxic substances or medicines, and autoimmune disease. Different viral types spread in different ways, so the name 'hepatitis' alone does not identify a route of transmission.",
        "Hepatitis may produce fatigue, appetite loss, nausea, abdominal pain, dark urine, pale stool, or yellowing of the eyes and skin. Some people have no symptoms, especially early in chronic disease. Assessment includes history, examination, and blood tests; imaging or liver biopsy may sometimes be needed. Persistent hepatitis can lead to liver scarring or other complications.",
        ["liver", "inflammation", "virus", "blood tests", "dark urine", "yellow skin", "cirrhosis"],
        "What hepatitis means",
        "Symptoms and assessment",
    ),
    "migraine": (
        ["migraine", "migraines", "migraine aura"],
        "Migraine is a recurring headache disorder that can cause moderate or severe throbbing pain, often on one side of the head. Nausea and sensitivity to light or sound may occur. Some attacks include an aura, such as visual changes, before or during the headache; not everyone experiences every phase.",
        "Migraine triggers differ between people and may include stress, sleep changes, hormonal changes, missed meals, or overuse of headache medicines. Diagnosis uses the symptom history and physical and neurological examination. Blood tests or brain imaging may be used to rule out other causes. A headache or visual symptom alone does not prove migraine.",
        ["headache", "throbbing", "aura", "nausea", "light", "sound", "triggers"],
        "What migraine means",
        "Triggers and assessment",
    ),
    "epilepsy": (
        ["epilepsy", "recurring seizures", "seizure disorder"],
        "Epilepsy is a brain disorder involving recurring seizures. Seizures arise from abnormal signaling by groups of nerve cells. They can change sensation, emotion, behavior, movement, or consciousness; they do not always look alike. Possible causes include illness, brain injury, or abnormal brain development, but the cause is often unknown.",
        "Clinicians use brain scans and other tests to assess epilepsy. Treatment can control seizures for many people, although epilepsy has no cure. Surgery or implanted devices may be considered when medicines do not work well. This overview explains the condition and does not classify an individual's event or select a medicine.",
        ["brain", "neurons", "seizures", "signals", "consciousness", "brain scan"],
        "What epilepsy means",
        "Assessment and care context",
    ),
    "peripheral-neuropathy": (
        ["peripheral neuropathy", "peripheral nerve disorders", "nerve damage"],
        "Peripheral nerves connect the brain and spinal cord with muscles, skin, and organs. Peripheral nerve disorders occur when these nerves are damaged and no longer transmit messages normally. Causes include diabetes, injury, infections, autoimmune conditions, vitamin imbalance, certain medicines, or inherited disorders. In some cases the cause is unknown.",
        "Peripheral neuropathy symptoms depend on the nerves affected. Sensory damage may cause pain, numbness, or tingling; motor damage may cause weakness; autonomic damage can affect digestion, sweating, or other involuntary functions. Assessment uses history and examination and may include blood tests, nerve and muscle electrical tests, imaging, or tissue sampling.",
        ["nerves", "tingling", "numbness", "weakness", "sensory", "motor", "autonomic", "diabetes"],
        "What peripheral neuropathy means",
        "Symptoms and assessment",
    ),
    "eczema": (
        ["eczema", "dermatitis", "atopic dermatitis"],
        "Eczema describes several forms of skin inflammation, often causing dry, itchy skin and rashes. Atopic dermatitis is the most common type. It often starts in infancy or childhood, although adults can have it. Eczema is not contagious, and genetic and environmental factors probably both contribute.",
        "Eczema can improve or worsen over time and may persist. Scratching can increase irritation and swelling. Some people also have asthma or hay fever. Irritating soaps, fabrics, stress, or allergens can worsen some forms. The term describes a group of conditions; it does not identify the cause of every itchy rash.",
        ["skin", "itch", "rash", "dryness", "inflammation", "allergens", "irritation"],
        "What eczema means",
        "Patterns and contributing factors",
    ),
    "cellulitis": (
        ["cellulitis", "skin infection"],
        "Cellulitis is an infection of the skin and deeper underlying tissue. Group A streptococcal bacteria are a common cause. Bacteria can enter after a skin injury, burn, cut, or wound. Cellulitis may cause painful, red, tender skin that can blister or form scabs.",
        "Cellulitis may also cause fever, chills, or swollen lymph nodes. A clinician may use a skin sample, culture, or blood test to help identify the responsible bacteria. Treatment depends on severity. A description of a red or swollen area does not by itself establish that cellulitis is the cause.",
        ["skin", "bacteria", "streptococcal", "wound", "tenderness", "fever", "culture"],
        "What cellulitis means",
        "Symptoms and assessment",
    ),
    "shingles": (
        ["shingles", "herpes zoster", "varicella-zoster virus"],
        "Shingles occurs when the varicella-zoster virus, which remains in the body after chickenpox, becomes active again. It typically causes pain or tingling followed by a blistering rash on one side of the body or face. Risk increases with age or a weakened immune system.",
        "A clinician usually assesses shingles through history and examination of the rash; a sample can sometimes be tested. Pain may persist after the rash, and eye involvement can threaten vision. Contact with fluid from shingles blisters can transmit chickenpox to a susceptible person, rather than directly transmitting shingles. Prompt assessment helps guide care.",
        ["virus", "chickenpox", "rash", "blisters", "pain", "postherpetic neuralgia", "eye"],
        "What shingles means",
        "Assessment and complications",
    ),
    "anemia": (
        [
            "anemia",
            "anaemia",
            "iron deficiency anemia",
            "iron deficiency anaemia",
            "low haemoglobin",
            "low hemoglobin",
        ],
        "Anemia reduces the blood's ability to carry oxygen to the body. It can result from blood loss, too little red blood cell production, or excessive red blood cell destruction. Iron deficiency is a common cause, but inherited disorders, vitamin deficiencies, bleeding, and other diseases can also contribute.",
        "Anemia can cause tiredness, feeling cold, dizziness, headache, or shortness of breath. A clinician assesses it using physical examination and blood tests. The cause matters because care depends on the type of anemia. Symptoms or the word 'anemia' alone do not show that iron deficiency is responsible.",
        ["red blood cells", "oxygen", "iron", "hemoglobin", "haemoglobin", "blood loss", "fatigue"],
        "What anemia means",
        "Symptoms and assessment",
    ),
    "cbc": (
        ["complete blood count", "CBC", "full blood count", "FBC", "blood cell count"],
        "A complete blood count measures blood cells and related features. Red cells transport oxygen, white cells help defend against disease, and platelets support clotting. A CBC commonly includes hemoglobin, hematocrit, and mean corpuscular volume, the average red-cell size. A CBC with differential separately counts the major white-cell types.",
        "A CBC can support assessment or monitoring of anemia, infection, and other blood or immune conditions. An abnormal result does not automatically mean a disease requiring treatment. Hydration, medicines, diet, activity, and menstruation can affect results. Clinicians interpret the pattern with symptoms, history, and sometimes additional tests.",
        [
            "RBC",
            "WBC",
            "platelets",
            "hemoglobin",
            "haemoglobin",
            "hematocrit",
            "haematocrit",
            "MCV",
            "differential",
        ],
        "What a CBC measures",
        "Uses and interpretation limits",
    ),
    "hemoglobin": (
        [
            "hemoglobin",
            "haemoglobin",
            "hemoglobin test",
            "haemoglobin test",
            "Hb",
            "Hgb",
            "low haemoglobin",
            "low hemoglobin",
        ],
        "A hemoglobin test measures the oxygen-carrying protein in red blood cells. It is commonly included in a CBC and can help assess anemia. This test differs from hemoglobin A1C, which estimates average blood glucose. A hemoglobin measurement describes the level, but does not by itself identify why it is abnormal.",
        "Hemoglobin reference ranges vary between laboratories and with personal factors such as age and sex. A low result can have many causes, including blood loss, iron or vitamin deficiency, or other disease. Hydration, smoking, altitude, medicines, and activity can also affect results. Interpretation includes symptoms, history, and other blood tests.",
        ["oxygen", "red cells", "anemia", "anaemia", "reference range", "blood loss", "CBC"],
        "What hemoglobin testing means",
        "Interpretation and limitations",
    ),
    "hba1c": (
        [
            "HbA1c",
            "HbA1C",
            "A1C",
            "glycated hemoglobin",
            "glycated haemoglobin",
            "glycosylated hemoglobin",
        ],
        "Hemoglobin A1C is a blood test reflecting average blood glucose over roughly the previous two to three months. It measures how much hemoglobin has glucose attached. It may be used to identify prediabetes or type 2 diabetes and to monitor diabetes, rather than measuring blood sugar at a single moment.",
        "A1C interpretation depends on health and the reason for testing. A higher result may need confirmation with another diabetes test. Conditions affecting red blood cells, including anemia or some blood disorders, can reduce its accuracy; kidney failure and liver disease can also affect it. A1C is not used to diagnose gestational diabetes.",
        [
            "glucose",
            "blood sugar",
            "average",
            "diabetes",
            "prediabetes",
            "red blood cells",
            "accuracy",
        ],
        "What A1C measures",
        "Uses and interpretation limits",
    ),
    "creatinine": (
        ["creatinine", "serum creatinine", "blood creatinine", "renal function", "kidney function"],
        "Creatinine is a waste product from normal muscle activity and tissue breakdown. Kidneys normally remove it from blood into urine. Creatinine testing in blood or urine can help assess kidney health and monitor kidney disease or medicine effects. Blood creatinine is often used to calculate an estimated filtration rate, called eGFR.",
        "Creatinine depends partly on muscle mass, diet, age, and activity, so an isolated value has limits. A normal blood result can occur in early kidney disease. A single high result cannot diagnose a specific condition and can also reflect dehydration, muscle injury, or intense exercise. Repeat or additional kidney tests may be needed.",
        ["kidney", "muscle", "waste", "urine", "eGFR", "dehydration", "blood test"],
        "What creatinine measures",
        "Interpretation and limitations",
    ),
    "bun": (
        ["BUN", "blood urea nitrogen", "urea nitrogen", "serum BUN"],
        "A blood urea nitrogen test measures a waste substance formed when the body breaks down protein. The kidneys normally remove it in urine. BUN is often included in a metabolic panel and can help assess or monitor kidney disease, including problems that have not yet caused symptoms.",
        "An elevated BUN can occur with reduced kidney function, but dehydration, some medicines, burns, or a high-protein diet can also raise it. Low results can occur with poor protein intake, malnutrition, or liver disease. BUN is only one measure of kidney function; creatinine or filtration-rate testing may add information.",
        ["kidney", "protein", "waste", "metabolic panel", "creatinine", "dehydration", "urea"],
        "What BUN measures",
        "Interpretation and limitations",
    ),
    "egfr": (
        [
            "eGFR",
            "estimated glomerular filtration rate",
            "GFR",
            "kidney filtration",
            "renal function",
        ],
        "eGFR estimates how effectively the kidneys filter blood. It is calculated from blood measurements such as creatinine or cystatin C together with relevant personal information. A measured GFR uses an injected filtration marker and repeated samples; it is more complicated and is reserved for selected circumstances.",
        "eGFR helps assess, monitor, or screen for kidney disease, but it is an estimate and can be unreliable in some settings, including altered muscle mass or severe malnutrition. A result needs interpretation with age, body size, other health conditions, and additional kidney tests. An eGFR alone does not provide a complete kidney assessment.",
        ["kidneys", "filtration", "creatinine", "cystatin C", "estimate", "glomeruli", "mGFR"],
        "What eGFR means",
        "Uses and interpretation limits",
    ),
    "electrolytes": (
        [
            "electrolyte panel",
            "electrolytes",
            "serum electrolytes",
            "lytes",
            "sodium",
            "potassium",
            "chloride",
            "bicarbonate",
        ],
        "Electrolytes are charged minerals in body fluids that help regulate water balance, acid-base balance, nerve and muscle activity, and heart rhythm. Blood testing checks levels of electrolytes such as sodium, potassium, chloride, and bicarbonate. Electrolytes may be tested together or individually depending on the clinical question.",
        "An electrolyte result above or below its reference range has several possible explanations. Fluid intake, vomiting, diarrhea, kidney disease, and some medicines can affect levels. The pattern and symptoms matter. Terms such as hyponatremia and hyperkalemia mean low sodium and high potassium respectively; they name an imbalance rather than its cause.",
        [
            "Na",
            "K",
            "Cl",
            "CO2",
            "fluid",
            "pH",
            "hyponatremia",
            "hyponatraemia",
            "hyperkalemia",
            "hyperkalaemia",
        ],
        "What electrolyte testing means",
        "Interpretation and terminology",
    ),
    "liver-function": (
        ["liver function tests", "liver panel", "LFT", "LFTs", "hepatic function panel"],
        "A liver panel measures several blood substances related to liver function or injury. Common measurements include albumin, bilirubin, and enzymes such as ALT, AST, and ALP. Some results describe how the liver is working and others suggest injury. Testing can help investigate symptoms, monitor liver disease, or check medicine effects.",
        "A liver panel alone usually cannot diagnose a specific liver disease. Clinicians compare the pattern of results with symptoms, history, medicines, and other tests. An abnormal value can also have another explanation; for example, ALP can rise with bone disease. Some changes are temporary, and repeat testing may help clarify them.",
        ["ALT", "AST", "ALP", "albumin", "bilirubin", "enzymes", "liver", "GGT"],
        "What a liver panel measures",
        "Interpretation and limitations",
    ),
    "ecg": (
        ["electrocardiogram", "ECG", "EKG", "heart tracing"],
        "An electrocardiogram records electrical signals from the heart through sensors placed on the skin. It describes heart rate, rhythm, and the timing of signals through the heart. The ECG does not send electricity into the body. The recording contains components known as the P wave, QRS complex, and T wave.",
        "An ECG can support investigation or monitoring of heart conditions, but its results require history and sometimes other tests for diagnosis. A short recording can miss an intermittent problem. A clinician may then use longer recording with a portable monitor. These terms explain the test and do not interpret a particular tracing.",
        ["heart", "electrical", "rhythm", "P wave", "QRS", "T wave", "Holter", "monitor"],
        "What an ECG records",
        "Uses and interpretation limits",
    ),
    "chest-xray": (
        ["chest X-ray", "chest xray", "CXR", "chest radiograph", "chest radiography"],
        "A chest X-ray is a quick, painless imaging test showing structures in and around the chest. Clinicians use it to help assess conditions such as pneumonia, heart failure, emphysema, lung scarring, or tuberculosis. It can also monitor treatment or look for complications after some procedures.",
        "Chest X-ray images are taken while the person remains still, standing, sitting, or lying down. The radiation amount is very small, but possible pregnancy should be discussed with the healthcare team. The test helps clinicians assess or monitor disease; this explanation does not interpret an individual image or report.",
        ["imaging", "lungs", "chest", "radiation", "pneumonia", "heart failure", "fibrosis"],
        "What a chest X-ray means",
        "Test context and limitations",
    ),
    "atelectasis": (
        ["atelectasis", "collapsed air sacs", "lung collapse"],
        "Atelectasis describes a lung, or part of a lung, that does not expand fully. Its air sacs collapse, reducing the amount of oxygen that reaches the blood. The term describes what happens to lung expansion; it does not by itself identify an underlying cause.",
        "NHLBI includes atelectasis among possible complications during ventilator support. This source provides a basic definition and care context, rather than a method for deciding whether an individual chest image shows atelectasis. The significance of the term in a person's record requires the healthcare team's assessment.",
        ["lung", "air sacs", "expansion", "oxygen", "ventilator", "collapse"],
        "What atelectasis means",
        "Source context and limitations",
    ),
    "pleural-effusion": (
        ["pleural effusion", "fluid around the lung", "pleural fluid"],
        "Pleural effusion is excess fluid in the pleural space around the lung. Exudative effusions relate to inflammation, tumors, infection, or lung injury. Transudative effusions arise from blood-vessel pressure, often associated with heart, kidney, or liver failure. The cause determines the type.",
        "Pleural fluid terminology describes different contents: empyema involves infection or pus, hemothorax involves blood, and chylothorax involves chyle, a substance formed in the small intestine. These names do not alone establish the underlying disease. A report mentioning pleural effusion needs interpretation in the person's clinical context.",
        [
            "pleura",
            "fluid",
            "exudative",
            "transudative",
            "empyema",
            "hemothorax",
            "haemothorax",
            "chylothorax",
        ],
        "What pleural effusion means",
        "Fluid terms and limitations",
    ),
    "pulmonary-edema": (
        ["pulmonary edema", "pulmonary oedema", "fluid in lung air sacs"],
        "Pulmonary edema means fluid has collected in air sacs inside the lungs, which normally contain air. The term identifies the location of the fluid. It does not, by itself, establish what caused the fluid to accumulate in an individual.",
        "NHLBI describes pulmonary edema among possible problems associated with ventilator support. This educational entry provides that limited source context and a definition. It does not establish a diagnosis from an uploaded image or determine how fluid in an individual's lungs should be managed.",
        ["lungs", "air sacs", "fluid", "edema", "oedema", "ventilator"],
        "What pulmonary edema means",
        "Source context and limitations",
    ),
    "pneumothorax": (
        ["pneumothorax", "air in pleural space", "collapsed lung"],
        "Pneumothorax is air or gas in the pleural space. Pressure from this buildup can collapse part or all of a lung. A spontaneous pneumothorax may occur without an obvious cause or with an underlying lung condition. A traumatic pneumothorax follows a chest injury.",
        "Tension pneumothorax can impair heart and lung function, interfere with blood flow through the chest, and lower blood pressure. These terms describe potentially serious conditions; they do not establish an individual's diagnosis from a report word or image. Clinical assessment determines the significance and urgency.",
        [
            "pleura",
            "air",
            "gas",
            "collapse",
            "spontaneous",
            "traumatic",
            "tension",
            "blood pressure",
        ],
        "What pneumothorax means",
        "Tension pneumothorax and limitations",
    ),
    "prescription-label": (
        [
            "prescription label",
            "prescribing information",
            "medication guide",
            "contraindication",
            "indication",
            "adverse reaction",
        ],
        "FDA prescription labeling includes information for healthcare professionals, packaging labels, and some patient materials. 'Indications and Usage' describes approved uses. 'Dosage and Administration' describes dose, frequency, route, and administration instructions. 'Dosage Forms and Strengths' identifies available forms and strengths. These section names are explanations of terminology, not a dosing recommendation.",
        "A contraindication is a situation in which a medicine must not be used because risk clearly outweighs possible benefit. Warnings, adverse reactions, and drug interactions describe important risks. Medication Guides, Patient Package Inserts, and Instructions for Use are patient materials, but not every medicine has all of them. Medicine questions require the prescribing clinician or pharmacist.",
        [
            "FDA",
            "label",
            "dose",
            "frequency",
            "route",
            "strength",
            "warnings",
            "interactions",
            "medicine",
        ],
        "Prescription labeling terms",
        "Risk terms and patient information",
    ),
}


def acquire(source: tuple[str, str, str]) -> dict:
    topic_id, title, suffix = source
    url = suffix if suffix.startswith("https://") else f"https://medlineplus.gov/{suffix}"
    try:
        response = httpx.get(url, follow_redirects=True, timeout=45)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        if url.startswith("https://www.nhlbi.nih.gov/"):
            main = soup.select_one("main article") or soup.select_one("main")
        elif url.startswith("https://www.fda.gov/"):
            main = soup.select_one(".field--name-body") or soup.select_one("main")
        elif suffix.startswith("lab-tests/"):
            main = soup.select_one("#mplus-content")
        else:
            main = soup.select_one("#topic-summary")
        if main is None:
            raise ValueError("No recognized content container")
        for unwanted in main.select("script, style, nav"):
            unwanted.decompose()
        body = main.get_text("\n", strip=True)
        if len(body) < 150:
            raise ValueError("Content too short to verify")
        snapshot = RAW / f"{topic_id}.html"
        snapshot.write_bytes(response.content)
        (RAW / f"{topic_id}.txt").write_text(body, encoding="utf-8")
        full_text = soup.get_text(" ", strip=True)
        source_date = None
        match = re.search(r"Last updated(?: on)?\s+([A-Za-z]+ \d{1,2}, \d{4})", full_text)
        if match:
            source_date = datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()
        match = re.search(r"Review Date\s+(\d{1,2}/\d{1,2}/\d{4})", full_text)
        if match:
            source_date = datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
        return {
            "id": topic_id,
            "title": title,
            "url": str(response.url),
            "raw_snapshot_path": snapshot.relative_to(ROOT).as_posix(),
            "raw_sha256": hashlib.sha256(response.content).hexdigest(),
            "status": "retrieved",
            "source_date": source_date,
        }
    except Exception as exc:
        return {"id": topic_id, "url": url, "status": "excluded", "reason": str(exc)}


def acquire_all() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(acquire, SOURCES))
    (RAW / "manifest.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    for result in results:
        print(result["id"], result["status"], result.get("reason", ""))


def build() -> None:
    results = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    documents = []
    for result in results:
        if result["status"] != "retrieved":
            continue
        topic_id = result["id"]
        aliases, first, second, keywords, first_title, second_title = NOTES[topic_id]
        url = result["url"]
        if url.startswith("https://medlineplus.gov/"):
            publisher = "MedlinePlus, National Library of Medicine (NIH)"
            terms = (
                "Source: MedlinePlus, National Library of Medicine. Original short English "
                "paraphrases of NLM health-topic summaries or medical-test information, "
                "which NLM identifies as public-domain content at "
                "https://medlineplus.gov/about/using/usingcontent/. Third-party encyclopedia "
                "articles, drug monographs, and illustrations are excluded from these notes."
            )
        elif url.startswith("https://www.nhlbi.nih.gov/"):
            publisher = "National Heart, Lung, and Blood Institute (NIH)"
            terms = (
                "Original short English paraphrases of NIH-authored federal educational "
                "text. Source: National Heart, Lung, and Blood Institute. Third-party "
                "artwork and media are not reproduced. No claim of clinical review."
            )
        else:
            publisher = "U.S. Food and Drug Administration"
            terms = (
                "Original short English paraphrases of FDA-authored educational information "
                "about prescription labeling. Source: U.S. Food and Drug Administration. "
                "No medicine-specific label, dosing table, or third-party media reproduced."
            )
        document_id = f"v2-topic-{topic_id}"
        document = {
            "id": document_id,
            "title": result["title"],
            "url": url,
            "publisher": publisher,
            "jurisdiction": "US",
            "source_date": result["source_date"],
            "retrieved_date": DATE,
            "version": f"retrieved-{DATE}-sha256-{result['raw_sha256'][:16]}",
            "terms": terms,
            "raw_snapshot_path": result["raw_snapshot_path"],
            "raw_sha256": result["raw_sha256"],
            "clinical_review": False,
            "sections": [
                {
                    "id": f"{document_id}-meaning",
                    "title": first_title,
                    "text": first,
                    "topics": aliases,
                    "keywords": keywords + ["definition", "meaning", "overview"],
                },
                {
                    "id": f"{document_id}-context",
                    "title": second_title,
                    "text": second,
                    "topics": aliases,
                    "keywords": keywords + ["assessment", "limitations", "interpretation"],
                },
            ],
        }
        assert all(len(section["text"].split()) <= 180 for section in document["sections"])
        snapshot = ROOT / document["raw_snapshot_path"]
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == document["raw_sha256"]
        documents.append(document)
    assert len({document["id"] for document in documents}) == len(documents)
    assert 40 <= len(documents) <= 50
    words_by_url: dict[str, int] = {}
    for document in documents:
        words_by_url.setdefault(document["url"], 0)
        words_by_url[document["url"]] += sum(
            len(section["text"].split()) for section in document["sections"]
        )
    assert all(count <= 200 for count in words_by_url.values()), words_by_url
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"documents": documents}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(documents)} documents, {sum(len(d['sections']) for d in documents)} sections"
    )
    print(
        f"Maximum section length: {max(len(s['text'].split()) for d in documents for s in d['sections'])} words"
    )
    print(f"Maximum source-derived text per URL: {max(words_by_url.values())} words")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build notes from existing verified snapshots; no network",
    )
    args = parser.parse_args()
    if args.build:
        build()
    else:
        acquire_all()
