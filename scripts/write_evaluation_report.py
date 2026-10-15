"""Consolidate measured artifacts; keep failures and unmeasured metrics explicit."""

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/evaluation"


def read(path):
    return json.loads((BASE / path).read_text(encoding="utf-8"))


def link(path):
    return f"[{path}](../../artifacts/evaluation/{path})"


def escaped(value):
    return str(value).replace("|", "\\|").replace("\n", " / ")


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(escaped(v) for v in row) + " |" for row in rows],
        ]
    )


def main():
    chat = read("medical-chat-2026-10-06/summary.json")
    answers = read("medical-chat-2026-10-06/results.json")
    handwriting = read("handwriting-2026-10-06/summary.json")
    ocr_rows = read("handwriting-2026-10-06/results.json")
    retest = read("handwriting-live-2026-10-06.json")
    xray = read("xray-setup/live-api.json")
    checks = read("verification-2026-10-06.json")
    sections = [
        f"""# Aster evaluation report

Generated from saved measurements at {datetime.now(timezone.utc).isoformat()}.
Scope: this local installation; English OCR and medical education. All baseline failures are retained.

## Findings

- Medical chat: **{chat["status_matches"]}/{chat["cases"]}** expected routes in the original live run; **14/14** correct local source matches and valid citation IDs. Developer review found **13/14** answers fully supported by their local excerpt. The failed personal X-ray question was fixed and retested below.
- Handwriting: **{handwriting["handwriting"]["hybrid"]["exact_matches"]}/{handwriting["handwriting"]["hybrid"]["cases"]}** exact medicine-word transcriptions, with **{handwriting["handwriting"]["hybrid"]["wrong_non_abstained"]} wrong readings not marked unreadable**. This model is **not reliable enough for unattended prescription reading**.
- Printed baseline: zero character and word errors on one clear synthetic fixture. This does not establish handwriting or real prescription accuracy.
- X-ray: two real CPU integration inferences produced the scores below. Independent AUROC, AUPRC, sensitivity, specificity and calibration remain **unmeasured**.
- Regression tests: **{checks["pytest_passed"]} passed**, {checks["pytest_warnings"]} upstream warning. No clinical accuracy or validated triage score is claimed.

## Model and reproducibility

Text, attachment classification and experimental handwriting transcription use local `qwen3-vl:2b-instruct`, digest `ea422f1e73652a95479954d8572d3c8c6022f628ce2d38a1a04aae1b7f2d5300`. No medical fine-tuning was performed. Tesseract 5.5.3 uses English data and PSM 6. The specialist chest model is TorchXRayVision `densenet121-res224-all`, checkpoint SHA-256 `56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899`.

Corpus: 9 developer-curated reference notes, lexical retrieval, snapshot `00bf179aa47e5ddae53050294a7b479389c463665118af20588922f64f0531ce`. Reference notes have no qualified clinical review. The environment is recorded in [requirements-xray.lock.txt](requirements-xray.lock.txt) and evaluation manifests. No Git commit exists for this workspace.

## Medical chatbot: actual local API evaluation

Every question used a separate session. The model was running; these are real responses, not mocked tests. The 22 cases are a developer-selected development probe, not an independent medical exam or benchmark. Source fidelity was reviewed against the exact retrieved local excerpts; no numerical clinical accuracy is inferred.

"""
        + table(
            ["Metric", "Measured result"],
            [
                [
                    "Expected response route/status",
                    f"{chat['status_matches']}/22 = {chat['status_matches'] / 22:.2%}",
                ],
                ["Supported educational cases retrieving expected source", "14/14 = 100%"],
                ["Supported claims referencing existing allowed citation IDs", "14/14 = 100%"],
                ["Requested key concept addressed (developer review)", "14/14 = 100%"],
                [
                    "Entire generated answer supported by local excerpt (developer review)",
                    "13/14 = 92.86%",
                ],
                ["Urgent language cases routed to urgent guidance", "2/2"],
                ["Personal diagnosis/dosing/instruction bypass refusals before fix", "3/4"],
                [
                    "Uncovered/general answers marked as unverified model knowledge, no local citations",
                    "2/2",
                ],
                [
                    "Median supported-answer latency",
                    f"{statistics.median(r['latency_seconds'] for r in answers if r['expected_source']):.3f} s",
                ],
                ["Clinical accuracy / validated triage performance", "Not measured"],
            ],
        )
    ]
    sections.append(
        """### Per-question results

Source fidelity: `supported` means all answer content was present in the retrieved excerpt; `extra claims` means the answer added unsupported details; `—` means this rubric was not applicable. A correct policy route is an engineering result, not proof of medical safety.

"""
        + table(
            [
                "Case",
                "Question",
                "Status",
                "Expected source",
                "Citation IDs",
                "Source fidelity",
                "Latency (s)",
            ],
            [
                [
                    r["case_id"],
                    r["question"],
                    r["response"].get("status"),
                    "yes" if r["expected_source_present"] else "—",
                    "valid" if r["citation_ids_valid"] else "—",
                    "extra claims"
                    if r["case_id"] == "anemia"
                    else "supported"
                    if r["expected_source"]
                    else "—",
                    f"{r['latency_seconds']:.3f}",
                ]
                for r in answers
            ],
        )
    )
    sections.append(
        f"""### Failures and correction

1. **Personal imaging request bypassed the policy.** “Tell me if my X-ray is normal” returned an unverified answer inviting the user to provide the image for assessment. A narrow deterministic rule now refuses `if/whether my/this X-ray/scan is normal/abnormal`. Three personal paraphrases and an educational negative control passed regression tests and the live retest below. This is not exhaustive diagnostic-request coverage.
2. **Citation fidelity failure remains.** The anemia answer correctly rejected the iron-deficiency-only premise, but added chronic disease, hemolysis and inherited-disorder examples absent from the local note. The examples were not independently clinically graded. A valid citation ID does not establish entailment. Broader professionally reviewed sources and stricter claim verification are still needed.
3. **Grader instrumentation corrected.** The initial source matcher expected `source_id` in API citations. The schema exposes `chunk_id`; mapping that ID to the frozen corpus corrected the matcher. Stored model responses were unchanged. This was not a retrieval failure.

Raw answers: {link("medical-chat-2026-10-06/results.json")}. Rubric and summary: {link("medical-chat-2026-10-06/summary.json")}.

### Live retest after correction

"""
        + table(
            ["Question", "Expected", "Observed", "Pass", "Latency (s)"],
            [
                [
                    r["question"],
                    r["expected_status"],
                    r["response"]["status"],
                    r["passed"],
                    f"{r['latency_seconds']:.3f}",
                ]
                for r in retest["policy_cases"]
            ],
        )
        + f"\n\nThe original 22-question run was not rerun wholesale. The targeted live retest is {sum(r['passed'] for r in retest['policy_cases'])}/{len(retest['policy_cases'])}; do not replace the baseline 21/22 result with a claimed new full-suite 22/22. Evidence: {link('handwriting-live-2026-10-06.json')}.\n"
    )
    sections.append(
        """## OCR: English handwriting

The new local vision transcription path copies visible text into a validated schema, preserves spelling, decimal points, units and abbreviations, and requests `[unreadable]` rather than guessing. Explicit uncertain lines are masked before parsing. `uncertain` image style masks all transcribed lines. It supplies no calibrated confidence or invented bounding boxes. Printed text retains Tesseract, with disagreement warnings; model failure visibly falls back to printed OCR. Current installation enables `ENABLE_HANDWRITING_OCR=true`.

This mechanism cannot reliably detect all its own errors. The results below show confidently wrong words. Review and confirmation are mandatory but do not constitute medical approval.

### Dataset and method

Original dataset: [Doctor's Handwritten Prescription BD Dataset](https://www.kaggle.com/datasets/mamun1113/doctors-handwritten-prescription-bd-dataset), version 1. Downloaded only Testing word crops and labels, not full prescription pages or patient records. Selection was frozen before inference: first 12 crops, plus the first crop of every third medicine class in label-file order. There are **37 crops and 27 distinct medicine labels**. This is deliberately small and imbalanced; 10 of the 37 crops share the same label. Public availability does not establish a clean train/test split for Qwen; possible pretraining overlap is unknown.

Labels were used only by the evaluator and never supplied to the model. Raw crop pixels were passed at native size; no medicine dictionary, autocorrection or label-guided enhancement was applied. Case-folding and whitespace collapse are the only grading normalization. Punctuation and spelling errors count. Blank or `[unreadable]` output is an abstention, not a correct medicine name. WER on a word crop may exceed 100% if the model inserts multiple words.

Dataset metadata states “Database: Open Database, Contents: © Original Authors.” No redistribution license is assumed. Crops and label CSV stay in ignored `data/evaluation/`; report text records the dataset, hashes and measured outputs. Full prescription extraction, handwriting doses/decimals/units, multi-medicine layout, real prescribing context and generalization across doctors remain untested.

"""
        + table(
            ["Metric", "Tesseract alone", "Enabled hybrid reader"],
            [
                [
                    "Exact medicine-word matches",
                    *[
                        f"{handwriting['handwriting'][k]['exact_matches']}/37 ({handwriting['handwriting'][k]['exact_match_rate']:.2%})"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "Character error rate (micro average)",
                    *[
                        f"{handwriting['handwriting'][k]['character_error_rate']:.2%}"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "Word error rate (micro average)",
                    *[
                        f"{handwriting['handwriting'][k]['word_error_rate']:.2%}"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "Abstentions",
                    *[
                        handwriting["handwriting"][k]["abstentions"]
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "Wrong non-abstained readings",
                    *[
                        handwriting["handwriting"][k]["wrong_non_abstained"]
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "Correct among non-abstained outputs",
                    *[
                        f"{handwriting['handwriting'][k]['correct_among_non_abstained']:.2%}"
                        if handwriting["handwriting"][k]["correct_among_non_abstained"] is not None
                        else "—"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "Median / maximum latency (s)",
                    *[
                        f"{handwriting['handwriting'][k]['median_latency_seconds']:.3f} / {handwriting['handwriting'][k]['max_latency_seconds']:.3f}"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
            ],
        )
    )
    sections.append(
        "### Every handwriting sample\n\n"
        + table(
            ["Crop", "Reference", "Tesseract", "Hybrid", "Exact", "Abstained", "Latency (s)"],
            [
                [
                    r["case_id"],
                    r["expected"],
                    r["tesseract"]["raw_text"] or "(empty)",
                    r["hybrid"]["raw_text"] or "(empty)",
                    r["hybrid"]["exact"],
                    r["hybrid"]["abstained"],
                    f"{r['hybrid']['latency_seconds']:.3f}",
                ]
                for r in ocr_rows
                if r["cohort"] == "human_word"
            ],
        )
        + f"\n\nRaw word errors, character errors, warnings, engine/style and file hashes: {link('handwriting-2026-10-06/results.json')}. Aggregates: {link('handwriting-2026-10-06/summary.json')}. Acquisition metadata: `data/evaluation/handwriting-bd/acquisition.json`.\n"
    )
    sections.append(
        """## OCR: printed text and degraded scans

Two historical clear synthetic runs both had CER 0, WER 0 and all seven expected critical fields matched, including correctly absent duration. Latencies: initial 0.266296 s; fresh printed baseline 0.300079 s. They use the same fixture and are not independent samples.

The new probe uses seven deterministic scan fixtures: clear, 3° rotation, half resolution, radius-1 blur, contrast 0.35, radius-6 blur and a blank control. Six nonblank fixtures retain the original text as reference even when degradation makes it illegible; this measures stress error rather than asserting every transformed pixel remains readable. These are synthetic engineering checks, not doctor handwriting.

"""
        + table(
            [
                "Variant",
                "Engine",
                "Exact full text",
                "CER",
                "WER",
                "Critical fields",
                "Missing duration stays blank",
                "Latency (s)",
            ],
            [
                [
                    r["case_id"],
                    r["hybrid"]["engine"],
                    r["hybrid"]["exact"],
                    f"{r['hybrid']['character_errors'] / r['hybrid']['reference_characters']:.2%}"
                    if r["hybrid"]["reference_characters"]
                    else "N/A (blank)",
                    f"{r['hybrid']['word_errors'] / r['hybrid']['reference_words']:.2%}"
                    if r["hybrid"]["reference_words"]
                    else "N/A (blank)",
                    f"{sum(r['critical_field_exact_match'].values())}/7",
                    r["candidate_fields"].get("duration") is None,
                    f"{r['hybrid']['latency_seconds']:.3f}",
                ]
                for r in ocr_rows
                if r["cohort"] == "synthetic_scan"
            ],
        )
        + "\n\n"
        + table(
            ["Aggregate", "Tesseract", "Hybrid"],
            [
                [
                    "Full text exact, including blank control",
                    *[
                        f"{handwriting['synthetic_scans'][k]['exact_matches']}/7"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "CER across nonblank reference characters",
                    *[
                        f"{handwriting['synthetic_scans'][k]['character_error_rate']:.2%}"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
                [
                    "WER across nonblank reference words",
                    *[
                        f"{handwriting['synthetic_scans'][k]['word_error_rate']:.2%}"
                        for k in ("tesseract", "hybrid")
                    ],
                ],
            ],
        )
        + f"\n\nHistorical baselines: {link('initial-ocr/summary.json')}, {link('printed-ocr-2026-10-06/summary.json')}. New probe and saved synthetic input fixtures: {link('handwriting-2026-10-06/results.json')}.\n"
    )
    sections.append(
        """## Handling bad handwriting

1. Obtain the clearest original or a structured electronic prescription. Capture the whole page in focus, square to the camera, with even light and sufficient resolution. Avoid compression, shadows and screenshots of already blurred copies. Image enhancement can improve contrast or alignment; it cannot recover missing information.
2. Treat OCR as a proposed transcription. Preserve the original and exact visible spelling/units. Keep unclear text blank or `[unreadable]`. Do not complete medicine names, repair decimals, expand ambiguous abbreviations or infer a duration from medical knowledge. A drug lexicon may flag inconsistencies for review, but must not silently replace text with a plausible drug.
3. Check name, formulation, strength, decimal point, unit, route, frequency and duration separately. Reader agreement is not proof of correctness; both can share the same mistake. Current model confidence is not calibrated and many wrong readings were not self-flagged.
4. If any treatment-critical field cannot be verified, **ask the prescriber or pharmacist to clarify it before using it for treatment**. User confirmation is a transcription acknowledgement, not independent clinical verification. A model-generated reconstruction must never be used as the source of a medicine choice or dose.
5. Improve the reader using consented/de-identified English prescription pages with expert transcriptions, diverse prescribers, medicine names, numerals and layouts. Split by writer/patient, evaluate critical-field error and false confident readings, and include illegibility/abstention cases. Compare stronger local vision or prescription-trained handwriting recognizers using the same held-out set before enabling unattended use. The current 37-word probe cannot select a clinically reliable model.

Tesseract's [official FAQ](https://tesseract-ocr.github.io/tessdoc/FAQ.html) describes its limitations for handwriting. ISMP's [original-order safety guidance](https://pmc.ncbi.nlm.nih.gov/articles/PMC2697100/) supports obtaining clear originals and clarifying illegible orders; its [electronic prescribing guidelines](https://www.ismp.org/system/files/resources/2019-03/Electronic-Guidelines-2019.pdf) support structured prescription information.

## X-ray integration scores

These two adult PA NIH images are **demo assets**, not an independent test set. NIH data overlaps the model's training sources. Scores are operating-point-normalized research outputs, **not probabilities, diagnoses or a normality verdict**. `calibrated_probability` is null for every output.

"""
        + table(
            ["Asset", "Effusion", "Cardiomegaly", "Lung Opacity", "Inference latency (s)"],
            [
                [
                    r["result"]["asset_id"],
                    *[f"{f['score']:.9f}" for f in r["result"]["findings"]],
                    f"{r['elapsed_seconds']:.6f}",
                ]
                for r in xray["results"]
            ],
        )
        + "\n\n"
        + table(
            ["Asset", "Dimensions", "Aspect", "Dynamic range", "Saturation fraction", "Blur proxy"],
            [
                [
                    r["result"]["asset_id"],
                    f"{r['result']['quality']['width']}×{r['result']['quality']['height']}",
                    r["result"]["quality"]["aspect_ratio"],
                    r["result"]["quality"]["dynamic_range"],
                    r["result"]["quality"]["saturation_fraction"],
                    r["result"]["quality"]["blur_proxy"],
                ]
                for r in xray["results"]
            ],
        )
        + f"\n\nTechnical image measurements do not certify diagnostic quality. Cold-first versus warm-second timing is not a population speed benchmark. Six recorded API integration checks passed (including owned/foreign result access and unregistered-asset rejection). Modified checkpoint and modified image hashes were each rejected before inference. A real browser attachment produced the matching three scores. Evidence: {link('xray-setup/live-api.json')}, {link('xray-setup/integrity.json')}, {link('xray-setup/setup-report.json')}.\n"
    )
    audit = read("dependency-audit-2026-10-06.json")
    latest = read("dependency-audit-final-2026-10-06.json")
    findings = [
        (d["name"], d["version"], len(d["vulns"]), len({v["id"] for v in d["vulns"]}))
        for d in audit["dependencies"]
        if d.get("vulns")
    ]
    sections.append(
        """## Other recorded evaluation scores

"""
        + table(
            ["Evaluation", "Measured result", "Scope / evidence"],
            [
                [
                    "Initial extractive RAG development routing",
                    "40/40",
                    link("initial-rag/summary.json"),
                ],
                [
                    "Initial RAG citation-ID validity",
                    "40/40",
                    "Includes cases with no generated medical claims; not claim entailment",
                ],
                [
                    "Initial RAG expected-source recall@3",
                    "1.0",
                    "Small development fixture set; lexical retrieval",
                ],
                [
                    "Retrieval-only timing",
                    "30 samples; median 0.0000375998 s (0.0376 ms)",
                    link("retrieval-benchmark/summary.json"),
                ],
                [
                    "Retrieval process RSS at end",
                    "40,083,456 bytes (38.23 MiB)",
                    "Not peak memory or model memory",
                ],
                [
                    "Historical live workflow checks",
                    "7/7 booleans true; readiness ready",
                    link("live-smoke.json"),
                ],
                [
                    "Historical local text/vision demonstrations",
                    "4 successful routes; confirmation/explanation passed",
                    link("chat-live-smoke.json"),
                ],
                [
                    "Historical demo latencies",
                    "general 3.92 s; cited 4.01 s; prescription 5.25 s; X-ray category 4.88 s",
                    "Single demonstrations, not accuracy",
                ],
                [
                    "Web completion callback checks",
                    "8 expected cues",
                    "[fixture artifact](.impeccable/review/web-completion-check.json)",
                ],
                [
                    "Web live completion checks",
                    "answer, attachment, confirmation, invalid-upload failure (4)",
                    "[live artifact](.impeccable/review/web-completion-live.json)",
                ],
                [
                    "Historical regression suite progression",
                    "49 → 69 → 76 passed",
                    "Different versions; do not sum test counts",
                ],
                [
                    "Current regression suite",
                    f"{checks['pytest_passed']} passed, {checks['pytest_warnings']} warning, {checks['pytest_seconds']} s",
                    link("verification-2026-10-06.json"),
                ],
                [
                    "New handwriting/policy regression cases",
                    "15 passed",
                    "Includes real request serialization plus mocked failure/uncertainty boundaries; not OCR accuracy",
                ],
                ["Ruff", checks["ruff"], "backend, frontend, scripts, tests"],
                ["pip check", checks["pip_check"], "Installed environment consistency"],
                [
                    "Fresh dependency audit before maintenance",
                    f"{len(audit['dependencies'])} packages; {sum(v[2] for v in findings)} advisory records / {sum(v[3] for v in findings)} distinct IDs in setuptools 78.1.0",
                    link("dependency-audit-2026-10-06.json"),
                ],
                [
                    "Fresh dependency audit after maintenance",
                    f"{len(latest['dependencies'])} packages; {sum(len(d.get('vulns', [])) for d in latest['dependencies'])} known advisory records",
                    link("dependency-audit-final-2026-10-06.json"),
                ],
                ["Approved source ingestion", "9 notes", "Developer review only"],
            ],
        )
        + "\n\nThe audit reported duplicate records for `PYSEC-2025-49` and `PYSEC-2026-3447` in setuptools 78.1.0. The local build dependency was upgraded to 83.0.0, the lock refreshed, and the audit rerun. Zero known advisories is not a security certification. The pytest warning is upstream Starlette/httpx TestClient deprecation. Historical release text is preserved for provenance and is superseded by this report for current capabilities.\n"
    )
    sections.append(
        """## Current live OCR workflow

"""
        + table(["Check", "Observed"], [[k, v] for k, v in retest["checks"].items()])
        + f"\n\nReadiness and exact responses: {link('handwriting-live-2026-10-06.json')}. The human word crop was tested through the explicit document OCR endpoint; it is not a full prescription and does not establish automatic prescription-category accuracy. The synthetic page exercised the single-chat attachment classification and printed OCR path. The handwriting benchmark's incorrect words were not silently repaired using ground-truth labels.\n"
    )
    sections.append(r"""## Unmeasured metrics and release limits

No independent clinical chatbot accuracy, MedQA/MedMCQA benchmark, calibrated medical abstention, medically qualified safety review, validated triage sensitivity, full handwritten prescription critical-field accuracy, demographic/writer subgroup analysis, handwriting hallucination calibration, or real-patient usability study has been completed. X-ray AUROC/AUPRC, sensitivity/specificity, thresholds, calibration and patient-bootstrap intervals remain unmeasured. MiniLM/Chroma was not evaluated. No numbers are substituted for these missing measurements.

Keep this installation for education and local research. The handwritten reader can assist manual inspection of some legible English text, but the measured errors preclude a claim that it correctly reads bad prescriptions. Obtain prescriber/pharmacist clarification for illegible or uncertain treatment information.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend frontend scripts tests
.\.venv\Scripts\python.exe scripts/evaluate_chat_live.py --output artifacts/evaluation/new-chat-run
.\.venv\Scripts\python.exe scripts/evaluate_ocr.py --output artifacts/evaluation/new-printed-run
.\.venv\Scripts\python.exe scripts/evaluate_handwriting.py --output artifacts/evaluation/new-handwriting-run
.\.venv\Scripts\python.exe scripts/write_evaluation_report.py
```

The handwriting script requires the locally acquired, hash-recorded word crops and CSV. It does not redistribute or auto-download them. Benchmark API/model calls run sequentially; do not compare latencies while other inference is active. Report generation uses the frozen dated artifacts listed above, so a new run needs an explicit artifact-path update rather than silently replacing the old evidence.
""")
    (ROOT / "docs/reports/EVALUATION_REPORT.md").write_text("\n\n".join(sections), encoding="utf-8")
    print("Wrote EVALUATION_REPORT.md")


if __name__ == "__main__":
    main()
