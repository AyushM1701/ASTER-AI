"""Write a source register and all photographed topics without claiming mastery."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def label(text):
    return str(text).replace("|", "\\|").replace("[", "\\[").replace("]", "\\]").replace("\n", " ")


def write(release, topics, output):
    release = Path(release)
    metadata = json.loads((release / "metadata.json").read_text(encoding="utf-8"))
    syllabus = json.loads((release / "syllabus.json").read_text(encoding="utf-8"))
    register = yaml.safe_load((release / "sources.yaml").read_text(encoding="utf-8"))["sources"]
    rows = {row["chunk_id"]: row for row in (json.loads(line) for line in (release / "records.jsonl").read_text(encoding="utf-8").splitlines())}
    explanations = json.loads((release / "explanations.json").read_text(encoding="utf-8"))
    excluded = {flag["chunk_id"] for flag in explanations["source_review_flags"] if flag["runtime_policy"] == "exclude"}
    mappings = defaultdict(set)
    for key, context in metadata["chunks"].items():
        if key not in excluded:
            for topic in context.get("syllabus_ids", []):
                mappings[topic].add(rows[key]["source_id"])
    by_source = {row["source_id"]: row for row in register}
    runtime = {row["id"]: row for row in json.loads(Path(topics).read_text(encoding="utf-8"))["topics"]}
    lines = ["# Aster MDS study-material register", "", "Oral Pathology and Oral Microbiology · photographed scope · 9 October 2026", "",
             "The four submitted images contain 89 topic entries. Images 2 and 3 repeat a page. Handwritten assignee names were ignored. This is the photographed checklist, not a claim to reproduce the complete official MDS curriculum.", "",
             "All topic associations below identify relevant material, not complete syllabus coverage. A chat response can answer only part of a broad topic. Faculty correctness and completeness remain unmeasured. Known source errors are held separately.", "",
             "## Foundation books", "",
             "- [Histology and Embryology for Dental Hygiene](https://openoregon.pressbooks.pub/histologyandembryology/), Laird C Sheldahl, 2020. Eleven captured chapters; CC BY-NC-SA 4.0. Dental-hygiene foundation level; PG depth is supplemented by research. Known flawed passages are blocked or restricted to bounded notes.",
             "- [Learning Statistics with R](https://learningstatisticswithr.com/), Danielle Navarro, version 0.7.1 in the captured 7 October 2026 changelog. Eight selected chapters; CC BY-SA 4.0. [Saved publisher PDF](<" + (ROOT / "data/references/mds/raw/statistics/Learning-Statistics-with-R.pdf").as_posix() + ">). HTML is the canonical extraction source; equations and relevant footnotes are retained.", "",
             "Figures, third-party media, unreviewed tables and code are excluded from answer evidence. Attribution, license links, changes and applicable noncommercial/ShareAlike obligations are retained per source.", "",
             "## Topic checklist", "", "The focused-source column uses author/curator associations after runtime exclusions. A retrieved candidate is shown separately where no focused association exists. Both require faculty inspection.", "",
             "| ID | Photographed topic | Related source links | Chat handling of the whole-topic prompt |", "|---|---|---|---|"]
    for topic in syllabus["topics"]:
        source_ids = sorted(mappings[topic["id"]])
        association = "focused association"
        if not source_ids:
            source_ids = sorted({row["source_id"] for row in runtime[topic["id"]]["candidates"]})
            association = "retrieval candidate only"
        links = [f"[{label(by_source[key]['title'])}]({by_source[key]['url']})" for key in source_ids[:3]]
        material = "; ".join(links) + (f" · {association}; {len(source_ids)} source units" if links else "No source candidate; gap")
        status = runtime[topic["id"]]["runtime_status"]
        lines.append(f"| {topic['id']} | {label(topic['title'])} | {material} | {status}; completeness unmeasured |")
    lines += ["", "MDS-49: the handwritten statistics term is uncertain (appears to read ‘indicative’). The tested interpretation is inferential statistics, explicitly recorded as unconfirmed in syllabus.json.", "",
              "## Research papers acquired", "", "Publication date, study design, population/model and limitations accompany every research excerpt. Twenty-seven licensed papers were acquired; three statistical-method papers are quarantined after source/extraction concerns. Their original files remain available for inspection. Experimental findings do not establish a human treatment.", "",
              "| Article | Date | Design / setting | Rights | Source status |", "|---|---|---|---|---|"]
    for source in register:
        if not source["source_id"].startswith("mds-pmc-"):
            continue
        contexts = [value for value in metadata["chunks"].values() if value.get("source_id") == source["source_id"]]
        context = contexts[0]
        source_keys = {key for key, value in metadata["chunks"].items() if value.get("source_id") == source["source_id"]}
        state = "Quarantined; original retained" if source_keys <= excluded else "Available with study limitations"
        lines.append(f"| [{label(source['title'])}]({source['url']}) | {source.get('source_date')} | {label(context.get('study_design'))} / {label(context.get('study_type'))} | {source.get('license')} | {state} |")
    lines += ["", "## Reading links without ingestion", "", "Unclear, missing or NoDerivatives rights produce reading links rather than imported article prose. Some links also identify secondary candidates outside the selected scope.", ""]
    bibliography_path = ROOT / "data/references/mds/components/research/mds-research-2026-10-09-v2/bibliography.json"
    bibliography = json.loads(bibliography_path.read_text(encoding="utf-8"))
    entries = bibliography if isinstance(bibliography, list) else bibliography.get("entries", bibliography.get("bibliography", []))
    for entry in entries:
        lines.append(f"- [{label(entry.get('title', entry.get('pmcid', 'Candidate article')))}]({entry.get('url', '')}) — {label(entry.get('reason', entry.get('exclusion_reason', 'Not ingested; permission/scope review required')))}")
    lines += ["", "[OpenIntro Statistics](https://www.openintro.org/book/os/) is a reading link only in this expansion. Its [current terms](https://www.openintro.org/terms/) include an automated AI/ML-training compensation condition; no agreement was accepted. The independent Navarro book supplies the imported statistics foundations.", "",
              "## Local provenance and study files", "",
              "- [Dental acquisition and licensing report](<" + (ROOT / "data/references/mds/raw/dental/ACQUISITION_REVIEW.md").as_posix() + ">)",
              "- [Research acquisition and exclusion report](<" + (ROOT / "data/references/mds/raw/research/RESEARCH_ACQUISITION_REPORT.md").as_posix() + ">)",
              "- [Statistics source and license report](<" + (ROOT / "data/references/mds/components/statistics/mds-statistics-v1-2026-10-09/BIBLIOGRAPHY_LICENSE_REPORT.md").as_posix() + ">)",
              "- [Complete source register](<" + (release / "sources.yaml").resolve().as_posix() + ">)",
              "- [All topic prompts, candidates and responses](<" + Path(topics).resolve().as_posix() + ">)",
              "", "The original MBBS references and medicine collections remain separate or preserved in the combined teaching release. This expansion changes retrieval content and bounded explanations, not the language model's weights."]
    output = Path(output)
    with output.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return {"output": str(output), "topics": len(syllabus["topics"]), "focused_associations": len(mappings)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--topics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write(args.release, args.topics, args.output)))
