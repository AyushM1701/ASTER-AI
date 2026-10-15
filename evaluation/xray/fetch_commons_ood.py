"""Download a small, licence-recorded out-of-scope image set from Wikimedia Commons
for local gate evaluation only (stored outside the repository; not redistributed).

    python evaluation/xray/fetch_commons_ood.py --out D:/aster-eval/xray/commons
"""
import argparse
import json
import re
import time
from pathlib import Path

import httpx

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "AsterEval/1 (+https://github.com/AyushM1701/ASTER-AI; local evaluation)"}
GROUPS = {
    # group: (expected gate outcome, categories)
    "chest_any_view": ("mixed", ["Category:X-rays of the chest"]),
    "chest_lateral": ("reject", ["Category:Lateral x-rays of the chest"]),
    "dental_panoramic": ("reject", ["Category:Orthopantomograms"]),
    "hand_xray": ("reject", ["Category:X-rays of fractures of the human wrist and hand", "Category:X-rays of injuries to the wrist and hand"]),
    "skull_xray": ("reject", ["Category:X-rays of fractures of the human skull", "Category:X-rays of fractures of the human mandible"]),
    "head_ct": ("reject", ["Category:CT images of fractures of the human skull", "Category:CT images of fractures of the human mandible"]),
    "brain_mri": ("reject", ["Category:MRI of the human brain", "Category:Magnetic resonance imaging of the brain"]),
    "photo": ("reject", ["Category:Quality images of cats", "Category:Quality images of food", "Category:Quality images of landscapes"]),
}


def members(client, category, limit):
    params = {"action": "query", "list": "categorymembers", "cmtitle": category, "cmtype": "file",
              "cmlimit": 200, "format": "json"}
    data = client.get(API, params=params).json()
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])
            if re.search(r"\.(?:jpe?g|png)$", m["title"], re.I)][:limit]


def info(client, titles):
    params = {"action": "query", "titles": "|".join(titles), "prop": "imageinfo", "iiprop": "url|extmetadata|size",
              "iiurlwidth": 1024, "format": "json"}
    pages = client.get(API, params=params).json().get("query", {}).get("pages", {})
    return [p for p in pages.values() if p.get("imageinfo")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--per-group", type=int, default=15)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(headers=UA, timeout=60, follow_redirects=True)
    manifest = []
    for group, (expected, categories) in GROUPS.items():
        titles = []
        for category in categories:
            titles += members(client, category, args.per_group * 2)
        titles = list(dict.fromkeys(titles))[: args.per_group]
        for start in range(0, len(titles), 20):
            for page in info(client, titles[start:start + 20]):
                ii = page["imageinfo"][0]
                meta = ii.get("extmetadata", {})
                license_name = (meta.get("LicenseShortName") or {}).get("value", "")
                if not re.search(r"public domain|cc0|cc[ -]by", license_name, re.I):
                    continue
                url = ii.get("thumburl") or ii["url"]
                name = re.sub(r"[^A-Za-z0-9._-]+", "_", page["title"].split(":", 1)[1])[:120]
                path = out / group / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    response = client.get(url)
                    if response.status_code != 200:
                        continue
                    path.write_bytes(response.content)
                    time.sleep(0.5)
                manifest.append({"file": str(path.relative_to(out)), "group": group, "expected": expected,
                                 "title": page["title"], "license": license_name,
                                 "artist": re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))[:200],
                                 "source_url": ii.get("descriptionurl")})
        print(group, sum(1 for m in manifest if m["group"] == group), flush=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
