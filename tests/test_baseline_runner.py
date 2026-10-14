from types import SimpleNamespace

import pytest

from backend.app.services.retrieval import Reference


def reference(identity, text):
    return Reference(source_id=identity, title="Synthetic mechanical fixture", url="https://example.test/fixture",
                     publisher="Test", jurisdiction="Global", section="Synthetic concept definition",
                     retrieved_date="2026-10-13", snapshot_id="synthetic", text=text,
                     topics=["synthetic concept"], keywords=["synthetic"], chunk_id=identity)


def teacher():
    rows = [reference("short", "Synthetic concept is a defined concept with a coherent definition."),
            reference("long", "Synthetic concept " + "other material " * 80),
            reference("held", "Synthetic concept is a definition that must remain withheld.")]
    return SimpleNamespace(records=rows, metadata={}, review_flags={"held": {"runtime_policy": "exclude"}},
                           version="synthetic", references=SimpleNamespace(id_records={r.chunk_id: r for r in rows}))


def test_bm25_uses_document_length_and_rrf_uses_ranks():
    from research.baselines.runner import RetrievalExperiment, reciprocal_rank_fusion

    experiment = RetrievalExperiment(teacher(), candidate_budget=2)
    assert experiment.retrieve("synthetic concept", "B0")[0] == "short"
    assert reciprocal_rank_fusion([["b", "a"], ["a", "c"]], limit=2) == ["a", "b"]


def test_holds_are_excluded_from_every_strategy_and_budget_is_total():
    from research.baselines.runner import RetrievalExperiment

    store = teacher()
    seen = []

    def dense(query, allowed):
        seen.append(set(allowed))
        return ["held", "long", "short"]

    experiment = RetrievalExperiment(store, candidate_budget=1, dense_rank=dense)
    for strategy in ("B0", "B2", "B3", "B5"):
        result = experiment.retrieve("Compare synthetic concept and another concept", strategy)
        assert len(result) <= 1
        assert "held" not in result
    assert all("held" not in allowed for allowed in seen)


def test_b6_inspected_bindings_cannot_bypass_budget_and_guard_runs():
    from research.baselines.runner import RetrievalExperiment

    store = teacher()
    store.metadata["long"] = {"ai_inspected_facet_bindings": [
        {"topic_id": "local:synthetic_concept", "facet": "definition", "scope": ""}]}
    result = RetrievalExperiment(store, candidate_budget=1).run_case(
        {"case_id": "fixture", "question": "Define synthetic concept.", "major": "synthetic"}, "B6")
    assert result["candidate_ids"] == ["short"]
    assert result["answer"]["facet_diagnostics"][0]["terminal_guard_executed"] is True
    assert all(r["chunk_id"] != "long" for r in result["answer"]["evidence_plan"]["rejected"])


def test_unlabelled_metrics_remain_unknown_and_missing_dense_is_not_a_fake_run():
    from research.baselines.runner import RetrievalExperiment

    experiment = RetrievalExperiment(teacher(), candidate_budget=2)
    result = experiment.run_case({"case_id": "fixture", "question": "Define synthetic concept."}, "B0")
    assert result["metrics"]["recall_at_k"] is None
    assert result["clinical_accuracy"] is None
    unavailable = experiment.run_case({"case_id": "fixture", "question": "Define synthetic concept."}, "B2")
    assert unavailable["status"] == "not_run"
    assert unavailable["reason"] == "frozen_dense_index_unavailable"


def test_false_gold_identity_is_rejected_and_provenance_is_required():
    from research.baselines.runner import RetrievalExperiment

    experiment = RetrievalExperiment(teacher())
    case = {"case_id": "fixture", "question": "Define synthetic concept.", "gold": {"missing": 3}}
    with pytest.raises(ValueError, match="label provenance"):
        experiment.run_case(case, "B0")
    case["label_origin"] = "synthetic_mechanics"
    with pytest.raises(ValueError, match="gold identity"):
        experiment.run_case(case, "B0")


def test_snapshot_detects_mutation_and_never_overwrites(tmp_path):
    from research.baselines.runner import Snapshot, create_output

    source = tmp_path / "source.txt"
    source.write_text("first", encoding="utf-8")
    snapshot = Snapshot({"source": source})
    source.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        snapshot.verify()
    create_output(tmp_path / "run")
    with pytest.raises(FileExistsError):
        create_output(tmp_path / "run")


def test_runner_captures_actual_rows_with_no_invented_scores(tmp_path):
    import json

    from research.baselines.runner import (
        EvaluationPipelineConfig,
        RetrievalExperiment,
        Snapshot,
        run,
    )

    source = tmp_path / "fixture.txt"
    source.write_text("Synthetic mechanical fixture", encoding="utf-8")
    snapshot = Snapshot({"fixture": source})
    config = EvaluationPipelineConfig(run_id="test", candidate_budget=2, source_version="synthetic",
                                      input_hashes=snapshot.hashes, strategies=["B0", "B2", "B6", "B7"])
    cases = [{"case_id": "fixture", "question": "Define synthetic concept."}]
    output = tmp_path / "run"
    result = run(RetrievalExperiment(teacher(), candidate_budget=2), config, cases, snapshot, output)
    assert result[0]["captured"] == 1 and result[0]["labelled_cases"] == 0
    assert result[1]["captured"] == 0 and result[3]["captured"] == 0
    assert json.loads((output / "manifest.json").read_text())["status"] == "stable_during_capture"
    rows = [json.loads(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
    assert rows[0]["metrics"]["recall_at_k"] is None
    with pytest.raises(FileExistsError):
        run(RetrievalExperiment(teacher(), candidate_budget=2), config, cases, snapshot, output)


def test_mid_run_mutation_invalidates_manifest(tmp_path):
    import json

    from research.baselines.runner import (
        EvaluationPipelineConfig,
        RetrievalExperiment,
        Snapshot,
        run,
    )

    source = tmp_path / "fixture.txt"
    source.write_text("first", encoding="utf-8")
    snapshot = Snapshot({"fixture": source})

    def dense(query, allowed):
        source.write_text("changed", encoding="utf-8")
        return ["short"]

    config = EvaluationPipelineConfig(run_id="test", candidate_budget=2, source_version="synthetic",
                                      input_hashes=snapshot.hashes, strategies=["B2"])
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="changed"):
        run(RetrievalExperiment(teacher(), candidate_budget=2, dense_rank=dense), config,
            [{"case_id": "fixture", "question": "Define synthetic concept."}], snapshot, output)
    assert json.loads((output / "manifest.json").read_text())["status"] == "invalid"


def test_b6_checks_the_full_declared_budget_beyond_eight_candidates():
    from research.baselines.runner import RetrievalExperiment

    store = teacher()
    unrelated = [reference(f"unrelated-{index}", "Other material about another unrequested topic with unrelated qualifications.") for index in range(8)]
    store.records = [*unrelated, store.records[0]]
    store.references.id_records = {row.chunk_id: row for row in store.records}
    experiment = RetrievalExperiment(store, candidate_budget=10)
    result = experiment.checked_answer("Define synthetic concept.", [row.chunk_id for row in store.records])
    assert len(result["claims"]) == 1
    assert result["claims"][0]["citation_ids"] == ["short"]
    assert result["evidence_plan"]["facets"][0]["candidate_count"] == 9
