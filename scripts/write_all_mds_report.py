"""Document actual imported material and developer checks, without accuracy claims."""

import json
from collections import Counter
from pathlib import Path

from backend.app.services.output_validation import finalize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/evaluation/all-mds-2026-10-10"
RELEASE = ROOT / "data/references/mds/releases/aster-teaching-all-mds-v3-2026-10-10"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    specs = read(ROOT / "configs/all_mds_topics.json")
    recent = read(ROOT / "data/references/mds/all-specialties/acquisition-v1-2026-10-10/selected-title-anchored-v2.json")
    older = read(ROOT / "data/references/mds/all-specialties/acquisition-established-v1-2026-10-10/selected-final-v2.json")
    documents = recent["documents"] + older["documents"]
    manifest = read(RELEASE / "manifest.json")
    explanations = read(RELEASE / "explanations.json")
    baseline = read(OUT / "baseline-optimized-lexical.json")
    lexical_path = OUT / "expanded-current-lexical.json"
    expanded = read(lexical_path if lexical_path.exists() else OUT / "expanded-lexical.json")
    hybrid_path = OUT / "expanded-hybrid-appraisal.json"
    active = read(hybrid_path) if hybrid_path.exists() else expanded
    final_rows = []
    for row in active["topics"]:
        response = finalize(row["question"], row["answer"], explanations["units"]) if row["answer"] else None
        final_rows.append({"id": row["id"], "specialty": row["area"], "question": row["question"],
                           "response": response, "medical_correctness": None, "completeness": None,
                           "faculty_review": "pending"})
    (OUT / "final-guard-responses.json").write_text(json.dumps(final_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    covered = {i for doc in documents for i in doc["syllabus_ids"]}
    counts = Counter((row["response"] or {}).get("status", "not_handled") for row in final_rows)
    unanswered = [r["question"].removeprefix("Explain ") for r in final_rows if not r["response"]]
    table, coverage = [], []
    for specialty in specs["specialties"]:
        sid = specialty["id"]
        docs = [d for d in documents if sid in d["subjects"]]
        associated = sum(t["id"] in covered for t in specialty["topics"])
        final = [r for r in final_rows if r["specialty"] == sid]
        ok = sum((r["response"] or {}).get("status") == "ok" for r in final)
        table.append(f'| {specialty["title"]} | {len(docs)} | {associated}/14 | {ok}/14 |')
        for topic in specialty["topics"]:
            coverage.append({"id": topic["id"], "specialty": specialty["title"], "title": topic["title"],
                             "associated_source_ids": [d["id"] for d in docs if topic["id"] in d["syllabus_ids"]],
                             "complete_curriculum_coverage": None, "medical_correctness": None})
    (OUT / "topic-gaps.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    summary = {"new_articles": len(documents), "teaching_records": manifest["records"], "teaching_sources": manifest["sources"],
               "topic_associations": len(covered), "editorial_topics": specs["topic_count"],
               "baseline_statuses": baseline["runtime_statuses"], "expanded_lexical_statuses": expanded["runtime_statuses"],
               "active_test_backend": active["release"]["backend"], "final_guard_statuses": dict(counts),
               "clinical_correctness": None, "faculty_review": "pending", "full_curriculum_mastery": False}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    doc = ["# Aster: all-specialty MDS knowledge expansion", "", "Built 10 October 2026.", "",
           f'Added **{len(documents)} unique openly licensed journal reviews** and **{manifest["records"] - 2916:,} research sections**. '
           f'The composed teaching library contains **{manifest["records"]:,} sections from {manifest["sources"]} registered sources**. '
           "The prior MBBS material, 43 prepared explanations and 117 source review holds remain intact. One additional inherited dentin classification passage is withheld pending review, bringing the hold count to 118.", "",
           "This is a retrieval-library expansion. Model weights have not been fine-tuned. It is a development educational collection, not evidence that Aster can answer every MDS question or has been clinically validated.", "",
           "## Specialty material and developer checks", "",
           "| Specialty | New associated articles | Topics with associated articles | Final guard accepts response |",
           "|---|---:|---:|---:|", *table, "",
           "Articles can be associated with multiple specialties, so the column totals are not additive. An association does not establish complete topic teaching. The 126-topic map is an editorial starting set, not the full official competency inventory.", "",
           "## What was acquired", "",
           "The recent pack contains 153 title-anchored reviews; the older pack contains 50 reviews with recorded publication dates through 2024. Full JATS XML, article-level licence evidence, authors, DOI, dates, complete paragraph extraction and snapshot hashes are retained. The corpus includes CC BY, CC BY-NC and CC BY-NC-SA 4.0 material. Source-specific noncommercial and share-alike obligations apply independently of Aster's MIT code licence.", "",
           "The two passes each used 126 keyword searches, up to 30 candidate records per topic. The recent pass selected up to three articles per topic; the older pass selected up to one. Earlier broad selections were held out after title/date checks. This is a bounded search, not all free dental literature or a systematic review. Citation count was used only for discovery; it is not a quality score.", "",
           "[Europe PMC API](https://europepmc.org/RestfulWebService) provides the full-text acquisition route; "
           '[PMC text-mining guidance](https://pmc.ncbi.nlm.nih.gov/tools/textmining/) explains permitted bulk access. '
           "Individual article licences, rather than repository membership, determine ingestion eligibility.", "",
           "Tables, figures, quotations, supplements and reference lists are excluded. Overlong sections that cannot preserve complete paragraphs are held out. Every research chunk repeats the source date, review scope and limitations. Population/model and synthesis quality are explicitly unappraised, rather than guessed. Old findings are not labelled current guidance.", "",
           "## Curriculum and study materials", "",
           "The [official 2017 MDS syllabus](https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf) includes all nine specialties. "
           'The project retains page-bound outlines for all nine in `data/references/mds/all-specialties/curriculum-reference-2017.json`. '
           "That file is a curriculum audit reference, not medical teaching content. Later amendments and university-specific requirements still need reconciliation.", "",
           "[Study material register](MDS_STUDY_MATERIAL_REGISTER.md) lists the imported articles by topic, with links, dates and licences. "
           '`artifacts/evaluation/all-mds-2026-10-10/topic-gaps.json` records source associations and unanswered coverage questions. '
           "The existing foundational library remains important: specialist research reviews do not replace anatomy, physiology or textbook teaching.", "",
           "## Evaluation and remaining gaps", "",
           f'The same 126 short questions produced {baseline["runtime_statuses"].get("ok", 0)}/126 teaching responses in the old library and '
           f'{expanded["runtime_statuses"].get("ok", 0)}/126 in the expanded lexical library. '
           f'The {active["release"]["backend"]} run, after the terminal output guard, has statuses {dict(counts)}. '
           'These measure response availability and engineering checks, not medical accuracy, completeness or postgraduate exam performance.', "",
           "No teaching response was returned for: " + "; ".join(unanswered) + ". "
           "Hybrid retrieval additionally finds a passage about oral-health survey limitations; that passage does not constitute a complete survey-methods lesson.", "",
           "All imported study designs/populations require critical appraisal. Independent medical scores remain blank. The faculty review pack includes the responses, evidence checks and scoring fields; no model or developer is presented as medical faculty.", "",
           "Live response inspection identified a dentin classification passage equating development timing with tooth eruption and reactionary dentin with sclerotic dentin. Revision v3 excludes that entire source unit (`chunk_e9a8236cee2f5b0382dcd5fc`) pending independent review. "
           "The appraisal comparisons include [reactionary dentinogenesis](https://pubmed.ncbi.nlm.nih.gov/7626417/), "
           "[experimental dentine development definitions](https://pmc.ncbi.nlm.nih.gov/articles/PMC2100295/) and "
           "[tooth eruption](https://www.ncbi.nlm.nih.gov/books/NBK549878/). These links are appraisal references, not newly imported teaching evidence or a faculty decision.", "",
           "Remaining work includes complete specialty competency mapping; verified plain-language introductions and deeper teaching notes; landmark articles absent under available reuse permissions; current guideline/version reconciliation; comparative and case-based answers; image/histology teaching; and independent scoring of factual correctness, applicability and completeness. Comparison requests currently abstain, and the generic viva workflow is not a complete exam tutor. Research-paper drafting and cross-paper critical appraisal are not complete workflows.", "",
           "## Retrieval and safety changes", "",
           "The retrieval service now stores source checks within each collection to avoid repeatedly re-scanning thousands of unchanged passages when global caches fill. A changed passage invalidates its stored checks. A direct-dose screening bug affecting multi-digit amounts was fixed. Indian/British spellings including dentine, paediatric and hypomineralisation now retrieve their corresponding concepts. Personal diagnosis/treatment boundaries and the final source-binding guard remain active.", "",
           "## Reference portals for further checking", "",
           "These portals were inspected but their complete documents have not been imported without individual rights/version review:", "",
           "- [AAE clinical resources](https://www.aae.org/specialty/clinical-resources/) and [guidelines](https://www.aae.org/specialty/clinical-resources/guidelines-position-statements/): endodontic terminology, diagnosis and professional guidance. Some resources are explicitly under review.",
           "- [AAPD reference manual](https://www.aapd.org/research/oral-health-policies--recommendations/overview/): paediatric policies, best practices and guidelines.",
           "- [EFP guidelines](https://www.efp.org/education/continuing-education/clinical-guidelines/): periodontitis and peri-implant disease guidance.",
           "- [WHO oral health status report](https://www.who.int/publications/i/item/9789240061484) and [strategy/action plan](https://www.who.int/publications/i/item/9789240090538): public-health context.", "",
           "## Reproduction and activation", "",
           "Search maps: `configs/all_mds_topics.json` and `configs/all_mds_established_searches.json`. Acquisition: `python -m scripts.acquire_all_mds --config PATH --output NEW_DIRECTORY`. "
           'The selected-title/date registries are the exact release inputs; raw search results include held candidates and must not be substituted blindly. '
           'Build with `scripts.build_mds_research --syllabus configs/all_mds_topics.json`, compose through `scripts.compose_mds_library`, and build the hybrid index through `scripts.build_teaching_index`. '
           'Use new versioned paths; preserve existing releases and review holds. No evaluation questions/answer keys enter teaching records.', "",
           "Active release: `data/references/mds/releases/aster-teaching-all-mds-v3-2026-10-10`. "
           'Index: `data/indexes/all-mds-v2-2026-10-10`. '
           'Runtime activation evidence and previous teaching settings are retained in `artifacts/evaluation/all-mds-2026-10-10/activation-appraisal.json`. '
           'The v2 dense index is compatible because v3 preserves byte-identical source records and changes only the version-bound review holds. '
           "This collection has not been approved for redistribution in the Windows release bundle.", ""]
    checks_path = OUT / "verification.json"
    if checks_path.exists():
        checks = read(checks_path)
        summary["verification"] = checks
        doc.extend(["## Verified runtime", "",
                    f'Automated tests: {checks["tests_passed"]} passed. Ruff: {checks["ruff"]}. '
                    f'Live synthetic API checks: {checks["live_status_passes"]}/{checks["live_cases"]} expected statuses. '
                    f'Running teaching version: `{checks["active_version"]}`. '
                    "The synthetic session was deleted. These checks do not score medical correctness. "
                    "The independent review pack is in `artifacts/evaluation/all-mds-2026-10-10/faculty-review-pack-appraisal`.", ""])
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (ROOT / "ALL_MDS_LIBRARY.md").write_text("\n".join(doc), encoding="utf-8")
    guide = ["# MDS study material register", "", "Imported review articles grouped by the editorial 126-topic map. "
             'Faculty appraisal, full coverage and currency are unverified. Read the complete original paper, including excluded tables/figures and its cited studies. '
             "A review is not automatically a guideline or an authoritative textbook.", ""]
    for specialty in specs["specialties"]:
        guide.extend(["## " + specialty["title"], ""])
        for topic in specialty["topics"]:
            guide.extend(["### " + topic["title"], ""])
            matching = [d for d in documents if topic["id"] in d["syllabus_ids"]]
            if not matching:
                guide.append("No new title-anchored article retained for this topic; inspect the existing library and fill this gap.")
            for article in sorted(matching, key=lambda d: d["source_date"], reverse=True):
                guide.append(f'- [{article["title"]}]({article["url"]}) — {article["source_date"]}; {article["license"]}; DOI: {article.get("doi") or "not supplied"}.')
            guide.append("")
    (ROOT / "MDS_STUDY_MATERIAL_REGISTER.md").write_text("\n".join(guide), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
