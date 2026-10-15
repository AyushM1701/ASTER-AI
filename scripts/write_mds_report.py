"""Publish measured MDS library results and reproducible evidence links."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts/evaluation/mds-v1"
RELEASE = ROOT / "data/references/mds/releases/aster-teaching-mbbs-mds-v2-final-2026-10-09"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def link(path, title=None):
    path = Path(path).resolve()
    return f"[{title or path.name}](<{path.as_posix()}>)"


def scores(report):
    rows = report["results"]
    supported = [row for row in rows if row["expected_status"] == "ok"]
    boundary = [row for row in rows if row["expected_status"] != "ok"]
    facts = sum(len(row["matched_fact_ids"]) + len(row["missing_fact_ids"]) for row in supported)
    claims = [claim for row in supported for claim in row["claim_support"]]
    return {
        "Expected response status": (sum(row["status_pass"] for row in rows), len(rows)),
        "Expected-source retrieval": (sum(row["retrieval_source_hit"] for row in supported), len(supported)),
        "Required reference facts": (sum(len(row["matched_fact_ids"]) for row in supported), facts),
        "Complete bounded reference agreement": (sum(row["reference_agreement_pass"] for row in supported), len(supported)),
        "Citation integrity (unanswered questions count as failures)": (sum(row["citation_integrity_pass"] for row in supported), len(supported)),
        "Source or validated-unit support among emitted claims": (sum(row["supported"] for row in claims), len(claims)),
        "Boundary non-handling": (sum(row["status_pass"] for row in boundary), len(boundary)),
    }


def main():
    mds_path = ARTIFACTS / "mds-hybrid-final-v3-2026-10-09.json"
    mbbs_path = ARTIFACTS / "mbbs-regression-hybrid-final-v3-2026-10-09.json"
    mds, mbbs = read(mds_path), read(mbbs_path)
    for report in (mds, mbbs):
        if not report["inputs"]["runtime_files_unchanged_during_evaluation"]:
            raise ValueError("Runtime changed during evaluation")
        for name, expected in report["inputs"]["runtime_files_sha256"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                raise ValueError("Evaluated runtime changed: " + name)
    topics_path = ARTIFACTS / "topics-hybrid-final-2026-10-09.json"
    topics = read(topics_path)
    baseline = read(ARTIFACTS / "baseline-hybrid-bound-topics-2026-10-09.json")
    live_path = max(ARTIFACTS.glob("live-api-*.json"))
    live = read(live_path)
    activation_path = max(ARTIFACTS.glob("activation-*.json"))
    activation = read(activation_path)
    if live["health"]["teaching"]["version"] != RELEASE.name or live["status_passes"] != live["cases"]:
        raise ValueError("Actual application checks did not pass on this release")
    score_mds, score_mbbs = scores(mds), scores(mbbs)
    lines = ["# Aster MDS library and evaluation report", "", "9 October 2026 · Oral Pathology and Oral Microbiology", "",
             "## Active result", "",
             f"The combined local teaching release `{RELEASE.name}` is active. It contains **2,705 sections from 181 source units**, with **39 source-bound plain-language explanations** and **78 source-review holds**. Source units are individual pages, chapters or articles, not 181 independent publications.", "",
             "The 1,891 original MBBS sections and 24 original explanations were preserved. The expansion adds **814 sections**: 260 dental foundations, 447 research sections and 107 statistics foundations. Two new foundation books and 27 licensed research papers were acquired. Three of those papers remain quarantined; acquisition does not imply availability for answers. The books, article dates, study designs, permissions, excluded candidates and all 89 topics are listed in " + link(ROOT / "docs/reports/MDS_STUDY_MATERIALS.md", "the study-material register") + ".", "",
             "This is retrieval augmentation of Aster's existing local model, not weight training. The existing Qwen 2B text/vision configuration remains in use. Medicine identity routing, secondary-data caution, OCR and X-ray paths are preserved. This release does not supply new OCR or imaging validation.", "",
             "The photographed checklist has 89 topic entries; images 2 and 3 duplicate a page. Assignee names were ignored. MDS-49 contains uncertain handwriting: inferential statistics was tested as an explicit, unconfirmed interpretation. The photographed pages do not establish a complete official MDS curriculum.", "",
             "## Actual evaluation scores", "",
             "These are developer-authored, bounded reference-agreement tests. Exact source wording and approved explanation bindings are checked. They do not measure faculty correctness, complete exam answers or clinical accuracy. The focused MDS benchmark is deliberately small and contains 22 supported questions plus six boundary cases.", "",
             "| Measure | Focused MDS, hybrid | Existing MBBS, hybrid |", "|---|---:|---:|"]
    for key in score_mds:
        values = []
        for score in (score_mds, score_mbbs):
            numerator, denominator = score[key]
            values.append(f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)" if denominator else "Unmeasured")
        lines.append(f"| {key} | {values[0]} | {values[1]} |")
    lines += ["| Clinical correctness / faculty review | Unmeasured | Unmeasured |", "",
              "Full outputs preserve every prompt, answer, citation, missing fact, timing, source hash and runtime hash: " + link(mds_path) + " and " + link(mbbs_path) + ". Earlier candidate runs remain available but are superseded by these final v3 files.", "",
              "The final lexical MDS run also passed 28/28 expected statuses and 22/22 bounded reference-agreement cases before the last shared guard improvements. The deployed hybrid results above are the final activation evidence. " + link(ARTIFACTS / "mds-lexical-final-v2-2026-10-09.json") + ".", "",
              "The previous active MBBS hybrid benchmark measured 92/93 expected statuses, 77/81 expected-source hits, 144/162 required facts and 69/81 complete reference-agreement cases. The final results above retain the full denominators; changed source matches and unanswered comparisons remain visible. The developing versus impaired hepatic-metabolism comparison is an existing non-handled case. The free-drug/protein-binding viva prompt is now also declined: its previous response discussed antibacterial ribosomes and resistance rather than pharmacokinetic distribution. Refusing that mismatch reduces the status score by one. This remaining retrieval gap is not a new successful answer.", "",
              "## Topic probes and remaining gaps", "",
              f"The same whole-topic probe method produced an educational response for **{topics['runtime_statuses'].get('ok', 0)}/89** topics in this release, compared with **{baseline['runtime_statuses'].get('ok', 0)}/89** in the previous active collection. Corpus and runtime changes both contributed; this is not a controlled measure of corpus improvement alone. A response may cover only a small part of a topic. All 89 have related material associations, which remain developer/curator nominations rather than verified coverage.", "",
              "The following broad prompts were not handled; focused questions can sometimes retrieve narrower material. These remain explicit retrieval or breadth gaps:", ""]
    lines.extend(f"- {row['id']}: {row['title']}." for row in topics["topics"] if row["runtime_status"] != "ok")
    lines += ["", link(topics_path, "All 89 topic prompts and outputs") + ". Full-topic completeness, independent postgraduate examination performance and medical faculty correctness remain **unmeasured**. It cannot yet answer every MDS or MBBS question.", "",
              "## Source quality and research safeguards", "",
              "Rights were checked per source against publisher statements or article XML. CC BY, CC BY-SA, CC BY-NC and CC BY-NC-SA conditions, attribution and relevant version information are retained. NoDerivatives, unclear rights and unselected candidates are reading links. Third-party figures and unreviewed tables are excluded. This local collection includes noncommercial material; public or commercial reuse needs source-specific review.", "",
              "The 78 holds comprise nine preserved MBBS holds, 19 dental passage holds and 50 sections from three quarantined statistical-method papers. Examples include misleading cell-cycle counts, tooth-resorption lineage, PTH/PTHrP wording, dentin dimensions, salivary-gland statements and statistics/extraction errors. Restricted passages can contribute only through specifically bound explanations where allowed; excluded passages cannot answer questions. Original files remain available for audit. A rights check does not establish factual correctness, and this was a bounded developer review rather than a full textbook audit.", "",
              "Research claims and citations retain publication date, study design, population/model and limitations. Experimental tooth-regeneration findings remain research evidence. Missing study context or changed source/explanation hashes fail closed. Source cards display research context and source-review notices.", "",
              "Regression checks prevent dental eruption from answering skin-eruption questions, invented syndromes from borrowing another syndrome, normal pulmonary distribution from substituting for a normal probability distribution, and antimicrobial resistance from substituting for pharmacokinetic free/protein-bound drug distribution. A shared guard now routes personal disease-exclusion or reassurance requests to professional review.", "",
              "Plain doctor-to-patient style is available through 39 bounded explanations. Other questions may use longer source excerpts. Unrestricted model paraphrasing is not enabled because meaning and qualifications must remain supported. A faculty-reviewed explanation set and broader independent assessment are the next steps for consistent postgraduate teaching quality.", "",
              "## Application and engineering checks", "",
              f"The actual frontend-to-backend chat bridge passed **{live['status_passes']}/{live['cases']} synthetic requests** after activation and restart. These include MDS concepts, research, established MBBS questions, unknown content, personal dosing, personal X-ray reassurance, emergency escalation and the existing Ascoril catalogue route. Its temporary API session was deleted. " + link(live_path) + ".", "",
              "The final full suite passed **296 tests** with one existing Starlette/httpx deprecation warning. Ruff checks passed for backend, scripts and tests. Dependency validation reported no broken requirements. " + link(ARTIFACTS / "pytest-final-v3-2026-10-09.log") + "; " + link(ARTIFACTS / "ruff-final-2026-10-09.log") + ". These verify software behavior, not clinical safety or OCR/X-ray performance.", "",
              "## Activation, rollback and reproducibility", "",
              "The six-field profile is " + link(ROOT / "configs/mds_teaching_profile.json") + ". Activation writes `configs/teaching.env`, preserves the previous profile and leaves `.env` unchanged. The actual readiness response confirms 2,705 records, 39 explanations, 78 holds and no teaching-load error. All services remain bound to loopback.", "",
              "Activation ledger: " + link(activation_path) + ". Previous profile backup: " + link(activation["rollback_path"]) + ". To roll back, restore that saved profile to `configs/teaching.env` and restart the owned Aster application; preserve the release and index for comparison. The existing request guards remain in code.", "",
              "Release manifest SHA-256: `" + hashlib.sha256((RELEASE / "manifest.json").read_bytes()).hexdigest() + "`. Index and source hashes are recorded in the benchmark inputs and " + link(RELEASE / "manifest.json") + ". Raw snapshots, extraction scripts, component manifests and acquisition reports are linked from the study-material register.", "",
              "Rebuild using the pinned source configurations with `scripts/build_mds_dental.py`, `scripts/build_mds_research.py` and `scripts/build_mds_statistics.py`; bind notes with `scripts/build_mds_notes.py`; compose a fresh release with `scripts/compose_mds_library.py`; then build its matching index with `scripts/build_teaching_index.py`. Immutable outputs require new destination names. `scripts/evaluate_mbbs.py`, `scripts/evaluate_mds_topics.py` and `scripts/smoke_mds.py` reproduce the checks against explicit release/index/notes inputs. `scripts/activate_teaching.py --profile configs/mds_teaching_profile.json --ledger-directory artifacts/evaluation/mds-v1 --activate` validates this profile before writing it.", "",
              "No paid resources, accounts, access agreements or public deployment were created. The collected material is a substantial, finite expansion rather than all published literature."]
    path = ROOT / "docs/reports/MDS_LIBRARY_REPORT.md"
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(json.dumps({"output": str(path), "mds": score_mds, "mbbs": score_mbbs, "live": live["status_passes"]}))


if __name__ == "__main__":
    main()
