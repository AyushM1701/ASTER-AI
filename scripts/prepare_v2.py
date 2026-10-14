"""Consolidate explicitly acquired v2 sections sharing the same source snapshot."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    grouped = {}
    for name in ["topics", "drugs", "india"]:
        for doc in json.loads(
            (ROOT / f"data/knowledge_v2/{name}.json").read_text(encoding="utf-8")
        )["documents"]:
            key = (doc["url"], doc["version"])
            if key not in grouped:
                grouped[key] = doc
                doc["original_document_ids"] = [doc["id"]]
            else:
                current = grouped[key]
                for field in ["publisher", "jurisdiction", "raw_sha256", "source_date"]:
                    if current[field] != doc[field]:
                        raise ValueError("Conflicting snapshot metadata cannot be consolidated")
                current["title"] += "; " + doc["title"]
                current["sections"].extend(doc["sections"])
                current["original_document_ids"].append(doc["id"])
    output = ROOT / "data/knowledge_v2/reviewed_documents.json"
    output.write_text(
        json.dumps({"documents": list(grouped.values())}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "documents": len(grouped),
                "sections": sum(len(d["sections"]) for d in grouped.values()),
                "consolidated": [
                    d["original_document_ids"]
                    for d in grouped.values()
                    if len(d["original_document_ids"]) > 1
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
