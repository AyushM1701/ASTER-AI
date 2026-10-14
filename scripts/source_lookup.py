"""Find official DailyMed product labels for a named ingredient (review required).

Only the supplied ingredient name is transmitted. This is a developer acquisition
tool, not an automatic chat fallback or an Indian brand-equivalence service.
"""

import argparse
import json
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ingredient", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; retain previous search evidence")
    response = requests.get(
        "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json",
        params={"drug_name": args.ingredient, "pagesize": 100},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    candidates = [
        {
            "title": row["title"],
            "setid": row["setid"],
            "url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={row['setid']}",
            "snapshot_url": f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{row['setid']}.xml",
            "published_date": row.get("published_date"),
            "review_status": "pending_review",
            "jurisdiction": "US",
        }
        for row in payload.get("data", [])
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "ingredient_query": args.ingredient,
                "metadata": payload.get("metadata"),
                "candidates": candidates,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Saved {len(candidates)} candidate labels. Verify exact product, formulation, strength, version and rights before ingestion. No library activation occurred."
    )


if __name__ == "__main__":
    main()
