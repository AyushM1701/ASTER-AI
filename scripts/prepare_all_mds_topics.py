"""Write an explicit editorial search map, distinct from a full competency inventory."""

import json
from pathlib import Path

BRANCHES = {
    "orthodontics": ("Orthodontics and Dentofacial Orthopaedics", [
        "Craniofacial growth", "Orthodontic tooth movement", "Orthodontic biomechanics",
        "Cephalometric analysis", "Malocclusion", "Class II malocclusion", "Class III malocclusion",
        "Functional appliances", "Orthodontic anchorage", "Clear aligners", "Maxillary expansion",
        "Orthognathic surgery", "Orthodontic retention", "Impacted canines"]),
    "endodontics": ("Conservative Dentistry and Endodontics", [
        "Dental caries", "Dentin bonding", "Dental composite", "Dental pulp", "Pulpitis",
        "Root canal anatomy", "Endodontic diagnosis", "Root canal irrigation", "Root canal instrumentation",
        "Root canal obturation", "Endodontic retreatment", "Regenerative endodontics", "Vital pulp therapy", "Cracked tooth"]),
    "oral_surgery": ("Oral and Maxillofacial Surgery", [
        "Third molar surgery", "Odontogenic infections", "Mandibular fractures", "Midface fractures",
        "Orthognathic surgery", "Cleft lip and palate", "Maxillofacial reconstruction",
        "Medication related osteonecrosis", "Oral cancer surgery", "Salivary gland surgery",
        "Temporomandibular joint surgery", "Dental implant complications", "Dental local anesthesia", "Oroantral communication"]),
    "prosthodontics": ("Prosthodontics and Crown & Bridge", [
        "Complete dentures", "Removable partial dentures", "Fixed dental prostheses", "Dental ceramics",
        "Dental impressions", "Digital dentistry", "Implant supported prostheses", "Dental occlusion",
        "Temporomandibular disorders", "Maxillofacial prostheses", "Overdentures", "Dental abutments",
        "Geriatric dentistry", "Prosthetic complications"]),
    "periodontology": ("Periodontology", [
        "Periodontal anatomy", "Periodontal pathogenesis", "Periodontitis classification", "Periodontal diagnosis",
        "Periodontal microbiome", "Non surgical periodontal therapy", "Periodontal surgery", "Periodontal regeneration",
        "Gingival recession", "Peri implantitis", "Periodontitis and diabetes", "Periodontal maintenance",
        "Mucogingival surgery", "Periodontal biomarkers"]),
    "oral_medicine": ("Oral Medicine and Radiology", [
        "Oral potentially malignant disorders", "Oral lichen planus", "Oral leukoplakia", "Oral submucous fibrosis",
        "Oral ulcers", "Oral candidiasis", "Salivary gland disorders", "Orofacial pain", "Burning mouth syndrome",
        "Cone beam computed tomography", "Dental radiation protection", "Jaw lesions imaging",
        "Oral manifestations of systemic disease", "Oral cancer screening"]),
    "paediatric_dentistry": ("Paediatric and Preventive Dentistry", [
        "Early childhood caries", "Dental behavior management", "Pediatric pulp therapy", "Immature permanent teeth",
        "Dental trauma in children", "Fluoride caries prevention", "Fissure sealants", "Space maintainers",
        "Molar incisor hypomineralization", "Dental development", "Special needs dentistry", "Silver diamine fluoride",
        "Dental sedation in children", "Dental prevention in children"]),
    "oral_pathology": ("Oral Pathology and Microbiology", [
        "Odontogenic cysts", "Odontogenic tumors", "Oral squamous cell carcinoma", "Salivary gland tumors",
        "Fibro osseous jaw lesions", "Oral epithelial dysplasia", "Oral histopathology", "Oral immunohistochemistry",
        "Oral microbiome", "Oral fungal infections", "Oral viral infections", "Forensic odontology",
        "Tooth development", "Oral molecular pathology"]),
    "public_health_dentistry": ("Public Health Dentistry", [
        "Dental epidemiology", "Oral health inequalities", "Community oral health promotion", "Water fluoridation",
        "Public oral health India", "Oral health surveys", "Dental health economics", "Evidence based dentistry",
        "Dental systematic review methodology", "Dental biostatistics", "Tobacco cessation dentistry",
        "Oral health policy", "Dental infection prevention", "Oral health quality of life"]),
}


def prepare():
    root = Path(__file__).resolve().parents[1]
    spec = {"version": "aster-all-mds-research-v1-2026-10-10",
            "scope": "Editorial specialty topic map, not a complete competency inventory or proof of mastery. Applied basic sciences preserved in existing library.",
            "curriculum_reference": "https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf",
            "curriculum_status": "2017 syllabus reference; later amendments and university requirements need reconciliation.",
            "specialties": [], "topics": []}
    for code, (name, titles) in BRANCHES.items():
        group = {"id": code, "title": name, "topics": []}
        for i, title in enumerate(titles, 1):
            # AND phrases tolerate spelling variants and differences in word order.
            words = [w for w in title.lower().split() if w not in {"and", "in", "of", "related", "non"}]
            synonyms = {"pediatric": '(pediatric OR paediatric)', "tumors": '(tumors OR tumours)',
                        "anesthesia": '(anesthesia OR anaesthesia)', "hypomineralization": '(hypomineralization OR hypomineralisation)',
                        "behavior": '(behavior OR behaviour)', "dentin": '(dentin OR dentine)',
                        "implantitis": '(implantitis OR periimplantitis OR "peri-implantitis")'}
            query = " AND ".join(synonyms.get(w, w) for w in words if w != "peri")
            row = {"id": f"ALL-MDS-{code.upper()}-{i:02}", "title": title, "query": query,
                   "area": code, "specialty": name, "coverage_claim": "topic_association_only"}
            group["topics"].append(row)
            spec["topics"].append(row)
        spec["specialties"].append(group)
    spec["topic_count"] = len(spec["topics"])
    (root / "configs/all_mds_topics.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f'{len(spec["specialties"])} specialties, {spec["topic_count"]} editorial topics')


if __name__ == "__main__":
    prepare()
