"""Render the expanded library report from saved evaluation measurements."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/evaluation/netmeds-v2-final"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    summary = read(OUT / "summary.json")
    retrieval_summary = read(ROOT / "artifacts/evaluation/netmeds-v2-final-retrieval/summary.json")
    audit = read(ROOT / "data/knowledge_v2/netmeds_import_audit.json")
    verified = read(ROOT / "data/knowledge_v2/netmeds_import_verification.json")
    checks = read(OUT / "engineering-checks.json")
    smoke = read(OUT / "api-smoke.json")
    index = read(ROOT / "data/indexes/aster-v2-netmeds-r2-2026-10-07/manifest.json")
    assert not summary.get("run_error"), summary.get("run_error")
    assert not retrieval_summary.get("run_error"), retrieval_summary.get("run_error")
    assert not verified["uncovered_nonwhitespace_ranges"]
    assert all(row["passed"] for row in smoke["results"])
    rows = [
        "# Aster Indian retailer library — evaluation",
        "",
        "Release **aster-v2-netmeds-r2-2026-10-07**, report date **2026-10-07**. "
        "The user confirmed verification/licensing and explicitly authorized clinical-library use. "
        "Source metadata preserves this as user attestation, distinct from developer integrity checks and qualified clinical review. "
        "**Clinical accuracy is not measured; qualified clinical review has not been performed.**",
        "",
        "## Coverage and source preservation",
        "",
        "| Measure | Recorded value |",
        "|---|---:|",
        f"| Combined reference sections | {index['records']:,} |",
        f"| Combined source documents | {index['documents']:,} |",
        f"| Retailer products | {index['retailer_products']:,} |",
        f"| Retailer sections | {index['retailer_sections']:,} |",
        f"| Clinical retailer source-text chunks | {audit['counts']['clinical_source_chunks']:,} |",
        f"| Identity-only products | {audit['counts']['identity_only_documents']:,} |",
        f"| Missing description / generic field | {audit['counts']['missing_description']} / {audit['counts']['missing_generic']} |",
        f"| Maximum section characters | {verified['max_chunk_chars']} |",
        "| Verbatim source-span / identity checks | Passed / passed |",
        "| Unaudited non-whitespace source gaps | 0 |",
        "",
        "Product counts include retailer products, not necessarily distinct drugs. Section counts do not establish complete clinical coverage. "
        "All 23,939 rows have identities; 3,802 only have identity evidence because description extraction could not safely produce clinical sections. "
        "Retailer purposes/mechanisms/warnings/side effects/interactions are secondary source information, not manufacturer-approved Indian labeling. "
        "Source errors, spelling corruption and historical update dates are preserved. Prices and current availability are not served as facts.",
        "",
        "Excluded source units are explicitly recorded. Directions/self-treatment, management/storage, source bibliography/author boilerplate, "
        "diagnostic lists, unrecognized layouts and unsplittable qualified units are not silently truncated into clinical claims. "
        "The complete CSV remains local audit material. Recorded exclusions:",
        "",
    ]
    rows += [f"- `{key}`: {value:,}" for key, value in audit["exclusion_counts"].items()]
    rows += [
        "",
        "## Retrieval development benchmark",
        "",
        f"Deterministic sampling selected {summary['sampling']['product_rows']} product rows. "
        "Product fixtures use exact released identities and available source sections. "
        "A top-three source hit is separate from retrieving the expected section. These are development fixtures, not held-out clinical validation.",
        "",
        "| Group | Lexical | Active hybrid |",
        "|---|---:|---:|",
    ]
    groups = retrieval_summary["retrieval"]
    for group in ("product", "common_brand", "regression", "identity_gates"):
        left, right = groups["lexical"][group], groups["hybrid"][group]
        rows.append(f"| {group.replace('_', ' ')} — expected source/abstention | {left['hit_at_3']}/{left['cases']} | {right['hit_at_3']}/{right['cases']} |")
        if group == "product":
            rows.append(f"| Product expected-section hits | {left['section_hits']}/{left['section_cases']} | {right['section_hits']}/{right['section_cases']} |")
            rows.append(f"| Median product retrieval latency | {1000*left['median_latency_seconds']:.2f} ms | {1000*right['median_latency_seconds']:.2f} ms |")
    rows += [
        "",
        "Common-brand fixtures include appropriate insufficient-evidence cases for unsupported formulations, so their hit count is not universal drug coverage. "
        "Shared retailer aliases abstain unless an applicable exact product is resolved. "
        "Retailer records are deliberately excluded from semantic identity inference: they use an inverted identity index and lexical source-section ranking. "
        "The original 250 curated sections retain the pinned MiniLM vectors; all combined records are still checksum/provenance validated.",
        "",
        "### Compared with original v2 retrieval",
        "",
    ]
    for backend, comparison in retrieval_summary["baseline_comparison"]["backends"].items():
        rows.append(f"- {backend}: {comparison['previous_hits']}/{comparison['comparable_cases']} prior hits → {comparison['current_hits']}/{comparison['comparable_cases']} current hits; lost {comparison['lost_hits']}; gained {comparison['gained_hits']}.")
    rows += [
        "",
        "Raw retrieval results record remaining misses and expected-section failures. Scores describe retrieval behavior, not medical correctness or completeness.",
        "",
        "## Live Qwen and application checks",
        "",
        "| Check | Recorded value |",
        "|---|---:|",
    ]
    live = summary["live"]
    gates = summary["offline_gates"]
    rows += [
        f"| Offline expected response statuses | {gates['route_correct']}/{gates['cases']} |",
        f"| Live expected response statuses | {live['route_correct']}/{live['cases']} |",
        f"| Complete served source-section support | {live['complete_section_supported']}/{live['source_backed_cases']} cited cases |",
        f"| Actual model calls / generation-call errors | {live['model_calls']} / {live['model_call_errors']} |",
        f"| Running UI → API checks | {sum(row['passed'] for row in smoke['results'])}/{len(smoke['results'])} |",
        f"| Automated tests | {checks['pytest']['passed']} passed, {checks['pytest']['failed']} failed |",
        "| Ruff / pip dependency consistency / JavaScript syntax | Passed |",
        "",
        f"Live answer methods: `{json.dumps(live['answer_methods'], sort_keys=True)}`. "
        "Generation failures and unsupported wording can trigger source-bound extractive fallback. "
        "Full-section support requires the complete cited text, not just a matching citation ID. "
        "It is a deterministic text-preservation check, not a medical entailment or clinical-accuracy measure. "
        "Uncited abstentions are not counted as source-backed successes.",
        "",
        f"Live failures: `{live['failures']}`. Automated tests took {checks['pytest']['seconds']} seconds and emitted one existing Starlette/httpx deprecation warning. "
        "The actual-app smoke checked Dolo 650 purpose, Ascoril LS Expectorant purpose, Ketocip Shampoo purpose and missing warnings, ambiguous Cyclopam, "
        "missing Dolo interaction evidence, Dolo 500-milligram mismatch and personal dosing. Its session was deleted after testing.",
        "",
        "## Review fixes and historical pilot",
        "",
        "Review reproduced wrong-form/route evidence, shared aliases mixing products, pack volume mistaken for drug strength, "
        "and ignored spelled-out units. These were fixed with failing-then-passing regression tests. "
        "The focused reviewer rechecked 16 real CSV products and 172 chunks; all 11 assertions passed with no remaining blocker in those findings. "
        "Full names containing several form words were also fixed: qualifiers are checked outside the exact matched identity. "
        "Unknown concentrations and incompatible extra routes/forms/strengths still abstain.",
        "A subsequent missing-section check found Dolo interaction questions retrieving unrelated purpose text. "
        "A dedicated regression test now requires insufficient evidence when the requested clinical section is absent. "
        "Retrieval scores above use a fresh run after that fix; the live model evaluation predates it, and the actual-app smoke checks the corrected behavior.",
        "",
        "The initial r2 pilot is retained in `artifacts/evaluation/netmeds-v2-r2/`: 119/185 product hits and 14/15 live expected statuses before the full-name form-word fix. "
        "The final measurements above rerun the same sample after that fix. The first unactivated release is preserved as historical build evidence. "
        "No historical v2 score or failed pilot was overwritten.",
        "The initial app smoke had one incorrect expectation: it expected an answer about Ketocip Shampoo warnings despite that entry having only identity/introduction sections. "
        "Its appropriate insufficient-evidence response is retained in `api-smoke-initial.json`. "
        "The corrected smoke checks both its supported purpose and missing warnings; production behavior was not weakened to satisfy the test.",
        "",
        "## Reproducibility and limits",
        "",
        f"- CSV SHA-256: `{audit['snapshot_sha256']}`.",
        f"- Combined corpus snapshot: `{index['snapshot_hash']}`.",
        f"- Semantic vector SHA-256: `{index['vectors_sha256']}`; {index['semantic_records']} × {index['dimension']} vectors.",
        f"- MiniLM revision: `{index['embedding_revision']}`.",
        f"- Local Qwen model: `{live['model']['model']}`, digest `{live['model']['digest']}`.",
        "",
        "[Raw retrieval](artifacts/evaluation/netmeds-v2-final-retrieval/retrieval.json), "
        "[latest retrieval summary](artifacts/evaluation/netmeds-v2-final-retrieval/summary.json), "
        "[live responses](artifacts/evaluation/netmeds-v2-final/live-results.json), "
        "[summary](artifacts/evaluation/netmeds-v2-final/summary.json), "
        "[actual app smoke](artifacts/evaluation/netmeds-v2-final/api-smoke.json), "
        "[engineering checks](artifacts/evaluation/netmeds-v2-final/engineering-checks.json), "
        "[run manifest](artifacts/evaluation/netmeds-v2-final/run-manifest.json), "
        "[source-span verification](data/knowledge_v2/netmeds_import_verification.json).",
        "",
        "Aster remains an educational/research assistant. Personal dosing, diagnosis and urgent-care gates are preserved. "
        "The dataset was not used to fine-tune Qwen or repair handwritten prescriptions. OCR and X-ray models/evaluation remain unchanged. "
        "See [the integration guide](NETMEDS_CLINICAL_LIBRARY.md) for exact names, provenance, exclusions and rollback to the original v2.",
    ]
    destination = ROOT / "NETMEDS_CLINICAL_LIBRARY_EVALUATION.md"
    destination.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
