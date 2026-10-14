from types import SimpleNamespace

import pytest

from backend.app.services.question_plan import plan_question


def test_oracle_runner_requires_actual_label_provenance():
    from research.evaluate.oracles import run_case

    with pytest.raises(ValueError, match="independent"):
        run_case(None, "Define oral epithelium", {"independent": False})


def test_four_oracle_arms_preserve_normal_terminal_validation():
    from research.evaluate.oracles import run_case

    question = "Define a synthetic concept."
    plan = plan_question(question, "study")
    row = SimpleNamespace(chunk_id="synthetic-passage", content_hash=lambda: "a" * 64)
    teacher = SimpleNamespace(search=lambda query, limit=8: [], references=SimpleNamespace(id_records={row.chunk_id: row}))
    seen = []

    class Service:
        teaching = teacher

        def answer(self, q, audience, question_plan=None):
            seen.append((question_plan is not None, bool(self.teaching.search(q))))
            return {"terminal_validation_fixture": True, "claims": [], "coverage_status": "insufficient_evidence"}

    labels = {"independent": True, "author": "Synthetic test fixture author",
              "label_origin": "synthetic_mechanics", "question_plan": plan.model_dump(),
              "passage_hashes": {row.chunk_id: "a" * 64}}
    result = run_case(Service(), question, labels)
    assert set(result["arms"]) == {"baseline", "oracle_plan", "oracle_evidence", "both"}
    assert seen == [(False, False), (True, False), (False, True), (True, True)]
    assert all(value["terminal_validation_fixture"] for value in result["arms"].values())
    assert result["clinical_accuracy"] is None
