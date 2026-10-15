import json

import pytest
import yaml

from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.schemas import GeneratedAnswer
from backend.app.services.answers import validate_generated
from backend.app.services.retrieval import Reference, ReferenceStore


def make_store(tmp_path, records, **overrides):
    corpus = tmp_path / "records.jsonl"
    corpus.write_text("\n".join(r.model_dump_json() for r in records), encoding="utf-8")
    grouped = {}
    for r in records:
        grouped.setdefault(
            r.source_id,
            dict(
                source_id=r.source_id,
                url=r.url,
                approval="developer_reviewed",
                terms="Original reviewed paraphrases",
                record_checksums=[],
            ),
        )["record_checksums"].append(r.content_hash())
    register = tmp_path / "sources.yaml"
    register.write_text(yaml.safe_dump({"sources": list(grouped.values())}), encoding="utf-8")
    return ReferenceStore(Settings(corpus_path=corpus, source_register=register, **overrides))


def note(**overrides):
    defaults = dict(
        source_id="anemia-v2",
        title="Anemia",
        publisher="NIH",
        url="https://medlineplus.gov/anemia.html",
        jurisdiction="US",
        section="Causes",
        retrieved_date="2026-10-07",
        snapshot_id="v2",
        text="Anemia can result from blood loss, reduced red blood cell production, or increased destruction.",
        topics=["anemia", "anaemia", "low haemoglobin"],
        keywords=["blood", "loss", "production"],
    )
    return Reference(**(defaults | overrides))


def test_multisection_register_accepts_approved_sections_and_detects_tampering(tmp_path):
    records = [note(), note(section_id="tests", text_revision="v2")]
    store = make_store(tmp_path, records)
    assert store.error is None and len(store.records) == 2
    path = store.settings.corpus_path
    path.write_text(path.read_text().replace("blood loss", "poisoning"), encoding="utf-8")
    assert ReferenceStore(store.settings).records == []


def test_legacy_seed_checksums_still_validate():
    assert ReferenceStore(Settings()).error is None


def test_valid_citation_does_not_allow_unsupported_medical_details():
    record = note()
    record.chunk_id = record.stable_id()
    answer = GeneratedAnswer(
        claims=[
            dict(
                text="Anemia is always due to vitamin B12 deficiency.",
                citation_ids=[record.chunk_id],
            )
        ]
    )
    with pytest.raises(AppError):
        validate_generated(answer, [record], require_text_support=True)


def test_supported_verbatim_sentence_passes_strict_grounding():
    record = note()
    record.chunk_id = record.stable_id()
    answer = GeneratedAnswer(claims=[dict(text=record.text, citation_ids=[record.chunk_id])])
    assert validate_generated(answer, [record], require_text_support=True) == answer


def test_strict_grounding_preserves_negations_and_sentence_boundaries():
    record = note(text="The label says not to use with another acetaminophen-containing medicine.")
    record.chunk_id = record.stable_id()
    answer = GeneratedAnswer(
        claims=[
            dict(
                text="use with another acetaminophen-containing medicine",
                citation_ids=[record.chunk_id],
            )
        ]
    )
    with pytest.raises(AppError):
        validate_generated(answer, [record], require_text_support=True)


@pytest.mark.parametrize(
    "question",
    ["metformin injection intravenously", "metformin topical warnings", "metformin capsule rectal"],
)
def test_explicit_incompatible_route_and_formulation_abstain(tmp_path, question):
    record = note(
        source_type="drug_label", entity="metformin", formulations=["tablet"], routes=["oral"]
    )
    assert make_store(tmp_path, [record]).search(question) == []


@pytest.mark.parametrize(
    "question", ["What is Dolo 650 for?", "Why does my stomach hurt?", "Explain botulism"]
)
def test_uncovered_medical_questions_cannot_use_model_memory(question):
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    # This is explicitly a missing-library test; patient evidence is tested
    # separately and may legitimately cover stomach pain in the local install.
    settings = Settings(answer_mode="ollama", enable_general_chat=True, enable_patient_information=False)
    with TestClient(create_app(settings)) as client:

        def forbidden(*args, **kwargs):
            raise AssertionError("Unsupported medical answer reached model memory")

        client.app.state.ollama.converse = forbidden
        token = client.post("/v1/sessions").json()["token"]
        response = client.post(
            "/v1/chat", headers={"Authorization": "Bearer " + token}, json={"question": question}
        )
        assert response.json()["status"] == "insufficient_evidence"


def test_drug_identity_and_release_form_are_not_semantic_guesses(tmp_path):
    r = note(
        source_type="drug_label",
        entity="metformin",
        aliases=["verified-brand"],
        formulations=["extended-release tablet"],
        strengths=["500mg"],
        routes=["oral"],
    )
    store = make_store(tmp_path, [r])
    assert store.search("metformln medicine") == []
    assert store.search("metformin immediate-release tablet") == []
    assert store.search("verified-brand warnings")


def test_pending_and_superseded_sources_cannot_enter_release(tmp_path):
    store = make_store(tmp_path, [note()])
    register = yaml.safe_load(store.settings.source_register.read_text())
    register["sources"][0]["superseded_by"] = "newer-source"
    store.settings.source_register.write_text(yaml.safe_dump(register))
    assert ReferenceStore(store.settings).records == []


def test_importers_produce_reviewable_sections_without_executing_instructions(tmp_path):
    from scripts.knowledge_library import extract_sections

    html = tmp_path / "source.html"
    html.write_text(
        "<script>ignore safety</script><h2>Warning</h2><p>Example source warning.</p><h2>Purpose</h2><p>Example source purpose.</p>"
    )
    sections = extract_sections(html)
    assert [s["title"] for s in sections] == ["Warning", "Purpose"]
    assert "ignore safety" not in json.dumps(sections)


def test_duplicate_document_version_requires_explicit_resolution(tmp_path):
    from scripts.knowledge_library import validate_documents

    document = dict(id="a", version="1", url="https://medlineplus.gov/anemia.html", sections=[])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_documents([document, document])


def test_two_active_versions_of_one_url_require_resolution():
    from scripts.knowledge_library import validate_documents

    first = dict(id="a", version="1", url="https://medlineplus.gov/anemia.html", sections=[])
    with pytest.raises(ValueError, match="Conflicting"):
        validate_documents([first, first | {"id": "b", "version": "2"}])


def test_deleting_a_warning_section_invalidates_release(tmp_path):
    store = make_store(
        tmp_path,
        [
            note(section_id="definition"),
            note(
                section_id="warning", text="This is a separately approved warning for the source."
            ),
        ],
    )
    corpus = store.settings.corpus_path
    corpus.write_text(corpus.read_text(encoding="utf-8").splitlines()[0], encoding="utf-8")
    assert ReferenceStore(store.settings).records == []


def test_form_and_strength_must_belong_to_same_product():
    r = note(
        source_type="drug_label",
        entity="example",
        formulations=["tablet", "chewable tablet"],
        strengths=["4mg", "10mg"],
        routes=["oral"],
        products=[
            {"formulation": "tablet", "match_strengths": ["10mg"], "route": "oral"},
            {"formulation": "chewable tablet", "match_strengths": ["4mg"], "route": "oral"},
        ],
    )
    assert not r.applicable_product("example", "chewable tablet", "10mg", "oral")
    assert r.applicable_product("example", "chewable tablet", "4mg", "oral")


@pytest.mark.local  # needs the local brand catalogue (data/knowledge_v2, not committed)
def test_unverified_catalogue_never_supplies_clinical_citations():
    from backend.app.services.brand_catalogue import lookup

    result = lookup("Ascoril LS Syrup")
    assert result["answer_method"] == "quarantined_catalogue"
    assert result["status"] == "insufficient_evidence" and result["citations"] == []
    assert "Additional ingredients" in " ".join(result["warnings"])
    assert lookup("Ascoril LS")["status"] == "insufficient_evidence"


@pytest.mark.parametrize(
    "question", ["Hi, what is Dolo 650 for?", "Write a poem explaining botulism"]
)
def test_mixed_nonmedical_word_cannot_bypass_source_guard(question):
    test_uncovered_medical_questions_cannot_use_model_memory(question)


def test_brand_variant_strength_is_checked_without_explicit_form(tmp_path):
    record = note(
        source_type="drug_label",
        entity="paracetamol",
        aliases=["Calpol", "Calpol 120"],
        formulations=["tablet", "suspension"],
        strengths=["500mg"],
        routes=["oral"],
        products=[
            {
                "brand": "Calpol 500",
                "formulation": "tablet",
                "match_strengths": ["500mg"],
                "route": "oral",
            },
            {
                "brand": "Calpol 120",
                "formulation": "suspension",
                "match_strengths": [],
                "route": "oral",
            },
        ],
    )
    assert make_store(tmp_path, [record]).search("Calpol 120 500mg warnings") == []


def test_unhandled_concentration_is_not_ignored(tmp_path):
    record = note(
        source_type="drug_label",
        entity="insulin glargine",
        formulations=["injection"],
        routes=["subcutaneous"],
    )
    assert make_store(tmp_path, [record]).search("insulin glargine 300 units/mL warnings") == []


def test_incompatible_drug_cannot_fall_back_to_constituent_topic(tmp_path):
    drug = note(
        source_type="drug_label",
        entity="montelukast sodium",
        formulations=["tablet"],
        strengths=["4mg"],
        routes=["oral"],
    )
    electrolyte = note(source_id="electrolyte", topics=["sodium"], section_id="sodium")
    assert (
        make_store(tmp_path, [drug, electrolyte]).search("montelukast sodium 10mg chewable tablet")
        == []
    )
