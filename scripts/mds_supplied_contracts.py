"""Independent scope contracts for the user's two MDS question attachments.

This is evaluation-only metadata. Never import it into answer generation or
retrieval. Facets describe requested content, not medically adjudicated answers.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANK = ROOT / "configs/benchmarks/mds-supplied/v2-2026-10-12"
VERSION = "mds-supplied-v2-2026-10-12"
SPECIALTIES = (
    "endodontics", "orthodontics", "oral_surgery", "prosthodontics",
    "periodontology", "pediatric_dentistry", "oral_medicine", "oral_pathology",
    "public_health",
)
REGISTERED = {
    "oral_epithelium", "keratinized_epithelium", "nonkeratinized_epithelium",
    "sulcular_epithelium", "junctional_epithelium", "apoptosis", "necrosis",
    "tooth_development", "oral_leukoplakia", "oral_epithelial_dysplasia",
    "odontogenic_keratocyst", "dentigerous_cyst", "radicular_cyst",
    "ameloblastoma", "salivary_glands", "pleomorphic_adenoma", "dental_caries",
    "oral_biofilm", "immunohistochemistry", "biostatistics",
}

# Reviewed request-scope descriptors. Each row specifies subjects independently
# of question_plan.py; comma-separated facets apply to each listed subject.
ORAL_SCOPE = """
oral_epithelium|definition,layers,functions|explanation
keratinized_epithelium nonkeratinized_epithelium|structure,anatomical_examples|comparison
oral_epithelium sulcular_epithelium junctional_epithelium|structure,functions,histopathology|comparison
apoptosis|definition,molecular_features,histopathology|explanation
apoptosis necrosis|causes,cellular_features,inflammation|comparison
tooth_development|stages,epithelial_mesenchymal_interactions|mechanism
oral_leukoplakia|definition,clinical_features,histopathology,relationship_to_dysplasia|explanation
oral_squamous_cell_carcinoma|histopathology,invasion|explanation
oral_lichen_planus oral_lichenoid_lesions|clinical_features,histopathology|comparison
oral_submucous_fibrosis|etiopathogenesis,histopathology,clinical_significance|explanation
odontogenic_keratocyst dentigerous_cyst|clinical_features,radiographic_features,histopathology|comparison
ameloblastoma|histopathological_variants,diagnostic_importance|explanation
pemphigus_vulgaris mucous_membrane_pemphigoid|histopathology,direct_immunofluorescence|comparison
dental_caries|mechanism,microbial_biofilms,ecological_plaque_hypothesis|mechanism
oral_epithelial_dysplasia|cellular_features,architectural_features,grading_limitations,malignant_transformation|critical_explanation
oral_squamous_cell_carcinoma|molecular_features,TP53,EGFR,cell_cycle_dysregulation|mechanism
pleomorphic_adenoma mucoepidermoid_carcinoma|histopathology,investigations|comparison
oral_lichen_planus|immunopathogenesis,T_lymphocytes,basal_keratinocyte_damage|mechanism
immunohistochemistry oral_potentially_malignant_disorders oral_squamous_cell_carcinoma|diagnostic_role,diagnostic_limitations|critical_explanation
chronic_periapical_inflammation periapical_granuloma radicular_cyst|mechanism,histopathology|multipart
white_patch|differential_diagnosis,histopathological_possibilities,investigations|educational_case
persistent_tongue_ulcer|differential_diagnosis,histopathology|educational_case
pericoronal_radiolucency|differential_diagnosis,histopathology,confirmation|educational_case
pemphigus_vulgaris|leading_diagnosis,mechanism,confirmatory_investigation|educational_case
palatal_swelling|differential_diagnosis,tissue_origins,histopathology|educational_case
oral_epithelial_dysplasia|question,rubric,followup|interactive_viva
oral_squamous_cell_carcinoma verrucous_carcinoma|clinical_features,histopathology,invasion_patterns,biological_behavior|comparison_table
oral_submucous_fibrosis oral_lichen_planus|mechanism,histopathology,comparison|multipart
apoptosis|molecular_features,intrinsic_pathway,extrinsic_pathway|progressive_explanation
HPV oral_cavity_squamous_cell_carcinoma oropharyngeal_cancer|evidence,anatomical_distinction,verifiable_sources,evidence_limitations|evidence_review
"""

SPECIALTY_SCOPE = {
    "endodontics": """
dentin_pulp_complex|structure,functions,pulp_response_to_caries|explanation
irreversible_pulpitis|pathophysiology,bacterial_toxins,inflammatory_mediators,intrapulpal_pressure,sensory_nerve_activation|mechanism
reversible_pulpitis symptomatic_irreversible_pulpitis pulp_necrosis symptomatic_apical_periodontitis|symptoms,clinical_examination,sensibility_testing,radiographic_features|comparison
tooth_pain|differential_diagnosis,investigations,test_interpretation,treatment_options|educational_case
root_canal_treatment|access_cavity,working_length,chemomechanical_preparation,irrigation,intracanal_medication,obturation,coronal_sealing,scientific_rationale,limitations|long_answer
sodium_hypochlorite_irrigation|question,rubric,advanced_followup|interactive_viva
""",
    "orthodontics": """
malocclusion|definition,Angle_classification,skeletal_limitations,transverse_limitations|explanation
orthodontic_tooth_movement|mechanism,periodontal_ligament,bone_remodeling,pressure_tension_theory,inflammatory_mediators|mechanism
fixed_orthodontic_appliances clear_aligners|biomechanics,tooth_movement_control,indications,limitations,compliance,effectiveness_evidence|comparison
skeletal_Class_II|diagnostic_records,growth_assessment,cephalometric_considerations,treatment_approaches,growth_modification_limitations|educational_case
orthodontic_anchorage|conventional_anchorage,skeletal_anchorage,temporary_anchorage_devices,biomechanics,unwanted_tooth_movement|long_answer
cephalometric_analysis|SNA,SNB,ANB,rubric,ANB_limitations|interactive_viva
""",
    "oral_surgery": """
mandibular_fractures|anatomical_classification,clinical_features,radiographic_features|explanation
mandibular_fracture_healing|stages,healing_factors,nonunion,infection|mechanism
Le_Fort_I Le_Fort_II Le_Fort_III|anatomical_fracture_patterns,clinical_features,imaging_findings|comparison
bilateral_mandibular_fractures|initial_trauma_priorities,clinical_examination,imaging_selection,definitive_management_principles|educational_case
impacted_mandibular_third_molar_removal|surgical_principles,preoperative_assessment,inferior_alveolar_nerve_risk,infection,alveolar_osteitis,postoperative_followup|long_answer
mandibular_angle_fracture|question,diagnostic_reasoning,rubric,increasing_complexity|interactive_viva
""",
    "prosthodontics": """
vertical_dimension_of_occlusion vertical_dimension_at_rest|definition,clinical_significance,complete_denture_fabrication|explanation
osseointegration|cellular_features,tissue_features,primary_stability,secondary_stability,implant_success_factors|mechanism
metal_ceramic_crowns monolithic_zirconia_crowns lithium_disilicate_restorations|material_properties,indications,preparation_requirements,aesthetics,failure_modes|comparison
edentulous_mandibular_ridge_resorption|examination,anatomical_limitations,treatment_alternatives,prosthodontic_planning|educational_case
complete_denture_impressions|anatomical_landmarks,stress_bearing_areas,selective_pressure,border_molding,impression_materials,impression_errors|long_answer
centric_relation maximum_intercuspation complete_denture_occlusal_schemes|question,rubric|interactive_viva
""",
    "periodontology": """
gingiva periodontal_ligament cementum alveolar_bone|anatomy,histopathology|explanation
periodontitis|mechanism,dysbiotic_biofilms,host_immune_response,cytokines,osteoclast_activation,alveolar_bone_loss|mechanism
gingivitis periodontitis|clinical_features,attachment_loss,pocketing,radiographic_features,reversibility|comparison
periodontal_stage_and_grade|stage,grade,additional_information|educational_case
guided_tissue_regeneration|biological_principles,barrier_membranes,indications,limitations,outcome_factors|long_answer
periodontal_classification|case_question,rubric,stage,grade,followup|interactive_viva
""",
    "pediatric_dentistry": """
primary_tooth_eruption_and_exfoliation|chronology,eruption_timing_disturbances,clinical_consequences|explanation
early_childhood_caries|mechanism,cariogenic_biofilms,fermentable_carbohydrates,feeding_patterns,salivary_factors,social_determinants|mechanism
primary_tooth_pulpotomy primary_tooth_pulpectomy|indications,contraindications,procedural_principles,materials,success_criteria|comparison
primary_molar_caries|diagnostic_assessment,pulp_status,treatment_selection_factors|educational_case
pediatric_behavior_guidance|basic_behavioral_approaches,protective_stabilization,sedation,general_anesthesia,consent,indications,safety_requirements,ethics|long_answer
molar_incisor_hypomineralization|clinical_identification,differential_diagnosis,hypersensitivity,management_principles,rubric|interactive_viva
""",
    "oral_medicine": """
radiolucent_lesions radiopaque_lesions|definition,location,borders,internal_structure,surrounding_tissue_effects|explanation
oral_candidiasis|mechanism,predisposing_factors,clinical_features,investigations|mechanism
intraoral_periapical_radiography panoramic_radiography CBCT conventional_CT|imaging_principles,indications,limitations,radiation_considerations,diagnostic_value|comparison
white_patch|differential_diagnosis,risk_factors,examination,biopsy_indications,clinical_appearance_limitations|educational_case
osteoradionecrosis|mechanism,risk_factors,clinical_features,imaging_findings,differential_diagnosis,prevention,management_principles|long_answer
multilocular_mandibular_radiolucency|written_imaging_case,differential_diagnosis,justification,investigations|interactive_viva
""",
    "oral_pathology": """
oral_epithelial_dysplasia|definition,architectural_features,cytological_features,histopathological_significance|explanation
oral_squamous_cell_carcinoma|molecular_features,DNA_damage,TP53,cell_cycle_dysregulation,invasion,tumour_microenvironment|mechanism
odontogenic_keratocyst dentigerous_cyst|clinical_features,radiographic_features,epithelial_lining,histopathology,recurrence|comparison
oral_submucous_fibrosis|likely_pathological_process,differential_diagnosis,etiopathogenesis,histopathology,malignant_transformation_risk|educational_case
ameloblastoma|classification,histopathology,variants,differential_diagnosis,molecular_features,pathological_significance|long_answer
pemphigus_vulgaris mucous_membrane_pemphigoid|cleavage_level,acantholysis,histopathology,direct_immunofluorescence,rubric|interactive_viva
""",
    "public_health": """
DMFT_index|definition,components,applications,limitations,primary_dentition_indices|explanation
social_determinants_of_oral_health|prevalence,dental_care_access,oral_health_inequalities|mechanism
incidence prevalence relative_risk odds_ratio sensitivity specificity|definition,appropriate_uses|comparison
school_oral_health_program|needs_assessment,target_population,interventions,implementation,outcome_measures|public_health_case
community_water_fluoridation|effectiveness_evidence,dental_fluorosis,surveillance,cost_effectiveness,equity,implementation_considerations|long_answer
case_control_study|study_design,association_measures,confounding,limitations,rubric|interactive_viva
""",
}

CROSS_SCOPE = """
endodontic_disease periodontal_disease combined_endodontic_periodontal_lesions|mechanism,investigations,differential_diagnosis|multipart
ameloblastoma odontogenic_keratocyst dentigerous_cyst|clinical_features,radiographic_features,histopathology,biological_behavior,diagnostic_overlaps|comparison_table
tooth_supported_fixed_partial_denture implant_supported_crown|prosthodontic_considerations,periodontal_considerations,radiographic_considerations,surgical_considerations,additional_information|educational_case_comparison
randomized_controlled_trial endodontic_irrigation_protocols|randomization,allocation_concealment,blinding,primary_outcomes,effect_sizes,confidence_intervals,bias,clinical_significance,limitations|research_appraisal
osseointegration|stages,cellular_features,question,rubric,missed_content|progressive_viva
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scope_rows(text):
    return [line.split("|") for line in text.strip().splitlines()]


def make_contract(identifier, question, specification, specialty, source_line, line_no, document):
    topics, facets, shape = specification
    topic_ids = [t if t in REGISTERED else "local:" + t.casefold() for t in topics.split()]
    return {
        "case_id": identifier, "question": question, "question_sha256": digest(question.encode()),
        "specialties": [specialty] if isinstance(specialty, str) else specialty,
        "topic_names": [t.replace("_", " ") for t in topics.split()], "topic_ids": topic_ids,
        "expected_facets": [{"topic_id": t, "facet": f} for t in topic_ids for f in facets.split(",")],
        "task_shape": shape, "audience": "research" if shape in {"research_appraisal", "evidence_review"} else "study",
        "split": "user_supplied_development", "independent_unseen": False,
        "clinical_reference_answer": None, "contract_role": "requested_scope_only",
        "origin": {"document": document, "line_number": line_no, "source_line": source_line,
                   "source_line_sha256": digest(source_line.encode())},
        "turns": [{"question": question, "question_sha256": digest(question.encode()), "role": "user", "origin": "supplied"}],
    }


def supplied_cases(oral_text, all_text):
    cases = []
    oral_specs = scope_rows(ORAL_SCOPE)
    for line_no, line in enumerate(oral_text.splitlines(), 1):
        match = re.match(r"^(\d+)\. (.+)$", line)
        if not match:
            continue
        number, question = int(match[1]), match[2]
        if number >= 26:
            quoted = re.findall(r'"([^"]+)"', question)
            question = quoted[0]
        case = make_contract(f"oral-{number:02}", question, oral_specs[number - 1], "oral_pathology", line, line_no, "oral-pathology.txt")
        if number == 29:
            case["turns"].append({"question": quoted[1], "question_sha256": digest(quoted[1].encode()), "role": "user", "origin": "supplied"})
            case["turn_requirements"] = ["simple_molecular_explanation", "postgraduate_intrinsic_and_extrinsic_without_repetition"]
        if number in range(21, 26):
            case["educational_context_origin"] = "attachment_level_4_introduction"
            case["context_instruction"] = "These are fictional postgraduate educational cases; discuss differentials and investigations without unwarranted certainty."
        cases.append(case)
    specialty = None
    cross = None
    lines = all_text.splitlines()
    for line_no, line in enumerate(lines, 1):
        header = re.match(r"^(\d+)\. (?!Basic:|Mechanism:|Comparison:|Clinical case:|Public-health case:|Long answer:|Viva:)(.+)$", line)
        if header:
            number = int(header[1])
            specialty = SPECIALTIES[number - 1] if number <= 9 else None
        prompt = re.match(r"^(\d+)\. (Basic|Mechanism|Comparison|Clinical case|Public-health case|Long answer|Viva): (.+)$", line)
        if prompt and specialty:
            number = int(prompt[1])
            cases.append(make_contract(f"{specialty}-{number:02}", prompt[3], scope_rows(SPECIALTY_SCOPE[specialty])[number - 1], specialty, line, line_no, "all-specialties.txt"))
        cross_header = re.match(r"^Test ([A-E]) (?:—|-) ", line)
        if cross_header:
            cross = cross_header[1]
            if cross != "E":
                next_no = next(i for i in range(line_no, len(lines)) if lines[i].strip())
                topics = {"A": ["endodontics", "periodontology"], "B": ["oral_pathology", "oral_medicine"],
                          "C": ["prosthodontics", "periodontology", "oral_surgery", "oral_medicine"], "D": ["endodontics", "public_health"]}[cross]
                case = make_contract(f"cross-{cross}", lines[next_no], scope_rows(CROSS_SCOPE)[ord(cross) - ord("A")], topics, lines[next_no], next_no + 1, "all-specialties.txt")
                if cross == "A":
                    case["context_instruction"] = "This is a fictional postgraduate educational case."
                    case["educational_context_origin"] = "attachment_cross_specialty_test_context"
                cases.append(case)
        if cross == "E" and re.fullmatch(r"Turn [1-4]", line):
            next_no = next(i for i in range(line_no, len(lines)) if lines[i].strip())
            question = lines[next_no]
            if line == "Turn 1":
                case = make_contract("cross-E", question, scope_rows(CROSS_SCOPE)[4], "prosthodontics", line, line_no, "all-specialties.txt")
                case["turns"] = []
                case["turn_requirements"] = ["stages", "cellular_depth_without_repetition", "one_viva_question_then_wait", "grading_requires_a_learner_answer"]
                case["conditional_turn_note"] = "Supplied turn 4 is a grading instruction, not a learner answer. Never score it as submitted subject knowledge."
                cases.append(case)
            case["turns"].append({"question": question, "question_sha256": digest(question.encode()), "role": "user", "origin": "supplied", "source_line_number": next_no + 1})
    if len(cases) != 89 or len({c["case_id"] for c in cases}) != 89:
        raise ValueError("Expected exactly 30 oral + 54 specialty + 5 cross-specialty cases")
    for case in cases:
        partition_contract(case)
    return cases


def partition_contract(case):
    """Keep interaction obligations out of claim-evidence coverage denominators.

    Comparisons share requested axes. Ordinary multipart operations preserve the
    subject of each part; a disease cannot inherit an unrelated entity's facet.
    """
    interaction_facets = {
        "question", "case_question", "rubric", "followup", "advanced_followup",
        "increasing_complexity", "written_imaging_case", "missed_content",
    }
    case["interaction_requirements"] = [f for f in case["expected_facets"] if f["facet"] in interaction_facets]
    content = [f for f in case["expected_facets"] if f["facet"] not in interaction_facets]
    identifier = case["case_id"]
    if identifier == "oral-20":
        content = [{"topic_id": "local:chronic_periapical_inflammation", "facet": "mechanism"},
                   {"topic_id": "local:periapical_granuloma", "facet": "histopathology"},
                   {"topic_id": "radicular_cyst", "facet": "histopathology"}]
    if identifier == "oral-28":
        content = [{"topic_id": "local:oral_submucous_fibrosis", "facet": "mechanism"},
                   {"topic_id": "local:oral_submucous_fibrosis", "facet": "histopathology"},
                   {"topic_id": "local:oral_lichen_planus", "facet": "histopathology"}]
        case["separate_parts"] = ["fibrosis_pathogenesis", "fibrosis_versus_lichen_planus_comparison", "both_histopathologies"]
    if identifier == "cross-D":
        content = [f for f in content if f["topic_id"] == "local:randomized_controlled_trial"]
        case["secondary_topic_role"] = "Endodontic irrigation protocols specify the appraisal domain; do not invent clinical claims about their efficacy."
    case["expected_content_facets"] = content
    case["turn_content_contracts"] = [content for _ in case["turns"]]
    if identifier == "oral-29":
        case["turn_content_contracts"] = [
            [{"topic_id": "apoptosis", "facet": "molecular_features"}],
            [{"topic_id": "apoptosis", "facet": "intrinsic_pathway"}, {"topic_id": "apoptosis", "facet": "extrinsic_pathway"}],
        ]
    if identifier == "cross-E":
        case["turn_content_contracts"] = [
            [{"topic_id": "local:osseointegration", "facet": "stages"}],
            [{"topic_id": "local:osseointegration", "facet": "cellular_features"}], [], [],
        ]
    case["grading_note"] = "Interaction-only and conditional turns have no claim-facet denominator. Review topic retention, one question, waiting, provisional rubric and follow-up separately."


VARIATIONS = {
    "endodontics-02": "In postgraduate terms, why does pulp inflammation become irreversible? Connect sensory nerve activation and pressure with bacterial toxins and inflammatory mediators.",
    "endodontics-03": "Use symptoms, sensibility tests, examination and imaging to distinguish symptomatic apical periodontitis, pulp necrosis, reversible pulpitis and symptomatic irreversible pulpitis.",
    "orthodontics-02": "How do inflammatory mediators and remodeling of bone translate periodontal ligament loading into orthodontic tooth movement? Include pressure and tension.",
    "orthodontics-03": "Contrast clear aligners with fixed appliances by compliance, effectiveness evidence, indications, limitations, biomechanics and control of movement.",
    "oral_surgery-02": "For mandibular fracture repair, explain healing stages and the factors behind nonunion, infection and successful healing.",
    "oral_surgery-03": "Distinguish Le Fort III, I and II using imaging, clinical presentation and the anatomical lines of fracture.",
    "prosthodontics-02": "At cellular and tissue scales, how does an implant integrate with bone? Contrast secondary and primary stability and discuss success factors.",
    "prosthodontics-03": "Contrast lithium disilicate, metal-ceramic and monolithic zirconia restorations by aesthetics, preparation, failure modes, material properties and indications.",
    "periodontology-02": "Trace periodontal bone loss from dysbiotic biofilm through immune cytokines and osteoclast activation.",
    "periodontology-03": "How do gingivitis and periodontitis differ in attachment loss, pocketing, radiographs, clinical findings and reversibility?",
    "pediatric_dentistry-02": "Explain ECC as a process involving social determinants, saliva, feeding, fermentable carbohydrate and cariogenic biofilms.",
    "pediatric_dentistry-03": "For primary teeth, contrast pulpectomy with pulpotomy by success criteria, materials, procedure, contraindications and indications.",
    "oral_medicine-02": "Discuss candidiasis in the mouth: why it develops, predisposition, clinical forms and diagnostic tests.",
    "oral_medicine-03": "Contrast CT, CBCT, panoramic and intraoral periapical imaging by diagnostic value, dose considerations, limitations, indications and principles.",
    "oral_pathology-02": "Explain oral SCC carcinogenesis through the tumour microenvironment, epithelial invasion, TP53, cell-cycle disruption and DNA damage.",
    "oral_pathology-03": "Contrast a dentigerous cyst with an OKC by recurrence, lining histology, radiographic appearance and clinical presentation.",
    "public_health-02": "Explain how social determinants affect inequalities, access to dental care and oral disease prevalence.",
    "public_health-03": "Explain appropriate dental research uses of specificity and sensitivity, odds ratio and relative risk, and prevalence and incidence.",
}


def variation_cases(cases):
    by_id = {c["case_id"]: c for c in cases}
    result = []
    for identifier, question in VARIATIONS.items():
        case = json.loads(json.dumps(by_id[identifier]))
        case.update(case_id="variation-" + identifier, question=question, question_sha256=digest(question.encode()),
                    origin={"kind": "developer_authored_paraphrase_subject_reordering", "parent_case_id": identifier},
                    split="related_development_variation", independent_unseen=False,
                    turns=[{"question": question, "question_sha256": digest(question.encode()), "role": "user", "origin": "developer_authored"}])
        result.append(case)
    return result


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def lock_bank(folder, oral_input, all_input):
    folder = Path(folder)
    if folder.exists():
        raise FileExistsError("Locked bank already exists; choose a fresh version directory")
    raw_inputs = {"oral-pathology.txt": Path(oral_input).read_bytes(), "all-specialties.txt": Path(all_input).read_bytes()}
    cases = supplied_cases(*(raw_inputs[n].decode("utf-8-sig") for n in ("oral-pathology.txt", "all-specialties.txt")))
    folder.mkdir(parents=True)
    blobs = {"inputs/" + n: b for n, b in raw_inputs.items()}
    for name, rows in [("supplied.jsonl", cases), ("variations.jsonl", variation_cases(cases))]:
        blobs[name] = ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n").encode()
    for name, blob in blobs.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    manifest = {"schema_version": 1, "version": VERSION, "files": {n: digest(b) for n, b in blobs.items()},
                "case_count": len(cases), "supplied_turn_count": sum(len(c["turns"]) for c in cases),
                "variation_count": len(VARIATIONS), "task_distribution": dict(Counter(c["task_shape"] for c in cases)),
                "input_hash_method": "SHA256 of exact attachment bytes; no newline or Unicode normalization",
                "question_extraction": "Strip list/task labels and outer quotation marks; preserve message spelling and punctuation. Keep full original line alongside the question.",
                "lock_rule": "Never rewrite locked bytes; new contracts or prompts require a new version directory",
                "evaluation_role": "user_supplied_and_related_development_cases", "independent_unseen": False,
                "clinical_reference_answers": "absent; independent qualified adjudication required",
                "clinical_accuracy": None, "clinical_completeness": None,
                "prohibited_inference": "Parser matches, alias mentions, valid citation coordinates and task shapes cannot establish clinical correctness or completeness."}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (folder / "manifest.sha256").write_text(digest((folder / "manifest.json").read_bytes()) + "\n", encoding="ascii")
    return manifest


def verify_bank(folder=DEFAULT_BANK):
    folder = Path(folder)
    raw = (folder / "manifest.json").read_bytes()
    if digest(raw) != (folder / "manifest.sha256").read_text().strip():
        raise ValueError("Locked manifest bytes changed")
    manifest = json.loads(raw)
    for name, expected in manifest["files"].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or digest(path.read_bytes()) != expected:
            raise ValueError("Locked bank bytes changed: " + name)
    cases = read_rows(folder / "supplied.jsonl")
    inputs = {n: (folder / "inputs" / n).read_text(encoding="utf-8-sig").splitlines() for n in ("oral-pathology.txt", "all-specialties.txt")}
    for case in cases:
        origin = case["origin"]
        line = inputs[origin["document"]][origin["line_number"] - 1]
        if line != origin["source_line"] or digest(line.encode()) != origin["source_line_sha256"]:
            raise ValueError("Question origin does not match attachment: " + case["case_id"])
        for turn in case["turns"]:
            if digest(turn["question"].encode()) != turn["question_sha256"]:
                raise ValueError("Question hash mismatch: " + case["case_id"])
    return manifest
