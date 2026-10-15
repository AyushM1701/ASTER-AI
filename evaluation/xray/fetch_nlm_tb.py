"""Download the NLM Montgomery and Shenzhen chest X-ray sets for LOCAL evaluation.

Terms (dataset ReadMe): deidentified, IRB-exempt public release; "do not share the
data set outside of your research group". Files are kept outside the repository
and never redistributed or packaged.

    python evaluation/xray/fetch_nlm_tb.py --out D:/aster-eval/xray --shenzhen-sample 220
"""
import argparse
import json
import random
import re
import time
from pathlib import Path

import httpx

BASE = "https://data.lhncbc.nlm.nih.gov/public/Tuberculosis-Chest-X-ray-Datasets/"
SETS = {
    "montgomery": ("Montgomery-County-CXR-Set/MontgomerySet/CXR_png/", "Montgomery-County-CXR-Set/MontgomerySet/ClinicalReadings/"),
    "shenzhen": ("Shenzhen-Hospital-CXR-Set/CXR_png/", "Shenzhen-Hospital-CXR-Set/ClinicalReadings/"),
}


def listing(client, path):
    html = client.get(BASE + path + "index.html").text
    return re.findall(r"href='([^'/]+\.(?:png|txt))'", html)


def parse_reading(text):
    age = re.search(r"(\d+)\s*(?:yrs?|years?|Y)\b", text, re.I) or re.search(r"Age:\s*0*(\d+)", text, re.I)
    months = re.search(r"(\d+)\s*(?:months?|month)\b", text, re.I)
    sex = re.search(r"\b(male|female|M|F)\b", text, re.I)
    return {"age_years": int(age.group(1)) if age else (0 if months else None),
            "sex": sex.group(1)[0].upper() if sex else None, "reading": " ".join(text.split())[:300]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--shenzhen-sample", type=int, default=220)
    args = parser.parse_args()
    out = Path(args.out)
    client = httpx.Client(timeout=120, headers={"User-Agent": "AsterEval/1 (local evaluation)"}, follow_redirects=True)
    manifest = []
    for name, (images, readings) in SETS.items():
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        texts = listing(client, readings)
        records = {}
        for txt in texts:
            path = folder / txt
            if not path.exists():
                path.write_bytes(client.get(BASE + readings + txt).content)
                time.sleep(0.2)
            stem = txt[:-4]
            info = parse_reading(path.read_text(encoding="utf-8", errors="ignore"))
            info["tb"] = stem.endswith("_1")
            records[stem] = info
        pngs = [p for p in listing(client, images) if p[:-4] in records]
        if name == "shenzhen":
            children = [p for p in pngs if (records[p[:-4]]["age_years"] or 99) < 18]
            adults = [p for p in pngs if p not in children]
            random.Random(14).shuffle(adults)
            pngs = children + adults[: max(0, args.shenzhen_sample - len(children))]
        for png in pngs:
            path = folder / png
            if not path.exists():
                response = client.get(BASE + images + png)
                if response.status_code != 200:
                    continue
                path.write_bytes(response.content)
                time.sleep(0.3)
            manifest.append({"file": f"{name}/{png}", "dataset": name, **records[png[:-4]]})
        print(name, len([m for m in manifest if m["dataset"] == name]), flush=True)
    (out / "nlm_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
