"""Render the v2 evaluation report from recorded results; does not run tests."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "artifacts/evaluation/knowledge-v2-numpy"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def ratio(numerator, denominator):
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)"


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def main():
    retrieval = read(RESULTS / "retrieval.json")
    live = read(RESULTS / "live-summary.json")
    responses = read(RESULTS / "live-results.json")
    engineering = read(RESULTS / "engineering-checks.json")
    smoke = read(RESULTS / "api-smoke.json")
    run = read(RESULTS / "run-manifest.json")
    index = read(ROOT / "data/indexes/aster-v2-numpy-2026-10-07/manifest.json")
    kaggle = read(ROOT / "data/knowledge_v2/kaggle_catalogue_audit.json")
    before = read(ROOT / "artifacts/evaluation/knowledge-v2-final/dependency-audit-before.json")
    after = read(ROOT / "artifacts/evaluation/knowledge-v2-final/dependency-audit-after.json")
    topics = read(ROOT / "data/knowledge_v2/topics.json")["documents"]
    drugs = read(ROOT / "data/knowledge_v2/drugs.json")["documents"]
    india = read(ROOT / "data/knowledge_v2/india.json")["documents"]
    lexical, hybrid = retrieval["lexical"], retrieval["hybrid"]
    audit = kaggle["profile"]
    skipped = [item for item in after["dependencies"] if item.get("skip_reason")]
    vulnerabilities = [v for dep in before["dependencies"] for v in dep.get("vulns", [])]
    assert not any(dep.get("vulns") for dep in after["dependencies"])
    assert index["snapshot_hash"] == run["corpus_snapshot_hash"]
    assert smoke["health"]["references"]["snapshot_hash"] == index["snapshot_hash"]
    assert len(responses) == live["cases"]

    lines = [
        "# Aster Knowledge Library v2 — evaluation and release evidence",
        "",
        "Release: **aster-v2-2026-10-07**. Report date: **2026-10-07**. "
        "This report reads saved measurements; generating it does not rerun evaluation. "
        "These are developer development fixtures, not an independent clinical benchmark. "
        "**Qualified clinical review: not performed. Clinical accuracy: not measured.**",
        "",
        "## Delivered coverage",
        "",
        "| Collection | Documents or entries | Reference sections |",
        "|---|---:|---:|",
        f"| General medical education | {len(topics)} topics | {sum(len(d['sections']) for d in topics)} |",
        f"| US DailyMed product labels | {len(drugs)} labels, 30 medicine entities | {sum(len(d['sections']) for d in drugs)} |",
        "| Indian ICMR workflows | 12 | 24 |",
        "| Indian manufacturer product information | 5 | 10 |",
        f"| Active, approved library | {index['documents']} unique source documents | {index['records']} |",
        f"| NLEM 2022 catalogue | {index['indian_catalogue_entries']} names; 358 with extracted formulations | Separate listing-only catalogue |",
        f"| Kaggle candidate catalogue | {audit['candidate_exact_names']:,} exact names / {audit['rows']:,} rows | Unverified; excluded from clinical retrieval |",
        "",
        "General coverage is 31 conditions, nine tests, five imaging terms and prescription-label terminology. "
        "Two pairs of imaging topics share a source page; consolidation preserves all sections and original document IDs. "
        "The 34 entity strings in the combined index are not 34 distinct pharmacological ingredients: spelling/salt/combination identities remain distinct. "
        "No universal medicine, formulation, interaction, mechanism or disease coverage is claimed.",
        "",
        "## Retrieval scores",
        "",
        "The same 107 v2 fixtures were run against lexical and hybrid search. A hit means an expected source appears among the first three results; "
        "it does not prove the answer is correct or sufficient. Paraphrase cases are a 15-case subset. Purpose-section checks use 31 label cases.",
        "",
        "| Measurement | Lexical on v2 | Active hybrid MiniLM + NumPy |",
        "|---|---:|---:|",
        f"| Expected source in top three | {ratio(lexical['hit_at_3'], lexical['cases'])} | {ratio(hybrid['hit_at_3'], hybrid['cases'])} |",
        f"| Paraphrase source hits | {ratio(lexical['paraphrase_hits'], lexical['paraphrase_cases'])} | {ratio(hybrid['paraphrase_hits'], hybrid['paraphrase_cases'])} |",
        f"| Expected drug-purpose section | {ratio(lexical['drug_purpose_section_hits'], lexical['drug_purpose_cases'])} | {ratio(hybrid['drug_purpose_section_hits'], hybrid['drug_purpose_cases'])} |",
        f"| Median retrieval latency | {1000 * lexical['median_latency_seconds']:.2f} ms | {1000 * hybrid['median_latency_seconds']:.2f} ms |",
        "",
        "Latency is the local retrieval measurement, excluding model acquisition and answer generation; no concurrent-load benchmark was performed. "
        "Drug-purpose fixtures include unspecified product forms/strengths and repeated acetaminophen labels; these scores are not product-selection safety scores. "
        "V1's nine-record seed is preserved, but no fresh v1 accuracy benchmark was run. The comparison above isolates search algorithms on the same v2 content.",
        "",
        "### Known active retrieval misses",
        "",
        "| Fixture | Question | Expected source IDs |",
        "|---|---|---|",
    ]
    for result in hybrid["results"]:
        if not result["hit_at_3"]:
            lines.append(f"| {result['id']} | {cell(result['question'])} | {cell(', '.join(result['expected']))} |")
    lines += [
        "",
        "## Live chatbot evaluation",
        "",
        "Local Ollama ran Qwen3-VL 2B Instruct with strict source grounding and the active hybrid index. "
        "The 28 fixtures exercise condition/test education, selected medicine purposes, Indian labels/workflows, NLEM membership, "
        "uncovered topics/brands, wrong formulations/routes/strengths, dosing/diagnosis/emergency gates, mixed medical/general requests and explicit unverified catalogue lookup.",
        "",
        "| Check | Recorded result | Interpretation |",
        "|---|---:|---|",
        f"| Expected response status | {ratio(live['route_correct'], live['cases'])} | Fixture expectation, not medical accuracy |",
        f"| Allowed citation IDs | {ratio(live['citation_ids_valid'], live['cases'])} | Only {live['source_backed_cases']} cases contain cited claims; uncited cases pass vacuously |",
        f"| Entire cited section preserved | {ratio(live['complete_section_supported'], live['source_backed_cases'])} | Deterministic text support in responses with citations |",
        f"| Extractive fallback | {live['extractive_fallback_cases']}/{live['cases']} | Generated wording failed full-section support and was replaced |",
        "| Clinical accuracy / expert review | Not measured / not performed | No clinical reliability claim |",
        "",
        "The support check requires complete source-section text, including negation and adjacent qualifications. "
        "It is not a clinical entailment, answer-completeness or medical-truth measure. Repeated text can be supported yet insufficient for a user's question. "
        "Qwen weights were not fine-tuned. Unknown medical requests abstain rather than use model memory; recognized nonmedical chat is narrowly allowed.",
        "",
        "### Every live fixture",
        "",
        "| ID | Question | Expected / actual status | Expected status met | Answer method |",
        "|---|---|---|---|---|",
    ]
    for result in responses:
        response = result["response"]
        lines.append(
            f"| {result['id']} | {cell(result['question'])} | {result['expected_status']} / {response['status']} "
            f"| {result['route_correct']} | {cell(response.get('answer_method', '—'))} |"
        )
    lines += [
        "",
        "## Engineering and actual app checks",
        "",
        f"- Automated tests: **{engineering['pytest']['passed']} passed, {engineering['pytest']['failed']} failed**, {engineering['pytest']['seconds']} seconds. "
        f"One existing warning: {engineering['pytest']['warning']}.",
        "- Ruff, dependency consistency (`pip check`) and frontend JavaScript syntax: passed.",
        f"- Running UI → API chat bridge: **{sum(item['passed'] for item in smoke['results'])}/{len(smoke['results'])} passed**. "
        "Covered low haemoglobin, Indian Calpol purpose, incompatible Calpol strength, metformin personal dosing and unverified Ascoril catalogue lookup. The test session was deleted.",
        f"- Health at smoke time: ready; {index['records']} records, {index['documents']} documents, NLEM {index['indian_catalogue_entries']}, "
        "hybrid retrieval. Chat, attachment routing, printed OCR and research X-ray assets reported ready; handwriting remains experimental.",
        "",
        "Focused regression tests cover complete approval-set integrity, legacy checksum compatibility, negation support, exact medicine identity, "
        "route/form/release/strength compatibility, one-product tuple matching, unknown concentrations, superseded documents, stripped HTML scripts, "
        "mixed medical/general requests and unverified catalogue isolation. Final review rechecked 24 focused tests and found no remaining blockers in the reviewed findings.",
        "",
        "An initial pilot recorded 23/24 expected statuses: montelukast chewable matching failed. "
        "That defect was fixed and the active 28-case run passed. Review also identified and reproduced unsafe negation shortening, model-memory bypasses, "
        "route/form mismatches, cross-product strengths and conflicting active versions. These were fixed with regression tests. "
        "Historical pilot and Chroma benchmark artifacts are retained rather than overwritten.",
        "",
        "## Dependency audit and vector store",
        "",
        f"The pre-removal audit recorded {len(vulnerabilities)} Chroma advisory entries / {len({v['id'] for v in vulnerabilities})} distinct IDs "
        "against Chroma 1.5.9, with no patched version listed. Chroma had only been used as an embedded benchmark; no Chroma HTTP server was exposed. "
        "It was removed from the installed environment and model requirements. The active index uses checksum-bound normalized NumPy vectors instead.",
        "",
        f"The post-removal audit reports **no known vulnerabilities among {len(after['dependencies']) - len(skipped)} auditable dependency entries**. "
        f"It lists {len(after['dependencies'])} entries total and skips the two installed CPU PyTorch wheels not found on PyPI. "
        "This is a point-in-time advisory scan, not proof that every dependency is vulnerability-free.",
        "",
    ]
    lines += [f"- Skipped: `{item['name']}` — {item['skip_reason']}" for item in skipped]
    lines += [
        "",
        "Primary advisory context: [Chroma remote-code injection](https://github.com/advisories/GHSA-f4j7-r4q5-qw2c) "
        "and [Chroma authenticated code injection](https://github.com/advisories/GHSA-36p7-vc44-83pf). "
        "The original and final audit JSON files remain in `artifacts/evaluation/knowledge-v2-final/`.",
        "",
        "## Kaggle acquisition and data-quality audit",
        "",
        f"The user-proposed [A–Z Medicine Dataset of India]({kaggle['dataset']['url']}) was downloaded from Kaggle's public API "
        "without credentials or installing kagglehub. It is version 1, last updated **2022-11-17**. "
        "The uploader declares CC BY-SA 4.0; upstream rights clearance and clinical provenance are unverified. "
        "Attribution and share-alike metadata accompany the transformed exact-name index.",
        "",
        f"- {audit['rows']:,} rows and {audit['candidate_exact_names']:,} exact names; {audit['malformed_csv_rows']} malformed rows, "
        f"{audit['missing_names']} missing names, {audit['duplicate_source_id_occurrences']} duplicate source-ID occurrences.",
        f"- {audit['exact_names_with_multiple_rows']:,} names have multiple rows; {audit['duplicate_name_extra_rows']:,} extra duplicate-name rows.",
        f"- **{audit['exact_names_with_conflicting_composition_strings']} names have conflicting composition strings**; "
        f"{audit['exact_names_with_multiple_manufacturer_strings']:,} have multiple manufacturer strings.",
        f"- {audit['blank_or_whitespace_counts']['short_composition2']:,} rows have a blank second composition column. "
        "Only two short composition columns exist; multi-ingredient completeness is not established.",
        "",
        "The dataset never supplies clinical answer evidence, OCR corrections, dosing, substitutions or current price/availability claims. "
        "An explicit `catalogue: Ascoril LS Syrup` request displays only unverified reported strings, limitations and conflicts; "
        "its status remains insufficient evidence and it has no clinical citations. This is candidate discovery for further human verification, not an authoritative Indian drug library.",
        "",
        "## Source review, rights and integrity",
        "",
        "The source register records publisher, URL, jurisdiction, source date when available, retrieval date, version, usage basis, raw-file SHA-256 and "
        "approved section checksums. Unknown source dates remain null. Loaded records must match the complete approved set; deleting a warning section invalidates the release. "
        "Duplicate IDs, inconsistent source snapshots and simultaneously active versions of one source are rejected. "
        "New importers produce pending drafts and never auto-approve medical content. PDF extraction is page-level and requires manual review of tables/columns.",
        "",
        "NLM public-domain summaries/test material were selected under its [reuse policy](https://medlineplus.gov/about/using/usingcontent/). "
        "Six restricted A.D.A.M. sources were excluded. ICMR and GSK sources use brief original paraphrases with attribution; "
        "no open licence is asserted and full snapshots remain ignored local audit material. NICE has not been imported. "
        "CDSCO acquisition with a certificate error was not bypassed; NLEM uses the original signed NHSRC copy. "
        "A prohibited/expired Cipla monograph and a price-control Gazette are excluded from the active clinical library. "
        "DailyMed provides product-specific US in-use labels, [which can differ from current FDA-approved labels](https://www.dailymed.nlm.nih.gov/dailymed/about-dailymed.cfm). "
        "Indian manufacturer information must establish Indian brand identity separately.",
        "",
        "## OCR and X-ray: unchanged evidence",
        "",
        "This release does not retrain, improve or re-evaluate handwriting OCR or X-ray classification. "
        "The [existing evaluation](EVALUATION_REPORT.md) remains the relevant baseline: experimental handwriting exact word matches **10/37**, "
        "with 27 wrong readings not flagged; Tesseract **2/37**, synthetic printed fields **7/7**. "
        "Full handwritten prescription pages and dosage accuracy remain unvalidated. Names, doses and routes require confirmation against the original; unclear handwriting requires prescriber/pharmacist clarification. "
        "No dictionary or Kaggle row silently repairs an unreadable medicine. Indian prescribing sources here are labels/workflows, not private patient prescriptions. "
        "Research X-ray scoring remains unchanged and is not an independently measured clinical diagnosis service.",
        "",
        "## Reproducibility and evidence files",
        "",
        f"- Python: `{run['python']}`; OS: `{run['os']}`; logical CPUs: {run['hardware']['logical_cpus']}; RAM: {run['hardware']['ram_bytes'] / 1024**3:.1f} GiB.",
        "- Local model: `qwen3-vl:2b-instruct`; recorded digest `ea422f1e73652a95479954d8572d3c8c6022f628ce2d38a1a04aae1b7f2d5300`.",
        f"- Embedding: `{index['embedding_model']}`; pinned revision `{index['embedding_revision']}`; {index['records']} × {index['dimension']} normalized vectors.",
        f"- Corpus SHA-256: `{index['snapshot_hash']}`.",
        f"- Vector SHA-256: `{index['vectors_sha256']}`.",
        f"- Knowledge dependency lock SHA-256: `{run['knowledge_dependency_lock_hash']}`.",
        f"- Source register SHA-256: `{run['source_register_hash']}`.",
        "- No Git revision was available in this workspace. Full model-file hashes and run metadata are preserved.",
        "",
        "[Retrieval raw results](artifacts/evaluation/knowledge-v2-numpy/retrieval.json), "
        "[live responses](artifacts/evaluation/knowledge-v2-numpy/live-results.json), "
        "[live summary](artifacts/evaluation/knowledge-v2-numpy/live-summary.json), "
        "[engineering checks](artifacts/evaluation/knowledge-v2-numpy/engineering-checks.json), "
        "[actual app smoke](artifacts/evaluation/knowledge-v2-numpy/api-smoke.json), "
        "[run manifest](artifacts/evaluation/knowledge-v2-numpy/run-manifest.json), "
        "[Kaggle audit](data/knowledge_v2/kaggle_catalogue_audit.json).",
        "",
        "Commands, source-review workflow, exact catalogue usage and v1 rollback are in [the library guide](KNOWLEDGE_LIBRARY_V2.md). "
        "Refresh evaluation after changing content, models, policies or matching rules. A future clinical release needs qualified clinician/pharmacist review, "
        "held-out questions, relevance/completeness grading, conflicting-source review and appropriate independent validation.",
        "",
        "## Actual source coverage",
        "",
        "### General topics",
        "",
    ]
    lines += [f"- [{cell(doc['title'])}]({doc['url']})" for doc in topics]
    lines += ["", "### US product-specific labels", ""]
    lines += [f"- [{cell(doc['title'])}]({doc['url']}) — {cell(doc['version'])}" for doc in drugs]
    lines += ["", "### Indian prescribing information and workflows", ""]
    lines += [f"- [{cell(doc['title'])}]({doc['url']}) — {cell(doc['version'])}" for doc in india]
    destination = ROOT / "KNOWLEDGE_LIBRARY_V2_EVALUATION.md"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
