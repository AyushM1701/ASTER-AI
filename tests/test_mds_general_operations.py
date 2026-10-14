"""General task grammar across specialties; no biomedical answer fixtures."""

import pytest

from backend.app.services.question_plan import plan_question


def test_differentiate_retains_four_explicit_entities_and_requested_axes():
    plan = plan_question(
        "Differentiate reversible pulpitis, symptomatic irreversible pulpitis, pulp necrosis "
        "and symptomatic apical periodontitis based on symptoms, clinical examination, "
        "sensibility testing and radiographic findings.", "study"
    )
    assert plan.task == "compare"
    assert plan.canonical_topics == [
        "local:reversible_pulpitis", "local:symptomatic_irreversible_pulpitis",
        "local:pulp_necrosis", "local:symptomatic_apical_periodontitis",
    ]
    assert {"clinical_features", "clinical_tests", "radiographic_features"} <= set(plan.comparison_axes)
    assert all(f.topic_id != "necrosis" for f in plan.facets)


def test_three_entity_comparison_keeps_unknown_entity_with_known_entities():
    plan = plan_question(
        "Compare ameloblastoma, odontogenic keratocyst, and dentigerous cyst in terms of "
        "clinical features, radiographic appearance, histopathological findings, and biological behavior.", "study"
    )
    assert plan.canonical_topics == ["ameloblastoma", "odontogenic_keratocyst", "dentigerous_cyst"]
    assert "biological_behavior" in plan.comparison_axes
    assert len(plan.facets) == 12


def test_mixed_comparison_keeps_mechanism_on_its_own_subject():
    plan = plan_question(
        "Explain the pathogenesis of oral submucous fibrosis, compare it with oral lichen planus, "
        "and describe the histopathological findings of both conditions.", "study"
    )
    assert plan.canonical_topics == ["local:oral_submucous_fibrosis", "local:oral_lichen_planus"]
    assert ("local:oral_submucous_fibrosis", "mechanism") in {(f.topic_id, f.facet) for f in plan.facets}
    assert ("local:oral_lichen_planus", "mechanism") not in {(f.topic_id, f.facet) for f in plan.facets}
    assert {(f.topic_id, f.facet) for f in plan.facets if f.facet == "histopathology"} == {
        ("local:oral_submucous_fibrosis", "histopathology"),
        ("local:oral_lichen_planus", "histopathology"),
    }


@pytest.mark.parametrize("question,identity", [
    ("Act as an MDS Endodontics examiner. Ask me one challenging question about sodium hypochlorite irrigation, wait for my answer, evaluate it against an explicit rubric, and then ask a follow-up.", "local:sodium_hypochlorite_irrigation"),
    ("Act as an MDS Oral Pathology examiner. Ask me one challenging viva question on oral epithelial dysplasia, wait for my answer, evaluate it and then ask a follow-up question.", "oral_epithelial_dysplasia"),
    ("Conduct an MDS Orthodontics viva on cephalometric analysis. Ask me to interpret SNA, SNB and ANB angles, wait for my response and evaluate it using a rubric.", "local:cephalometric_analysis"),
])
def test_examiner_instructions_yield_practice_with_only_explicit_topic(question, identity):
    plan = plan_question(question, "study")
    assert plan.task == "viva"
    assert plan.intent == "practice"
    assert plan.canonical_topics == [identity]
    assert plan.topic == identity.removeprefix("local:").replace("_", " ")


def test_fictional_patient_preserves_case_without_inferring_diagnosis():
    plan = plan_question(
        "A fictional 32-year-old patient reports spontaneous lingering molar pain after cold stimulation. "
        "Discuss the differential diagnosis, relevant tests, interpretation of results and treatment options in an educational context.", "study"
    )
    assert plan.is_fictional_case
    assert plan.task == "fictional_case"
    assert plan.original_question.startswith("A fictional 32-year-old patient")
    assert plan.patient_context["age_statement"] == "32-year-old"
    assert not plan.individualized_advice_requested
    assert {"differential_diagnosis", "clinical_tests", "management"} <= {f.facet for f in plan.facets}
    assert not any("pulpitis" in t or "necrosis" in t for t in plan.canonical_topics)
    assert "histopathology" not in {f.facet for f in plan.facets}


@pytest.mark.parametrize("question", [
    "A fictional patient: I have tooth pain. Which antibiotic should I take?",
    "Fictional case: my child has tooth pain. What dose should I give?",
    "A fictional patient represents my real patient with tooth pain. Diagnose me.",
])
def test_fictional_label_does_not_bypass_personal_context(question):
    plan = plan_question(question, "study")
    assert not plan.is_fictional_case
    assert plan.individualized_advice_requested


def test_explicit_new_facets_are_operations_not_disease_evidence():
    plan = plan_question(
        "Discuss oral squamous cell carcinoma: diagnostic limitations, invasion patterns, biological behavior, and management principles.", "study"
    )
    assert plan.canonical_topics == ["local:oral_squamous_cell_carcinoma"]
    assert {"diagnostic_limitations", "invasion", "biological_behavior", "management"} <= {f.facet for f in plan.facets}
    materials = plan_question("Compare pulpotomy and pulpectomy in primary teeth: materials and clinical tests.", "study")
    assert materials.canonical_topics == ["local:pulpotomy", "local:pulpectomy"]
    assert {"materials", "clinical_tests"} <= set(materials.comparison_axes)


@pytest.mark.parametrize("question,identity", [
    ("Explain the pathophysiology of irreversible pulpitis, including inflammatory mediators.", "local:irreversible_pulpitis"),
    ("Explain the structure and functions of the dentin–pulp complex.", "local:dentin_pulp_complex"),
    ("Explain the principles of orthodontic anchorage, including skeletal anchorage.", "local:orthodontic_anchorage"),
    ("Explain the biological basis of orthodontic tooth movement, including pressure–tension theory.", "local:orthodontic_tooth_movement"),
    ("Explain the molecular pathogenesis of oral squamous cell carcinoma, including TP53 alterations.", "local:oral_squamous_cell_carcinoma"),
    ("Describe the normal anatomy and histology of the periodontium, including gingiva and alveolar bone.", "local:periodontium"),
    ("Discuss osteoradionecrosis of the jaws, including pathogenesis and management principles.", "local:osteoradionecrosis_of_the_jaws"),
])
def test_requested_operation_head_and_facet_list_are_not_part_of_entity(question, identity):
    plan = plan_question(question, "study")
    assert plan.canonical_topics == [identity]


def test_explicit_fictional_case_narrative_cannot_become_a_provisional_diagnosis():
    plan = plan_question("A fictional 13-year-old patient presents with an increased overjet and convex facial profile. Discuss diagnostic records and growth assessment.", "study")
    assert plan.canonical_topics == ["local:overjet"]


def test_shared_comparison_name_keeps_each_explicit_fracture_type():
    plan = plan_question("Differentiate Le Fort I, II and III fractures based on anatomical patterns and imaging findings.", "study")
    assert plan.canonical_topics == ["local:le_fort_i_fractures", "local:le_fort_ii_fractures", "local:le_fort_iii_fractures"]


def test_examiner_case_instruction_uses_case_topic_without_inferring_diagnosis():
    plan = plan_question("Act as an MDS Oral and Maxillofacial Surgery examiner. Present a fictional patient with a mandibular angle fracture, ask me one diagnostic question at a time and evaluate my answers.", "study")
    assert plan.task == "viva"
    assert plan.canonical_topics == ["local:mandibular_angle_fracture"]
    assert plan.topic == "mandibular angle fracture"


def test_comparison_axes_are_not_population_scope_but_primary_teeth_are():
    plan = plan_question("Compare fixed orthodontic appliances and clear aligners in terms of biomechanics, control, limitations and compliance.", "study")
    assert all(not f.scope for f in plan.facets)
    primary = plan_question("Compare pulpotomy and pulpectomy in primary teeth, including materials and clinical success criteria.", "study")
    assert all("primary teeth" in f.scope for f in primary.facets)


def test_case_narrative_with_short_first_clause_still_has_case_identity():
    plan = plan_question("A fictional 13-year-old patient presents with overjet. Discuss clinical examination and treatment options.", "study")
    assert plan.canonical_topics == ["local:overjet"]


@pytest.mark.parametrize("question,identities", [
    ("Act as an MDS Prosthodontics examiner. Ask me challenging questions on centric relation, maximum intercuspation and occlusal schemes in complete dentures, one at a time. Assess each answer using a rubric.", ["local:centric_relation", "local:maximum_intercuspation", "local:occlusal_schemes"]),
    ("Conduct an MDS Oral Pathology viva about pemphigus vulgaris and mucous membrane pemphigoid. Ask me about cleavage level and assess my answer.", ["local:pemphigus_vulgaris", "local:mucous_membrane_pemphigoid"]),
    ("Act as an MDS Oral Medicine and Radiology examiner. Present the written radiographic findings of a multilocular radiolucent lesion in the posterior mandible. Ask me to construct a differential diagnosis.", ["local:multilocular_radiolucent_lesion"]),
    ("Act as an MDS Public Health Dentistry examiner. Present a fictional case-control study investigating tobacco use and oral cancer. Ask me to identify the study design and explain limitations.", ["local:case_control_study"]),
])
def test_viva_keeps_explicit_multiple_or_case_targets_instead_of_examiner_text(question, identities):
    plan = plan_question(question, "study")
    assert plan.task == "viva"
    assert plan.canonical_topics == identities


def test_fictional_symptom_case_does_not_enter_patient_information_route():
    plan = plan_question("A fictional patient has tooth pain. Discuss possible causes and diagnostic tests in an educational context.", "study")
    assert plan.is_fictional_case
    assert plan.intent == "concept_explanation"
    assert plan.medical_audience == "student"


@pytest.mark.parametrize("question", [
    "Explain the pathophysiology of irreversible pulpitis.",
    "Explain the biological basis of orthodontic tooth movement.",
])
def test_requested_causal_operation_gets_mechanism_intent(question):
    plan = plan_question(question, "study")
    assert plan.task == "mechanism"
    assert plan.intent == "mechanism"
    assert "mechanism" in {f.facet for f in plan.facets}


@pytest.mark.parametrize("question,identity", [
    ("Explain irreversible pulpitis including its mechanism and clinical features.", "local:irreversible_pulpitis"),
    ("Explain how social determinants of health influence oral disease prevalence and access to dental care.", "local:social_determinants_of_health"),
    ("Design a school oral-health program, including needs assessment, interventions and outcome measures.", "local:school_oral_health_program"),
    ("Critically evaluate community water fluoridation as a public-health intervention, discussing evidence and cost-effectiveness.", "local:community_water_fluoridation"),
    ("Explain osseointegration of dental implants at the cellular and tissue levels.", "local:osseointegration_of_dental_implants"),
    ("Classify mandibular fractures according to anatomical location and describe their clinical features.", "local:mandibular_fractures"),
    ("Explain the chronology of primary tooth eruption and exfoliation and discuss the clinical consequences of disturbances in eruption timing.", "local:primary_tooth_eruption_and_exfoliation"),
])
def test_bounded_educational_subject_grammar_preserves_explicit_topic(question, identity):
    plan = plan_question(question, "study")
    assert plan.canonical_topics == [identity]


def test_pronoun_followup_facets_stay_on_prior_entity():
    plan = plan_question("Explain the pathogenesis of oral candidiasis and discuss its predisposing factors, common clinical presentations and diagnostic investigations.", "study")
    assert plan.canonical_topics == ["local:oral_candidiasis"]
    assert {"mechanism", "clinical_features", "investigations"} <= {f.facet for f in plan.facets}


def test_rationale_for_each_stage_stays_on_procedure():
    plan = plan_question("Discuss the principles of modern root canal treatment, covering access preparation and obturation. Explain the scientific rationale and limitations of each stage.", "study")
    assert plan.canonical_topics == ["local:modern_root_canal_treatment"]


def test_named_classification_does_not_lose_noun_as_a_facet():
    plan = plan_question("Define malocclusion and explain Angle's classification, including its limitations.", "study")
    assert plan.canonical_topics == ["local:malocclusion", "local:angle_s_classification"]


def test_joint_definitions_keep_explicit_entities_and_plural_facet_reference():
    plan = plan_question("Define vertical dimension of occlusion (VDO) and vertical dimension at rest (VDR). Explain their clinical significance in complete denture fabrication.", "study")
    assert plan.canonical_topics == ["local:vertical_dimension_of_occlusion_vdo", "local:vertical_dimension_at_rest_vdr"]
    assert {(f.topic_id, f.facet) for f in plan.facets if f.facet == "clinical_significance"} == {
        ("local:vertical_dimension_of_occlusion_vdo", "clinical_significance"),
        ("local:vertical_dimension_at_rest_vdr", "clinical_significance"),
    }


def test_including_preserves_named_requested_parts_as_facets_of_primary_subject():
    plan = plan_question("Explain the pathogenesis of dental caries, including the role of microbial biofilms and the ecological plaque hypothesis.", "study")
    assert plan.canonical_topics == ["dental_caries"]
    assert {(f.topic_id, f.facet) for f in plan.facets} == {
        ("dental_caries", "mechanism"),
        ("dental_caries", "microbial_biofilms"),
        ("dental_caries", "ecological_plaque_hypothesis"),
    }


@pytest.mark.parametrize("marker", ["including", "emphasizing", "emphasising", "covering"])
def test_explicit_detail_enumerations_preserve_names_and_canonical_facets(marker):
    plan = plan_question(f"Explain the molecular pathogenesis of oral squamous cell carcinoma, {marker} DNA damage, TP53 alterations, cell-cycle dysregulation, histopathology and invasion.", "study")
    assert plan.canonical_topics == ["local:oral_squamous_cell_carcinoma"]
    assert {"dna_damage", "tp53_alterations", "cell_cycle_dysregulation", "histopathology", "invasion"} <= {f.facet for f in plan.facets}
    assert "histopathological_features" not in {f.facet for f in plan.facets}


def test_generic_mechanism_steps_do_not_gain_unrequested_named_details():
    plan = plan_question("Explain the mechanism of apoptosis, including the steps in simple language.", "study")
    assert {f.facet for f in plan.facets} == {"mechanism"}
    assert all(not f.scope for f in plan.facets)


def test_explicit_detail_in_second_clause_does_not_leak_to_first_subject():
    plan = plan_question("Explain apoptosis; explain the pathogenesis of dental caries, including microbial biofilms and the ecological plaque hypothesis.", "study")
    assert {(f.topic_id, f.facet) for f in plan.facets if f.facet == "ecological_plaque_hypothesis"} == {("dental_caries", "ecological_plaque_hypothesis")}


def test_now_explain_keeps_context_topic_without_turning_instruction_into_entity():
    question = "Now explain the intrinsic and extrinsic apoptotic pathways in postgraduate detail without repeating your earlier explanation."
    plan = plan_question(question, "study", context_topic="apoptosis")
    assert plan.original_question == question
    assert plan.canonical_topics == ["apoptosis"]
    assert {"intrinsic_pathway", "extrinsic_pathway"} <= {f.facet for f in plan.facets}


def test_personal_symptoms_do_not_gain_educational_named_detail_contract():
    plan = plan_question("My tooth hurts; explain the pathogenesis including microbial biofilms and the ecological plaque hypothesis.", "study")
    assert plan.intent == "symptom_information"
    assert not plan.facets


@pytest.mark.parametrize("question,identity,scope", [
    ("Explain the stages of osseointegration following implant placement.", "local:osseointegration", "following implant placement"),
    ("Explain the mechanism of dentin bonding before restoration in diabetic adults.", "local:dentin_bonding", "before restoration in diabetic adults"),
    ("Explain oral epithelium structure after chemotherapy in children.", "oral_epithelium", "after chemotherapy in children"),
])
def test_temporal_context_is_separate_from_explicit_topic_and_retained(question, identity, scope):
    plan = plan_question(question, "study")
    assert plan.canonical_topics == [identity]
    assert all(f.scope == scope for f in plan.facets)
    assert all(scope in f.query for f in plan.facets)


@pytest.mark.parametrize("question,identity", [
    ("Define orthodontic tooth movement cellular mechanisms in diabetic adults.", "local:orthodontic_tooth_movement"),
    ("Define oral candidiasis histopathology and diagnostic limitations in children receiving chemotherapy.", "local:oral_candidiasis"),
    ("Define cracked tooth clinical features after biting trauma.", "local:cracked_tooth"),
])
def test_editorial_noun_heads_keep_provisional_identity_with_facet_suffixes(question, identity):
    plan = plan_question(question, "study")
    assert plan.canonical_topics == [identity]
    assert all(f.scope for f in plan.facets)


def test_editorial_substring_cannot_replace_a_longer_explicit_disorder_name():
    plan = plan_question("Define orthodontic tooth movement disorder in adults.", "study")
    assert plan.canonical_topics == ["local:orthodontic_tooth_movement_disorder"]


def test_depth_instruction_is_not_a_provisional_topic():
    question = "Go deeper into the cellular mechanisms without repeating the previous explanation."
    resolved = plan_question(question, "study", context_topic="osseointegration")
    assert resolved.original_question == question
    assert resolved.canonical_topics == ["local:osseointegration"]
    assert {"cellular_features", "mechanism"} <= {f.facet for f in resolved.facets}
    unresolved = plan_question(question, "study")
    assert not unresolved.canonical_topics
    assert unresolved.needs_clarification
