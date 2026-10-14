"""Reproduced question-fit failures; synthetic evidence isolates retrieval logic."""

import pytest

from backend.app.services.teaching import teaching_terms
from tests.test_mbbs_teaching import teaching_release
from tests.test_teaching_audit import store_for


def make_store(tmp_path):
    root, _ = teaching_release(tmp_path)
    return store_for(root)


@pytest.mark.parametrize("question", [
    "Please explain osmosis in simple terms for a patient.",
    "Could you describe osmosis using plain language?",
    "For an MBBS viva, explain: Osmosis. Address the underlying mechanism and relevant terminology.",
    "Give an analytical viva discussion of: Osmosis. Identify common misconceptions, evidence limits and how to distinguish related concepts. State what cannot be established from the available evidence.",
])
def test_presentation_instructions_do_not_replace_the_requested_concept(tmp_path, question):
    store = make_store(tmp_path)
    result = store.answer(question)
    assert result is not None
    assert len(result["claims"]) == 1
    assert result["claims"][0]["text"] == store.records[2].text


def test_independent_concepts_are_both_represented_in_the_answer(tmp_path):
    store = make_store(tmp_path)
    result = store.answer("Explain osmosis and glomerular filtration")
    assert result is not None
    assert {row["section"] for row in result["citations"]} == {"Osmosis", "Filtration"}


def test_unknown_compound_part_is_explicit_in_the_user_visible_response(tmp_path):
    store = make_store(tmp_path)
    result = store.answer("Explain glomerular filtration and blorptosis")
    assert result is not None
    assert result["unsupported_topics"] == ["blorptosis"]
    assert any("blorptosis" in text for text in result["warnings"] + result["limitations"])


def change(store, row, section, text, topics, keywords=()):
    row.section, row.text, row.topics, row.keywords = section, text, topics, list(keywords)
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section + " " + " ".join(keywords))


def test_homonym_cannot_be_matched_by_nonadjacent_tokens(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "ECG / ST depression", "ST depression is an ECG term.", ["ST depression"])
    change(store, store.records[1], "Depression", "St. John's wort has been studied for depression.", ["depression"])
    result = store.answer("Explain ST depression")
    assert result is not None
    assert {row["section"] for row in result["citations"]} == {"ECG / ST depression"}


def test_a_named_context_modifier_is_not_silently_discarded(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Normal distribution", "A normal distribution is a Gaussian distribution.", ["normal distribution"])
    assert store.answer("Explain normal distribution in the liver") is None


def test_broad_topic_keywords_do_not_substitute_for_passage_support(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Water balance", "Some unrelated discussion of water balance.",
           ["glomerular filtration"], ["glomerular", "filtration"])
    assert store.answer("Explain glomerular filtration") is None


def test_direct_concept_phrase_beats_disconnected_mentions(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Cell cycle", "The cell cycle is discussed here.", ["cell cycle"])
    change(store, store.records[1], "Viral life cycle", "A virus infects a cell. Its life cycle is discussed here.", ["cell cycle"])
    result = store.answer("Explain cell cycle")
    assert result is not None
    assert {row["section"] for row in result["citations"]} == {"Cell cycle"}


def test_sibling_topic_does_not_inherit_a_stats_only_source_scope(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Normal distribution", "A normal distribution is a Gaussian distribution.", ["normal distribution"])
    result = store.answer("Explain normal distribution and osmosis")
    assert result is not None
    assert {row["section"] for row in result["citations"]} == {"Normal distribution", "Osmosis"}


def test_a_generic_function_word_is_not_treated_as_an_independent_topic(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Cell structure and function", "Cell structure and function are introduced here.", ["cell structure and function"])
    result = store.answer("Explain cell structure and function")
    assert result is not None
    assert result["supported_topics"] == ["cell structure and function"]


def test_a_general_definition_prefers_foundations_over_species_limited_research(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Introduction", "Taste was studied in chimpanzees.", ["taste"])
    store.metadata[store.records[0].chunk_id] = {"material_type": "research", "study_design": "narrative review"}
    change(store, store.records[1], "Introduction", "Taste is a sensory function. This foundation describes human taste.", ["taste"])
    result = store.answer("Explain taste")
    assert result is not None
    assert result["citations"][0]["chunk_id"] == store.records[1].chunk_id
    research = store.answer("Explain taste research in chimpanzees")
    assert research is not None
    assert research["citations"][0]["chunk_id"] == store.records[0].chunk_id


@pytest.mark.parametrize("question", [
    "Describe the clinical features, investigations and principles of management of bladder cancer",
    "Explain the pathophysiology and pathologic changes seen in hepatic failure and their clinical manifestations, complications and consequences",
    "Explain indications for and steps involved in tracheostomy and the care of the patient with a tracheostomy",
])
def test_disease_or_procedure_scope_cannot_be_replaced_by_generic_facets(tmp_path, question):
    store = make_store(tmp_path)
    change(store, store.records[0], "Oral cancer / Pathophysiology and clinical features",
           "Oral cancer has pathophysiology, clinical features and management considerations.", ["cancer"])
    change(store, store.records[1], "Drug indications", "Drug indications and consequences are discussed here.", ["indications"])
    assert store.answer(question) is None


def test_a_true_short_concept_can_still_match_the_plural_in_its_source(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Cutaneous eruptions / Rash", "Skin eruptions are rashes.", ["skin eruption"])
    assert store.answer("Explain skin eruption")["claims"][0]["text"] == store.records[0].text


def test_known_organ_modifier_still_has_to_be_supported_by_the_selected_passage(tmp_path):
    from collections import Counter

    store = make_store(tmp_path)
    change(store, store.records[0], "Oral cancer / Management", "Oral cancer management is discussed here.", ["cancer"])
    change(store, store.records[1], "Bladder anatomy / Principles", "Bladder anatomy principles are discussed here.", ["bladder"])
    store.df = Counter(word for row in store.records for word in teaching_terms(row.section + " " + row.text))
    assert store.answer("Explain principles of management of bladder cancer") is None


def test_a_numbered_curriculum_heading_is_presentation_not_a_medical_entity(tmp_path):
    store = make_store(tmp_path)
    result = store.answer("For MDS 3. Physiology (General & Oral) :, explain: Osmosis. Address the stated curriculum scope, underlying mechanisms and relevant terminology.")
    assert result is not None
    assert result["supported_topics"] == ["Osmosis"]


def test_mcq_references_do_not_present_an_unchecked_choice_verdict(tmp_path):
    store = make_store(tmp_path)
    result = store.answer("Osmosis: A water movement; B solute movement. Explain the correct option.")
    assert result is not None
    assert result["claims"][0]["text"] == store.records[2].text
    assert any("choice" in line.casefold() for line in result["limitations"])


def test_fictional_context_explanation_keeps_case_reasoning_explicitly_unverified(tmp_path):
    store = make_store(tmp_path)
    result = store.answer("In a fictional physiology case a learner asks a question. Explain osmosis.")
    assert result is not None
    assert any("case" in line.casefold() for line in result["unverified_requested_tasks"])


def test_dependent_clause_cannot_be_retrieved_as_a_standalone_generic_topic(tmp_path):
    store = make_store(tmp_path)
    result = store.answer("Explain osmosis and how solute particles cross by osmosis")
    assert result is not None
    assert result["supported_topics"] == ["osmosis and how solute particles cross by osmosis"]


def test_an_explicit_body_definition_is_not_hidden_by_a_general_section_title(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], "Control centre", "The control centre is the hypothalamus. This example concerns body temperature.", ["homeostasis"])
    result = store.answer("Explain hypothalamus")
    assert result is not None
    assert result["claims"][0]["text"] == store.records[0].text


def test_a_paired_note_accepts_discourse_words_but_keeps_the_drug_concept(tmp_path):
    store = make_store(tmp_path)
    row = store.records[0]
    change(store, row, "Free drug", "Free drug and protein-bound drug distribution are described here.", ["free drug"])
    store.units = [{"id": "pk", "topics": ["free drug"], "text": "Free drug circulates; protein-bound drug is a reservoir in drug distribution.", "citation_ids": [row.chunk_id]}]
    result = store.answer("Explain free drug distribution and how protein-bound drug can serve as a reservoir")
    assert result is not None
    assert result["claims"][0]["text"] == store.units[0]["text"]


def test_a_paired_homonym_note_cannot_bypass_the_phrase_guard(tmp_path):
    store = make_store(tmp_path)
    row = store.records[0]
    change(store, row, "Depression", "St. John's wort has been studied for depression.", ["depression"])
    store.units = [{"id": "mood", "topics": ["depression"], "text": "St. John's wort has been studied for depression.", "citation_ids": [row.chunk_id]}]
    assert store.answer("Explain ST depression") is None


def test_original_question_policy_and_product_identity_survive_presentation_wrappers(tmp_path):
    store = make_store(tmp_path)
    assert store.answer("Please explain osmosis in simple terms. Should I double my medicine?") is None
    assert store.answer("For a viva, explain: osmosis Dolo 650mg tablet.") is None


@pytest.mark.parametrize("question", [
    "For kidney failure, explain osmosis",
    "For an MBBS student with kidney failure, explain osmosis",
    "Explain diffusion and osmosis in kidney failure",
    "Compare diffusion and osmosis in kidney failure",
    "Explain diffusion and osmosis for children with kidney failure",
    "Compare diffusion and osmosis for dialysis",
    "Explain diffusion and osmosis under hypoxic conditions",
])
def test_medical_context_survives_prefixes_and_shared_compound_scope(tmp_path, question):
    store = make_store(tmp_path)
    change(store, store.records[0], "Diffusion", "Diffusion is passive movement of solute particles.", ["diffusion"])
    assert store.answer(question) is None


@pytest.mark.parametrize("facet", ["investigations", "diagnostic assessment", "management", "development"])
def test_paired_definition_cannot_claim_an_uncovered_clinical_facet(tmp_path, facet):
    store = make_store(tmp_path)
    row = store.records[0]
    change(store, row, "Depression", "Depression is a mood condition.", ["depression"])
    store.units = [{"id": "mood", "topics": ["depression"], "text": "Depression is a mood condition.", "citation_ids": [row.chunk_id]}]
    assert store.answer("Explain depression " + facet) is None


def test_long_question_cannot_hide_missing_investigations_in_generic_facets(tmp_path):
    from collections import Counter

    store = make_store(tmp_path)
    change(store, store.records[0], "Depression", "Depression is a mood condition. Management and structure are discussed here.", ["depression"])
    store.df = Counter(word for row in store.records for word in teaching_terms(row.section + " " + row.text))
    assert store.answer("Explain depression management investigations and structure") is None


@pytest.mark.parametrize("question", [
    "For kidney failure, explain osmosis",
    "For an MBBS student with kidney failure, explain osmosis",
    "Compare diffusion and osmosis for dialysis",
    "What is the difference between diffusion and osmosis for dialysis?",
    "Differences between diffusion and osmosis for dialysis",
    "For kidney failure, what is osmosis?",
    "For kidney failure, tell me about osmosis",
])
def test_unsupported_teaching_scope_cannot_fall_back_to_an_unrelated_primary_note(tmp_path, question):
    from backend.app.config import Settings
    from backend.app.services.answers import AnswerService

    store = make_store(tmp_path)
    store.units = [{"id": "osmosis", "topics": ["osmosis", "diffusion"], "text": store.records[2].text,
                    "citation_ids": [store.records[2].chunk_id]}]

    class Primary:
        def matched_identities(self, question):
            return []

        def catalogue_match(self, question):
            return None

        def search(self, question):
            return [store.records[0]]

    result = AnswerService(Settings(_env_file=None, answer_mode="extractive"), Primary(), None, None, teaching=store).answer(question)
    assert result["status"] == "insufficient_evidence"
    assert not result["claims"]
    assert result["unsupported_topics"] == [question]


@pytest.mark.parametrize("question, expected", [
    ("What do systolic and diastolic blood pressure mean?", "ok"),
    ("Compare mean and median for kidney failure", "insufficient_evidence"),
    ("What is the difference between mean and median in liver disease?", "insufficient_evidence"),
])
def test_mean_noun_scope_is_preserved_without_blocking_the_question_verb(tmp_path, question, expected):
    from backend.app.config import Settings
    from backend.app.services.answers import AnswerService

    store = make_store(tmp_path)
    store.units = [{"id": "mean", "topics": ["mean"], "text": "A statistics definition.", "citation_ids": [store.records[2].chunk_id]}]
    primary_row = store.records[0].model_copy(update={"section": "Blood pressure", "text": "Synthetic primary reference fixture."})

    class Primary:
        def matched_identities(self, question):
            return []

        def catalogue_match(self, question):
            return None

        def search(self, question):
            return [primary_row]

    result = AnswerService(Settings(_env_file=None, answer_mode="extractive"), Primary(), None, None, teaching=store).answer(question)
    assert result["status"] == expected
    if expected == "ok":
        assert result["answer_method"] == "extractive"
        assert result["claims"][0]["text"] == primary_row.text
    else:
        assert not result["claims"]
