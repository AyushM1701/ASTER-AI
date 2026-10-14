from contextlib import nullcontext
from types import SimpleNamespace

from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.schemas import GeneratedAnswer
from backend.app.services.answers import AnswerService
from tests.mds_fixtures import make_teacher
from tests.test_knowledge_v2 import make_store, note


def test_safety_failed_generation_cannot_escape_as_benign_source_fallback(tmp_path):
    store = make_store(tmp_path, [note()])
    def generate(*args):
        return GeneratedAnswer(claims=[{"text": "You should take 50 mg daily.", "citation_ids": [store.records[0].chunk_id]}])
    service = AnswerService(Settings(answer_mode="ollama", strict_source_grounding=True), store,
                            SimpleNamespace(generate=generate), SimpleNamespace(enter=nullcontext))
    result = service.answer("Explain anemia")
    assert result["status"] == "insufficient_evidence"
    assert not result["claims"]
    assert "safety_failed_generation" in result["rejection_codes"]


def test_outage_fallback_keeps_transport_failure_separate_from_evidence(tmp_path):
    store = make_store(tmp_path, [note()])
    def generate(*args):
        raise AppError(503, "error", "Model unavailable")
    service = AnswerService(Settings(answer_mode="ollama", strict_source_grounding=True), store,
                            SimpleNamespace(generate=generate), SimpleNamespace(enter=nullcontext))
    result = service.answer("Explain anemia")
    assert result["claims"]
    assert result["model_failure"]["upstream_status_code"] == 503
    assert result["model_failure"]["kind"] == "transport_error"


def test_shadow_synthesis_draft_is_never_shown_and_runs_only_one_model_call(tmp_path):
    teacher, _ = make_teacher(tmp_path, [("oral epithelium", "Oral epithelium / Functions", "Oral epithelium functions as a synthetic barrier with qualifications retained in this fixture.")])
    seen = []
    def synthesize(plan, records):
        seen.append(1)
        return SimpleNamespace(claims=[SimpleNamespace(text="PRIVATE UNVALIDATED DRAFT", citation_ids=[next(iter(records))])])
    service = AnswerService(Settings(mds_synthesis_mode="shadow"), teacher.references,
                            SimpleNamespace(synthesize=synthesize), SimpleNamespace(enter=nullcontext), teaching=teacher)
    result = service.answer("Explain oral epithelium functions", audience="study")
    assert len(seen) == 1
    assert "PRIVATE UNVALIDATED DRAFT" not in str(result)
    assert result["shadow_evaluation"]["displayed"] is False
    assert result["claims"][0]["text"].startswith("Oral epithelium functions")
