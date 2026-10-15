"""Publish measured audit results without inferring medical correctness."""

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/evaluation/comprehensive-v1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def link(label, path):
    return f"[{label}](<{Path(path).resolve().as_posix()}>)"


def fraction(number, total):
    return f"{number}/{total} ({number / total:.1%})" if total else "Not assessed"


def write():
    full = read(ART / "all-curricula-v3/summary.json")
    concept = read(ART / "all-concepts-v1/summary.json")
    if full["cases"] != 9144 or concept["cases"] != 3048 or not full["runtime_unchanged"] or not concept["runtime_unchanged"]:
        raise ValueError("Incomplete or superseded curriculum evaluation")
    full_rows = read(ART / "all-curricula-v3/answers.json")["cases"]
    concept_rows = read(ART / "all-concepts-v1/answers.json")["cases"]
    by_item = {}
    for row in full_rows:
        by_item.setdefault(row["curriculum_id"], []).append(row)
    gaps_path = ART / "curriculum-gap-register-v2.csv"
    with gaps_path.open("x", encoding="utf-8-sig", newline="") as handle:
        columns = ["curriculum_id", "programme", "subject", "title", "kind", "concept_handled",
                   "complex_prompts_handled", "complex_prompts", "observed_assessment_required",
                   "priority", "faculty_accuracy", "concept_source_urls"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in concept_rows:
            handled = row["evaluation"]["handled"]
            complex_handled = sum(x["evaluation"]["handled"] for x in by_item[row["curriculum_id"]])
            writer.writerow({**{key: row.get(key) for key in columns if key in row},
                             "concept_handled": handled, "complex_prompts_handled": complex_handled,
                             "complex_prompts": len(by_item[row["curriculum_id"]]), "faculty_accuracy": "",
                             "concept_source_urls": " | ".join(sorted({x["url"] for x in (row.get("answer") or {}).get("citations", [])})),
                             "priority": ("Review acquisition, extraction and question interpretation" if not handled else
                                          "Review question framing, case/viva reasoning and completeness" if not complex_handled else
                                          "Independent correctness and completeness review pending")})
    mbbs, mds = (read(ART / name) for name in ("mbbs-focused-final.json", "mds-focused-final.json"))
    photo = read(ART / "mds-photo-topics-final.json")
    ocr = read(ART / "ocr-printed/summary.json")
    handwriting = read(ART / "ocr-handwriting/summary.json")
    xray = read(ART / "xray-integration/summary.json")
    medicines = read(ART / "active-medicine-regression/summary.json")
    live_path = max(ART.glob("live-api-*.json"))
    live = read(live_path)
    profile = read(ROOT / "configs/comprehensive_teaching_profile.json")
    release = ROOT / profile["TEACHING_RELEASE_PATH"]
    notes = read(release / "explanations.json")
    manifest = read(release / "manifest.json")
    test_log = (ART / "pytest-delivery.log").read_text(encoding="utf-8")
    test_result = re.search(r"(\d+) passed, (\d+) warning", test_log)
    if not test_result or "failed" in test_log:
        raise ValueError("Final software verification missing or failed")
    packs = [ART / "faculty-curriculum-pack", ART / "faculty-concept-pack"]
    for path, expected in zip(packs, (9144, 3048), strict=True):
        pack = read(path / "manifest.json")
        if pack["cases"] != expected or pack["qualified_human_accuracy"] is not None:
            raise ValueError("Human review pack not ready or falsely scored")
    lines = ["# Aster comprehensive audit — 9 October 2026", "",
             "**Aster is not yet a comprehensive, clinically validated MBBS/MDS tutor.** This audit fixes reproduced defects, expands the licensed library, and tests every item in the current inventory. It does not close every content, question-understanding or reasoning gap. No qualified faculty review has been performed.", "",
             "## Scope and limits", "",
             "The register contains 306 MDS Oral and Maxillofacial Pathology and Oral Microbiology items, 2,626 active numbered MBBS competencies across 19 subjects, and 116 supplemental objectives. It preserves the 89 photographed topics. The 9,144 complex prompts are three correlated development templates per inventory item; 3,048 additional short concept prompts help distinguish breadth and question-framing problems. These are not independent examination items or validated medical answer keys.", "",
             "The broad runs exercise TeachingStore directly. They do not measure the language model's unrestricted medical knowledge or every full-application answer. Separate live chat, medicine, OCR and X-ray runs test those pathways. A handled answer and matching citation can still be wrong, incomplete or unrelated.", "",
             "Official scope is pinned to the detailed 2019 dental amendment and the NMC 2024 CBME curriculum/clarification, rechecked against current publisher listings. Pediatric summary/table counts do not reconcile; missing/malformed competency codes remain explicit. This is a full pass over the extracted inventory, not independently certified complete curriculum extraction. Written tests cannot demonstrate clinical, practical, communication or laboratory competence.", "",
             link("Curriculum sources, page references and extraction discrepancies", ART / "curriculum-review-guide.md"), "",
             "## Measured curriculum results", "",
             "These percentages measure **answer handling**, not medical accuracy or curriculum mastery.", "",
             "| Programme | Complex prompts handled | Short concepts handled |",
             "|---|---:|---:|"]
    for group in ("all", "MDS", "MBBS"):
        a, b = full["groups"][group], concept["groups"][group]
        lines.append(f"| {group} | {fraction(a['handled'], a['cases'])} | {fraction(b['handled'], b['cases'])} |")
    lines += ["", f"Short concept probes returned no answer for {concept['cases'] - concept['groups']['all']['handled']:,} inventory items. Complex probes returned no answer for {full['cases'] - full['groups']['all']['handled']:,} prompts. Long instructional framing, compound questions, incomplete extraction, conservative matching and missing content can all contribute; a failed query is not by itself proof that the concept is absent from the source files.", "",
              "| Subject / scope | Short concepts handled | Complex prompts handled |",
              "|---|---:|---:|"]
    for group, value in concept["groups"].items():
        if ":" in group:
            complex_value = full["groups"][group]
            lines.append(f"| {group.replace('|', '/')} | {fraction(value['handled'], value['cases'])} | {fraction(complex_value['handled'], complex_value['cases'])} |")
    claims = sum(row["evaluation"]["emitted_claims"] for row in full_rows + concept_rows)
    bound = sum(row["evaluation"]["bound_claims"] for row in full_rows + concept_rows)
    lines += ["", f"Emitted-claim text binding: {fraction(bound, claims)}. This verifies exact source text or an explicitly paired developer note; it is **not semantic proof or clinical correctness**. Query embeddings were batched using the same pinned model, with individual/batch agreement checked; ranking thresholds were not relaxed. Both final runs retain unchanged runtime/input hashes.", "",
              link("Every inventory item and its open-gap priority", gaps_path), "",
              link("Complex question results, full answers and source metadata", ART / "all-curricula-v3/answers.json"), "",
              link("Short concept results and source metadata", ART / "all-concepts-v1/answers.json"), "",
              "## Focused developer regression tests", "",
              "| Check | Result | Meaning |", "|---|---:|---|",
              f"| MBBS expected routing | {fraction(sum(row['status_pass'] for row in mbbs['results']), mbbs['cases'])} | Expected status, not correctness |",
              f"| MBBS expected-source hit | {fraction(sum(bool(row['retrieval_source_hit']) for row in mbbs['results'] if row['retrieval_source_hit'] is not None), mbbs['metrics']['retrieval_source_hit']['denominator'])} | Developer-selected source fixture |",
              f"| MBBS expected fact-phrase mean | {mbbs['metrics']['fact_completeness']['mean']:.1%} across {mbbs['metrics']['fact_completeness']['denominator']} questions | Limited phrase coverage, not complete medical facts |",
              f"| MBBS full developer-reference agreement | {fraction(sum(bool(row['reference_agreement_pass']) for row in mbbs['results'] if row['reference_agreement_pass'] is not None), mbbs['metrics']['reference_agreement_pass']['denominator'])} | Source/fact fixture agreement, not medical accuracy |",
              f"| MDS focused expected routing | {fraction(sum(row['status_pass'] for row in mds['results']), mds['cases'])} | Includes six boundaries |",
              f"| MDS focused developer-reference agreement | {fraction(sum(bool(row['reference_agreement_pass']) for row in mds['results'] if row['reference_agreement_pass'] is not None), mds['metrics']['reference_agreement_pass']['denominator'])} | Small development set |",
              f"| Original photographed topic handling | {fraction(photo['runtime_statuses'].get('ok', 0), photo['topic_count'])} | Partial answers can count |",
              f"| Actual local chat bridge | {fraction(live['status_passes'], live['cases'])} | Routing/identity/boundary checks; temporary session deleted |", "",
              "The old fact/source rubrics were shown to pass some faulty or irrelevant copied passages. They are retained as engineering regressions with this limitation, not renamed as faculty medical-accuracy scores. Preventing a faulty source from appearing can lower reference/fact metrics. The remaining fact gaps need independent reference checks and deeper explanations.", "",
              "## Fixes and library changes", "",
              f"The active immutable teaching release is `{manifest['version']}`: {manifest['records']:,} sections, {manifest['sources']} source units, {len(notes['units'])} paired plain-language explanations and {len(notes['source_review_flags'])} source restrictions. It preserves the original 2,705 records and adds 101 foundation contexts plus 110 contexts from seven licensed narrative reviews. A restriction can suppress a raw passage completely or permit only a bounded paired explanation; it is not faculty approval.", "",
              "- Embedded release checksums now keep review holds active even if a profile omits the separate notes checksum.",
              "- Bibliography/navigation paragraphs and generic research-method passages are blocked from answering concept questions.",
              "- Comparisons retain the parent question's drug-metabolism scope. Nutritional metabolism and transfusion mentions no longer substitute for the reproduced drug-metabolism and vessel-anatomy queries.",
              "- Added British/Indian spelling aliases and bounded pharmacokinetic explanations; fixed the two reproduced free-drug/metabolism cases against their source passages.",
              "- Expanded emergency and personal-treatment checks for the reproduced choking, unilateral weakness, poison ingestion, antibiotic selection and child-dose variants. These language checks remain unvalidated triage.",
              "- Paired explanations are no longer padded with raw textbook paragraphs for viva wording. Unpaired topics still use extractive passages; conversational depth across the whole curriculum remains incomplete.",
              "- Cached pure term/scope computations by content to reduce retrieval overhead; changed content invalidates cached source-safety checks. Source thresholds and permissions remain enforced.",
              "- Rebound holds when a component version changed chunk identities; matching/superseded context provenance is recorded. An absent identity cannot silently drop a hold.", "",
              "The checks found errors involving penetrance/expressivity, integrins, insulin uptake absolutes, implant junctional epithelium, variance/covariance, antigenicity/immunogenicity, outdated viral/fungal taxonomy, blood typing, CFTR transport, haemostasis, tongue muscles, cementum and nerve anatomy. Specialty passages also reversed a screening result and a mouse experimental intervention. Identified raw contexts are held rather than silently rewritten as verified facts. The specialty source check is partial; whole-source and medical correctness remain unestablished.", "",
              link("Original answer/source quality audit", ART / "independent-quality-audit.md"), "",
              link("New foundation source review", ART / "new-foundation-quality-review.md"), "",
              link("Specialty holds and primary counterevidence", ROOT / "configs/audit_specialty_holds.json"), "",
              link("Acquisition licenses, snapshots and excluded material", ROOT / "data/references/mds/raw/audit-foundations/ACQUISITION_REPORT.md"), "",
              "## Medicine evaluation", "",
              "The current primary medicine release was evaluated separately using a deterministic 60-product sample, named-brand, identity-gate and general-reference cases. This is not a medical review of all 23,939 retailer products. Retailer licence/verification remains user-attested; secondary Indian notes remain explicitly unverified. Ingredient, route, strength and product identity must not be silently interchanged.", "",
              "| Backend / group | Expected retrieval hits | Requested-section hits |",
              "|---|---:|---:|"]
    for backend, groups in medicines["retrieval"].items():
        for group, score in groups.items():
            lines.append(f"| {backend} / {group} | {fraction(score['hit_at_3'], score['cases'])} | {fraction(score['section_hits'], score['section_cases'])} |")
    for name in ("extractive", "responses", "live"):
        if name in medicines:
            lines += ["", f"Additional `{name}` measurements are in the full medicine summary; generation and extractive fallback are distinguished there."]
    if medicines.get("live"):
        model = medicines["live"]
        lines += ["", f"The local model run had {model['route_correct']}/{model['cases']} expected routes, {model['model_calls']} model calls and {model['model_call_errors']} model-call errors. All {model['source_backed_cases']} source-backed answers used verified extractive fallback ({model['answer_methods']}); this does not establish successful model-generated medical explanations. The guard contained the failures, but model-format/grounding and fluent explanation gaps remain."]
    lines += ["", link("Current medicine pipeline results, failures and model execution", ART / "active-medicine-regression/summary.json"), "",
              "## OCR and X-ray", "",
              "| Test | Result | Limit |", "|---|---:|---|",
              f"| Printed OCR | CER {ocr['character_error_rate']:.1%}; WER {ocr['word_error_rate']:.1%}; {sum(ocr['critical_field_exact_match'].values())}/{len(ocr['critical_field_exact_match'])} critical fields exact | {ocr['cases']} synthetic printed prescription |"]
    for engine in ("tesseract", "hybrid"):
        result = handwriting["handwriting"][engine]
        lines.append(f"| English word crops / {engine} | Exact {fraction(result['exact_matches'], result['cases'])}; CER {result['character_error_rate']:.1%}; WER {result['word_error_rate']:.1%}; wrong non-abstained {result['wrong_non_abstained']} | 37 development crops, 27 unique labels; not full doctor prescriptions |")
    lines += [f"| Hybrid synthetic scan variants | {fraction(handwriting['synthetic_scans']['hybrid']['exact_matches'], 7)} exact | Seven engineering variants including blank control |",
              f"| X-ray model integration | {xray['assets']} demo assets / {xray['patients']} patients; diagnostic metrics null | Not independent or clinical validation |", "",
              "The hybrid handwriting reader produced 27 wrong non-abstained readings in 37 word crops. It is not dependable for difficult handwritten prescriptions. Every extracted prescription requires confirmation before explanation; uncertain text remains unreadable, and names, strengths, decimals and instructions need checking with the original and prescriber/pharmacist. Dictionary correction or two readers agreeing does not establish the intended medicine. Improved recognition needs consented representative full-prescription data, independent human transcription and separate evaluation of critical-field errors/abstention. These missing data are not manufactured by this audit.", "",
              "X-ray diagnostic accuracy, sensitivity, specificity, calibration and external generalization remain unmeasured. The two demo images verify preprocessing/checkpoint integration only. An independent labelled dataset with documented training-overlap exclusion and expert review is still required.", "",
              link("Printed OCR results", ART / "ocr-printed/summary.json"), " · " + link("Handwriting results and actual errors", ART / "ocr-handwriting/results.json"), " · " + link("X-ray integration and withheld metrics", ART / "xray-integration/summary.json"), "",
              "## Faculty review pack", "",
              "No reviewer is available, so all faculty accuracy scores remain null. Two randomized, blinded packs contain the actual module outputs, source passages/attribution and independent-reference rubrics. They distinguish emitted answers from abstentions; absent answers cannot receive invented medical-accuracy/reference-agreement scores. Qualifications and CSV attestations require external verification even after scores are entered.", "",
              link("Complex curriculum pack rubric — 9,144 entries", packs[0] / "rubric.md"), "",
              link("Complex pack blank scores", packs[0] / "scores-blank.csv"), "",
              link("Concept pack rubric — 3,048 entries", packs[1] / "rubric.md"), "",
              link("Concept pack blank scores", packs[1] / "scores-blank.csv"), "",
              "Keep each private-case-key file separate from blinded reviewers. Reviewers should use independent current references and work only within their qualifications. Send no real patient data. Import only personally completed assessments using `scripts/curriculum_audit.py import-scores`; do not fill pending cells with zeros or simulated faculty identities. Practical competencies need an observed assessment plan in addition to written review.", "",
              "## Verification and remaining work", "",
              f"Software verification: {test_result[1]} tests passed with {test_result[2]} existing Starlette/httpx deprecation warning. Ruff passes, pip reports no broken requirements, and the frontend JavaScript syntax check passes. These checks and actual runtime validation are recorded in the delivery ledger. No software pass rate is a medical-accuracy score. Earlier interrupted broad runs and rejected checksum attempts are retained as superseded evidence, not included in final scores.", "",
              "The largest unresolved gaps are full clinical-subject coverage, long/composite question interpretation, source-supported case/viva reasoning, complete patient-friendly explanations, independent current-reference answer keys, faculty review, observed practical assessment, full handwritten-prescription recognition and independent X-ray performance. The gap register gives every inventory item a triage priority. Closing these requires further reviewed material and human assessment; this release does not claim that every MBBS/MDS question can be answered.", "",
              "The corrected local profile is active at http://127.0.0.1:8501. The original medicine/model `.env` remains unchanged; an activation ledger records the previous teaching profile for rollback. Full source/index/notes and evaluated-runtime hashes are retained.", "",
              link("Browser proof of the corrected explanation", ART / "browser-metabolism-v2-2026-10-09.jpg"), ""]
    report_path = ROOT / "docs/reports/ASTER_COMPREHENSIVE_AUDIT_v2.md"
    with report_path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    tracked = [ART / "all-curricula-v3/summary.json", ART / "all-concepts-v1/summary.json", gaps_path,
               report_path, release / "manifest.json", live_path,
               *[ART / name for name in ("pytest-delivery.log", "ruff-delivery.log", "pip-delivery.log", "js-delivery.log")],
               *[path / "manifest.json" for path in packs]]
    ledger = {"schema_version": 1, "clinical_accuracy": None, "faculty_review": "pending",
              "curriculum_inventory_completeness": None,
              "files": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked},
              "runtime_hashes": full["inputs"]["runtime_hashes"], "live_chat_cases": live["cases"],
              "clinical_validation_complete": False, "all_gaps_closed": False,
              "software_tests_passed": int(test_result[1]), "software_warnings": int(test_result[2])}
    with (ART / "delivery-v2.json").open("x", encoding="utf-8") as handle:
        json.dump(ledger, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"report": str(report_path), "all_gaps_closed": False, "faculty_review": "pending"}))


if __name__ == "__main__":
    write()
