"""Offline audit and local API capture for the immutable supplied MDS bank.

Commands: verify; audit --output NEW_DIRECTORY; run --output NEW_DIRECTORY.
No external network or clinical accuracy score. Output folders cannot overwrite.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.mds_supplied_contracts import (  # noqa: E402
    DEFAULT_BANK,
    digest,
    read_rows,
    verify_bank,
)

DEFAULT_RELEASE = ROOT / "data/references/mds/releases/aster-teaching-all-mds-v3-2026-10-10"
CODE_FILES = (
    "backend/app/services/question_plan.py", "backend/app/services/mds_curriculum.py",
    "backend/app/services/evidence_plan.py", "backend/app/services/answer_composer.py",
    "backend/app/services/output_validation.py", "backend/app/services/chat.py",
    "backend/app/services/viva.py", "backend/app/main.py",
    "backend/app/services/answers.py", "backend/app/services/sessions.py", "backend/app/schemas.py",
    "scripts/mds_pilot.py", "scripts/evaluate_mds_pipeline.py",
)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_output(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    return output


def code_snapshot():
    paths = {ROOT / name for name in CODE_FILES if (ROOT / name).is_file()}
    paths.update((ROOT / "backend/app").rglob("*.py"))
    paths.update({Path(__file__), ROOT / "scripts/mds_supplied_contracts.py"})
    return {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path.read_bytes()) for path in sorted(paths)}


def cases_from_bank(bank, include_variations=False):
    verify_bank(bank)
    cases = read_rows(bank / "supplied.jsonl")
    if include_variations:
        cases.extend(read_rows(bank / "variations.jsonl"))
    return cases


def audit(args):
    """Inspect planner and source identity signals, independently of runtime claims."""
    before = code_snapshot()
    from backend.app.services.question_plan import plan_question
    from scripts.mds_pilot import source_snapshot

    cases = cases_from_bank(args.bank, args.variations)
    output = prepare_output(args.output)
    source_before = source_snapshot(args.release)
    planner_rows = []
    for case in cases:
        context_topic = None
        for number, turn in enumerate(case["turns"], 1):
            plan = plan_question(turn["question"], case["audience"], context_topic=context_topic)
            actual = plan.model_dump()
            expected_topics = set(case["topic_ids"])
            turn_facets = case.get("turn_content_contracts", [case["expected_facets"]] * len(case["turns"]))[number - 1]
            expected_facets = {(f["topic_id"], f["facet"]) for f in turn_facets}
            actual_facets = {(f["topic_id"], f["facet"]) for f in actual["facets"]}
            planner_rows.append({"case_id": case["case_id"], "turn": number, "question": turn["question"],
                                 "question_sha256": turn["question_sha256"], "expected_task_shape": case["task_shape"],
                                 "expected_topics": sorted(expected_topics), "actual_plan": actual,
                                 "missing_exact_topic_ids": sorted(expected_topics - set(actual["canonical_topics"])),
                                 "missing_exact_facet_keys": [{"topic_id": t, "facet": f} for t, f in sorted(expected_facets - actual_facets)],
                                 "provided_context_topic": context_topic,
                                 "interpretation": "Exact contract-ID differences require semantic adjudication; this does not measure answer correctness or completeness."})
            # This deliberately shows the planner's context-argument behavior.
            # It is not a claim that API conversation memory passed the test.
            context_topic = case["topic_names"][0]
    records = read_rows(args.release / "records.jsonl")
    topics = {}
    for case in cases:
        for identity, name in zip(case["topic_ids"], case["topic_names"]):
            topics[identity] = name
    source_rows = []
    for identity, name in sorted(topics.items()):
        # Literal independent subject mentions. Existing aliases are not used,
        # because this report audits their gaps too. Synonyms can yield false negatives.
        pattern = re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.I)
        hits = [row for row in records if pattern.search(row.get("text", ""))]
        source_rows.append({"topic_id": identity, "topic_name": name, "literal_mention_chunks": len(hits),
                            "literal_mention_sources": len({row.get("source_id") for row in hits}),
                            "clinically_reviewed_mention_chunks": sum(row.get("clinical_review") is True for row in hits),
                            "example_chunk_ids": [row["chunk_id"] for row in hits[:5]],
                            "scientific_sufficiency": None, "reason": "A literal mention can occur in unrelated prose; no facet support or specialist adequacy is inferred."})
    after = code_snapshot()
    source_after = source_snapshot(args.release)
    report = {"bank_version": verify_bank(args.bank)["version"], "manifest_sha256": digest((args.bank / "manifest.json").read_bytes()),
              "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "cases": len(cases),
              "turns": len(planner_rows), "source_chunks": len(records), "source_set": source_before,
              "source_topics_with_no_literal_mentions": sum(row["literal_mention_chunks"] == 0 for row in source_rows),
              "source_topic_count": len(source_rows), "planner_task_counts": dict(Counter(row["actual_plan"]["task"] for row in planner_rows)),
              "first_turns_with_missing_exact_topic_ids": sum(bool(row["missing_exact_topic_ids"]) for row in planner_rows if row["turn"] == 1),
              "first_turns_with_missing_exact_facet_keys": sum(bool(row["missing_exact_facet_keys"]) for row in planner_rows if row["turn"] == 1),
              "code_sha256": before, "code_after_sha256": after, "code_changed_during_audit": before != after,
              "source_changed_during_audit": source_before != source_after,
              "clinical_accuracy": None, "clinical_completeness": None, "independent_unseen": False,
              "method_limits": ["Scope-only developer annotations, no medical answer keys.",
                                "Exact ID mismatches may include synonyms; inspect individual rows.",
                                "Source mention counts cannot establish evidence sufficiency.",
                                "Later turns receive explicitly supplied topic context; real session memory requires the run command."]}
    write_json(output / "planner-audit.json", planner_rows)
    write_json(output / "source-mention-audit.json", source_rows)
    write_json(output / "summary.json", report)
    print(json.dumps(report, indent=2))
    return report


def task_shape_signals(case, result, turn_number):
    """Observable structural signals only; a missing feature may be unsupported."""
    shape = case["task_shape"]
    comparison = result.get("comparison") or {}
    viva = result.get("viva") or {}
    signals = {"coverage_status": result.get("coverage_status"), "clinical_accuracy": None,
               "clinical_completeness": None}
    if shape in {"comparison", "comparison_table", "educational_case_comparison"}:
        axes = comparison.get("axes") or []
        rows = comparison.get("rows") or []
        signals["structured_comparison_present"] = any(
            isinstance(axis, dict) and isinstance(axis.get("cells"), list) and len(axis["cells"]) >= 2
            for axis in axes
        ) or any(isinstance(row, dict) and isinstance(row.get("cells"), list) and len(row["cells"]) >= 2 for row in rows)
        signals["comparison_cells_require_human_review"] = True
    if shape in {"interactive_viva", "progressive_viva"} and (shape != "progressive_viva" or turn_number >= 3):
        signals["viva_state_present"] = bool(viva)
        signals["viva_state"] = viva
        signals["one_question_then_wait_requires_review"] = True
    if len(case["turns"]) > 1:
        signals["context_retention_depth_and_repetition_require_review"] = True
    if shape == "multipart":
        signals["separate_parts_require_review"] = True
    if "case" in shape:
        signals["differential_missing_information_uncertainty_require_review"] = True
    if shape in {"evidence_review", "research_appraisal"}:
        signals["evidence_quality_currency_and_claim_support_require_review"] = True
    return signals


def prepared_identity_signals(case, response, records, units, metadata, flags):
    """Resolve prepared pointers against pinned files, never output declarations.

    This measures exact paired-text identity and annotation presence. It neither
    proves paraphrase entailment nor evaluates the medical content of the pair.
    Reference.content_hash is only the project's record serialization identity.
    Runtime prepared_support/valid_prepared_mapping are deliberately not called.
    """
    from backend.app.services.retrieval import Reference

    mappings = response.get("prepared_claim_evidence") or []
    claims = response.get("claims") or []
    citations = response.get("citations") or []
    citation_counts = Counter(c.get("chunk_id") for c in citations if isinstance(c, dict))
    displayed = {c.get("chunk_id"): c for c in citations if isinstance(c, dict)}
    by_id = {}
    for unit in units:
        by_id.setdefault(unit.get("id"), []).append(unit)
    valid_indices, bound, checks = set(), set(), []
    for mapping in mappings:
        reasons = []
        if not isinstance(mapping, dict):
            checks.append({"valid": False, "reason": "malformed_pointer"})
            continue
        index = mapping.get("claim_index")
        candidates = by_id.get(mapping.get("prepared_id"), [])
        if type(index) is not int or not 0 <= index < len(claims) or len(candidates) != 1:
            checks.append({"valid": False, "reason": "missing_or_duplicate_trusted_unit_or_claim_index"})
            continue
        unit, claim = candidates[0], claims[index]
        text, ids, hashes = unit.get("text"), unit.get("citation_ids"), unit.get("source_hashes")
        binding = {"topic_id": mapping.get("topic_id"), "facet": mapping.get("facet"), "scope": mapping.get("scope")}
        if (not isinstance(text, str) or not text or unit.get("prepared_text_sha256") != digest(text.encode())
                or unit.get("review_status") != "developer_reviewed" or not unit.get("reviewer")
                or unit.get("clinical_review") is not False or claim.get("text") != text):
            reasons.append("trusted_text_or_review_identity_changed")
        if (not isinstance(ids, list) or not ids or len(ids) != len(set(ids))
                or not isinstance(hashes, dict) or set(ids) != set(hashes)
                or claim.get("citation_ids") != ids):
            reasons.append("parent_reference_set_changed")
            ids = []
        if binding not in unit.get("facet_bindings", []):
            reasons.append("no_exact_predeclared_facet_scope_binding")
        expected_pointer = {"claim_index": index, "prepared_id": unit.get("id"), **binding,
                            "prepared_text_sha256": unit.get("prepared_text_sha256"), "source_hashes": hashes}
        if mapping != expected_pointer:
            reasons.append("pointer_does_not_equal_trusted_unit_metadata")
        qualifications = unit.get("qualifications", [])
        if not isinstance(qualifications, list) or any(not isinstance(q, str) or not q or q.casefold() not in str(text).casefold() for q in qualifications):
            reasons.append("qualifications_missing")
        for key in ids:
            try:
                row = Reference.model_validate(records[key])
                content_hash = row.content_hash()
            except (KeyError, TypeError, ValueError):
                reasons.append("missing_or_invalid_parent_record")
                continue
            flag, context = flags.get(key), metadata.get(key, {})
            if hashes[key] != content_hash or row.source_type != "teaching" or row.clinical_review is not False:
                reasons.append("parent_record_hash_or_role_changed")
            expected_citation = row.citation()
            if flag:
                allowed = (flag.get("runtime_policy") == "explanation_only" and flag.get("clinical_review") is False
                           and flag.get("content_sha256") == content_hash and unit.get("id") in flag.get("allowed_explanation_ids", [])
                           and isinstance(flag.get("reason"), str) and bool(flag["reason"].strip()))
                if not allowed:
                    reasons.append("held_parent_without_exact_unit_exception")
                if flag.get("runtime_policy") == "explanation_only":
                    expected_citation["source_review_notice"] = flag.get("reason")
            if context.get("runtime_policy") == "explanation_only" and not flag:
                reasons.append("metadata_hold_without_bound_exception")
            if displayed.get(key) != expected_citation or citation_counts[key] != 1:
                reasons.append("displayed_parent_citation_changed_or_duplicated")
            if context.get("material_type") == "research" or row.permission_basis.get("material_type") == "research":
                study_context = context.get("study_context")
                if (not row.source_date or not context.get("study_type") or not context.get("limitations")
                        or not isinstance(study_context, str) or not study_context
                        or study_context not in row.text or study_context not in str(text)):
                    reasons.append("research_context_or_limitations_unresolved")
        good = not reasons
        checks.append({"claim_index": index, "prepared_id": unit.get("id"), "valid": good,
                       "reasons": sorted(set(reasons)), "topic_id": binding["topic_id"], "facet": binding["facet"]})
        if good:
            valid_indices.add(index)
            bound.add((binding["topic_id"], binding["facet"]))
    # A malformed extra pointer invalidates that claim's prepared channel.
    invalid_indices = {check.get("claim_index") for check in checks if not check["valid"]}
    valid_indices -= invalid_indices
    bound = {(check["topic_id"], check["facet"]) for check in checks if check["valid"] and check["claim_index"] in valid_indices}
    expected = {(f["topic_id"], f["facet"]) for f in case.get("expected_facets", [])}
    return {"mapping_checks": checks, "valid_claim_indices": sorted(valid_indices),
            "bound_facets": [{"topic_id": t, "facet": f} for t, f in sorted(bound)],
            "requested_prepared_facet_signal": {"numerator": len(expected & bound), "denominator": len(expected)},
            "clinical_accuracy": None, "clinical_completeness": None, "semantic_support": None,
            "method": "exact_claim_and_trusted_prepared_unit_identity_source_record_hashes_metadata_and_displayed_citation_identity"}


def run(args):
    """Call actual API routes with isolated sessions, offline and source-pinned.

    Supplied conversation turns share a session. The supplied grading instruction
    in cross-E is sent verbatim and explicitly annotated as NOT a learner answer.
    Optional viva probes insert a disclosed nonsense answer in a separate probe
    sequence after supplied turns. They never contribute a medical accuracy score.
    """
    before = code_snapshot()
    from fastapi.testclient import TestClient

    from backend.app.config import Settings
    from backend.app.main import create_app
    from scripts.mds_pilot import score_response, source_snapshot

    cases = cases_from_bank(args.bank, args.variations)
    if args.case:
        cases = [case for case in cases if case["case_id"] in args.case]
        if not cases:
            raise ValueError("No requested case IDs exist")
    if args.limit:
        cases = cases[:args.limit]
    output = prepare_output(args.output)
    source_before = source_snapshot(args.release)
    records = {row["chunk_id"]: row for row in read_rows(args.release / "records.jsonl")}
    prepared_document = json.loads((args.release / "explanations.json").read_text(encoding="utf-8"))
    prepared_units = prepared_document.get("units", [])
    prepared_flags = {flag["chunk_id"]: flag for flag in prepared_document.get("source_review_flags", [])}
    source_metadata_document = json.loads((args.release / "metadata.json").read_text(encoding="utf-8"))
    source_metadata = source_metadata_document.get("chunks", source_metadata_document)
    captured, scores = [], []
    with tempfile.TemporaryDirectory(prefix="aster-supplied-mds-") as temporary:
        settings = Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                            enable_mds_pipeline=True, enable_general_chat=False, answer_mode="extractive",
                            enable_research_search=False, teaching_release_path=args.release.resolve(),
                            teaching_explanations_path=args.release.resolve() / "explanations.json",
                            teaching_explanations_sha256=source_before["files"].get("explanations.json", ""),
                            corpus_path=ROOT / "data/references/normalized/seed.jsonl",
                            source_register=ROOT / "configs/sources.yaml",
                            patient_release_path=ROOT / "data/references/patient/releases/aster-patient-v1-2026-10-10",
                            workspace_path=Path(temporary) / "workspace.sqlite3")
        with TestClient(create_app(settings)) as client:
            if client.app.state.teaching.error:
                raise ValueError("Teaching release load failed: " + client.app.state.teaching.error)
            for case in cases:
                session = client.post("/v1/sessions")
                session.raise_for_status()
                headers = {"Authorization": "Bearer " + session.json()["token"]}
                # Optional context is an explicit additional user turn. Exact
                # supplied messages and their hashes remain unchanged.
                turns = list(case["turns"])
                if args.attachment_context and case.get("context_instruction"):
                    context = case["context_instruction"]
                    turns.insert(0, {"question": context, "question_sha256": digest(context.encode()), "origin": "attachment_context_instruction"})
                last_result = {}
                supplied_index = 0
                for index, turn in enumerate(turns, 1):
                    if turn["origin"] == "supplied":
                        supplied_index += 1
                    started = time.perf_counter()
                    payload = {"question": turn["question"], "audience": case["audience"]}
                    response = client.post("/v1/chat", headers=headers, json=payload)
                    elapsed = (time.perf_counter() - started) * 1000
                    result = response.json()
                    last_result = result
                    row = {"case_id": case["case_id"], "turn": index, "supplied_turn_index": supplied_index,
                           "question": turn["question"], "question_sha256": turn["question_sha256"],
                           "origin": turn["origin"], "http_status": response.status_code, "latency_ms": elapsed,
                           "response": result, "signals": task_shape_signals(case, result, supplied_index)}
                    if case["case_id"] == "cross-E" and supplied_index == 4:
                        row["interpretation"] = case["conditional_turn_note"]
                    captured.append(row)
                    # All predeclared scope must remain visible in this signal;
                    # do not replace it with whatever the parser recognized.
                    content_facets = case.get("turn_content_contracts", [case["expected_facets"]] * len(case["turns"]))[max(supplied_index - 1, 0)]
                    if turn["origin"] == "attachment_context_instruction":
                        content_facets = []
                    score_case = dict(case, expected_facets=content_facets, operation="comparison" if "comparison" in case["task_shape"] else case["task_shape"], declared_core=False)
                    score = score_response(score_case, result, records)
                    score["legacy_quote_only_signal"] = {k: score[k] for k in ("facet_coverage", "claim_support_flags")}
                    prepared_score = prepared_identity_signals(score_case, result, records, prepared_units, source_metadata, prepared_flags)
                    score["prepared_identity_signal"] = prepared_score
                    score["claim_support_method"] = "legacy_quote_only_signal plus separately measured exact trusted prepared identity; semantic support remains unknown"
                    score.update(turn=index, http_status=response.status_code, latency_ms=elapsed,
                                 contract_interpretation="Exact bound-facet engineering signal only; no clinical completeness inferred")
                    scores.append(score)
                    with (output / "responses.jsonl").open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                if args.viva_probe and case["task_shape"] in {"interactive_viva", "progressive_viva"}:
                    question = "My answer is that pineapple planets cause everything. I cannot explain the topic."
                    payload = {"question": question, "audience": case["audience"]}
                    question_id = (last_result.get("viva") or {}).get("question_id")
                    if question_id:
                        payload["viva_question_id"] = question_id
                    response = client.post("/v1/chat", headers=headers, json=payload)
                    probe = {"case_id": case["case_id"], "origin": "developer_authored_nonsense_learner_probe",
                             "question": question, "http_status": response.status_code, "response": response.json(),
                             "clinical_accuracy": None, "expected_behavior": "Do not award knowledge credit for irrelevant nonsense; any grading remains provisional."}
                    with (output / "viva-probes.jsonl").open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(probe, ensure_ascii=False) + "\n")
                cleanup = client.delete("/v1/sessions/current", headers=headers)
                cleanup.raise_for_status()
                print(f"{case['case_id']} supplied_turns={len(case['turns'])}", flush=True)
    verify_bank(args.bank)
    after, source_after = code_snapshot(), source_snapshot(args.release)
    summary = {"bank_version": verify_bank(args.bank)["version"], "manifest_sha256": digest((args.bank / "manifest.json").read_bytes()),
               "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
               "cases": len(cases), "captured_turns": len(captured), "configuration": {"network": False, "inference": "none", "answer_mode": "extractive", "attachment_context": args.attachment_context},
               "http_status_counts": dict(Counter(row["http_status"] for row in captured)),
               "coverage_status_counts": dict(Counter(str(row["response"].get("coverage_status")) for row in captured)),
               "source_set": source_before, "code_sha256": before,
               "code_after_sha256": after, "code_changed_during_run": before != after, "source_changed_during_run": source_before != source_after,
               "clinical_accuracy": None, "clinical_completeness": None, "independent_unseen": False,
               "qualified_review": "pending", "multi_turn_semantic_success": None,
               "interpretation": "Actual API captures with shared sessions for supplied turns. Bound-facet and structural signals require independent medical and conversation review."}
    summary["response_content_signals"] = {
               "turns_with_claims": sum(bool(row["response"].get("claims")) for row in captured),
        "complete_turns_with_claims": sum(row["response"].get("coverage_status") == "complete" and bool(row["response"].get("claims")) for row in captured),
        "complete_turns_without_claims": sum(row["response"].get("coverage_status") == "complete" and not row["response"].get("claims") for row in captured),
        "warning": "Complete may mean a viva activity started. These are observable response fields; do not count them as medically complete answers.",
    }
    summary["prepared_explanation_signals"] = {
        "trusted_prepared_units_in_release": len(prepared_units),
        "units_with_explicit_facet_bindings": sum(bool(unit.get("facet_bindings")) for unit in prepared_units),
        "turns_with_exact_trusted_prepared_claims": sum(bool(score["prepared_identity_signal"]["valid_claim_indices"]) for score in scores),
        "exact_trusted_prepared_claim_instances": sum(len(score["prepared_identity_signal"]["valid_claim_indices"]) for score in scores),
        "invalid_pointer_instances": sum(not check["valid"] for score in scores for check in score["prepared_identity_signal"]["mapping_checks"]),
        "distinct_trusted_prepared_ids_returned": sorted({check["prepared_id"] for score in scores
                                                          for check in score["prepared_identity_signal"]["mapping_checks"]
                                                          if check["valid"] and check["claim_index"] in score["prepared_identity_signal"]["valid_claim_indices"]}),
        "semantic_support": None, "clinical_correctness": None,
        "interpretation": "Paired explanation availability is distinct from raw quotation availability; exact trusted identity is not F03 review or medical correctness.",
    }
    summary["snapshot_status"] = "provisional_changed_during_capture" if before != after or source_before != source_after else "stable_during_capture"
    summary["responses_sha256"] = digest((output / "responses.jsonl").read_bytes())
    write_json(output / "scores.json", scores)
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "audit", "run"])
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--variations", action="store_true")
    parser.add_argument("--case", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--attachment-context", action="store_true")
    parser.add_argument("--viva-probe", action="store_true")
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify_bank(args.bank), indent=2))
    else:
        if args.output is None:
            parser.error("audit/run require a new --output directory")
        (audit if args.command == "audit" else run)(args)


if __name__ == "__main__":
    main()
