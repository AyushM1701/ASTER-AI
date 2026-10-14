"""Offline, provenance-preserving links to Netmeds; never merges clinical evidence.

Name links and reported-field agreement are separate. No fuzzy spelling repair,
ingredient synonyms, concentration inference or prescribing equivalence is used.
"""

import argparse
import csv
import hashlib
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "artifacts/evaluation/medicine-crosswalk"
NETMEDS = ROOT / "data/references/raw/v2/kaggle_drowsyng/medicines.csv"
AZ = ROOT / "data/references/raw/v2/kaggle/A_Z_medicines_dataset_of_India.csv"
HF = ROOT / "data/references/raw/v2/hf_dmedhi/train-00000-of-00001.parquet"
CORPUS = ROOT / "data/references/releases/aster-v2-netmeds-r2-2026-10-07/records.jsonl"
SOURCE_HASHES = {
    NETMEDS: "d2efadab6cfba2b5f713126c7b5dbccffd4698dee8fd2ffb795bbe7ba28c433e",
    AZ: "f89c1cdea39c615151201f15a99082e83c1aac0cd41a742d0f0c3a511c87a2d7",
    HF: "8d6d4f5e19ce637093183c246829247dcfa6a2373082f8a2b000e00b0146bee2",
}
FORM_WORDS = {
    "tablet", "capsule", "injection", "suspension", "solution", "syrup", "drop",
    "cream", "gel", "ointment", "spray", "powder", "lotion", "inhaler", "sachet",
    "patch", "suppository", "soap", "shampoo", "expectorant", "softgel", "infusion",
    "lozenge", "granule", "rotacap", "respule", "nebule",
}
PLURALS = {word + "s": word for word in FORM_WORDS}
PLURALS["suppositories"] = "suppository"
PACK = re.compile(r"\s+\d+(?:\.\d+)?\s*(?:['’]s|s|ml|gm|g|kg|litre|liter)\s*$", re.I)
AMOUNT = re.compile(
    r"^(.+?)\s*\(?\s*(\d+(?:\.\d+)?)\s*(mcg|mg|gm|g|iu|units?|%)"
    r"\s*(?:/\s*(\d+(?:\.\d+)?)?\s*(ml|g|mg))?\s*(w/w|w/v|v/v)?\s*\)?$", re.I
)
METHODS = ["exact_name", "case_whitespace_name", "source_text_alias", "pack_or_unit_normalized_name", "brand_variant_candidate", "unmatched"]


def literal_key(value):
    return " ".join(value.casefold().split())


def tokens(value):
    value = unicodedata.normalize("NFKC", value).casefold().replace("’", "'")
    value = re.sub(r"(?<=\d)\s*(mcg|mg|gm|ml|iu|kg|g)\b", r" \1", value)
    return [PLURALS.get(word, word) for word in re.findall(r"[a-z]+|\d+(?:\.\d+)?", value)]


def forms(value):
    return sorted(set(tokens(value)) & FORM_WORDS)


def pack_free(value):
    # Removal is a candidate-generating name transform, not a formulation assertion.
    if forms(value):
        return PACK.sub("", value).strip()
    return value


def product_key(value):
    # Keep meaningful punctuation in brand names; only unit spacing/plurals change.
    value = unicodedata.normalize("NFKC", pack_free(value)).casefold().replace("’", "'")
    value = re.sub(r"(?<=\d)\s*(mcg|mg|gm|ml|iu|kg|g)\b", r" \1", value)
    value = re.sub(r"\b[a-z]+\b", lambda m: PLURALS.get(m[0], m[0]), value)
    return " ".join(value.split())


def brand_key(value):
    # Preserve junior/SR/CR/SF, route, flavour and all other alphabetic qualifiers.
    excluded = FORM_WORDS | {"mcg", "mg", "gm", "g", "ml", "iu", "kg", "w", "v"}
    return " ".join(word for word in tokens(pack_free(value)) if not word[0].isdigit() and word not in excluded)


@lru_cache(maxsize=200_000)
def composition_signature(value):
    value = re.sub(r"^\s*Generic Name\s*", "", value, flags=re.I)
    value = re.split(r"\bAlso Known As:", value, flags=re.I)[0].strip()
    if not value:
        return None
    signature = []
    for component in value.split("+"):
        match = AMOUNT.fullmatch(component.strip())
        if not match:
            return None  # Never ignore an unknown extra ingredient or quantity.
        ingredient, amount, unit, denominator, denominator_unit, basis = match.groups()
        ingredient = literal_key(ingredient.strip().rstrip("("))
        if not ingredient:
            return None
        signature.append((
            ingredient, str(Decimal(amount).normalize()), unit.casefold(),
            str(Decimal(denominator or "1").normalize()) if denominator_unit else "",
            (denominator_unit or "").casefold(), (basis or "").casefold(),
        ))
    return tuple(sorted(signature))  # Multiplicity is preserved; no dose summing.


def compare_composition(source, target):
    left, right = composition_signature(source), composition_signature(target)
    if left is None or right is None:
        return "unavailable_or_unparsed"
    if left == right:
        return "reported_fields_agree"
    if Counter(left) < Counter(right):
        return "source_subset_only"
    if {part[0] for part in left} == {part[0] for part in right}:
        return "same_ingredients_amount_or_basis_differs"
    return "ingredient_strings_differ"


class MatchIndex:
    def __init__(self, products):
        self.exact = defaultdict(set)
        self.normal = defaultdict(set)
        self.alias = defaultdict(set)
        self.product = defaultdict(set)
        self.brand = defaultdict(set)
        for row in products:
            number, name = row["row"], row["name"]
            self.exact[name].add(number)
            self.normal[literal_key(name)].add(number)
            for identity in [name, *row.get("aliases", [])]:
                if identity != name:
                    self.alias[literal_key(identity)].add(number)
                self.product[product_key(identity)].add(number)
                key = brand_key(identity)
                if key:
                    self.brand[key].add(number)

    def match(self, name):
        for method, lookup, key in [
            ("exact_name", self.exact, name),
            ("case_whitespace_name", self.normal, literal_key(name)),
            ("source_text_alias", self.alias, literal_key(name)),
            ("pack_or_unit_normalized_name", self.product, product_key(name)),
            ("brand_variant_candidate", self.brand, brand_key(name)),
        ]:
            if key and key in lookup:
                return method, sorted(lookup[key])
        return "unmatched", []


def review_flags(source, target, source_conflict, candidate_count):
    flags = []
    if source_conflict:
        flags.append("source_composition_conflict")
    if candidate_count > 1:
        flags.append("multiple_netmeds_candidates")
    left, right = forms(source), forms(target)
    if not left or not right:
        flags.append("dosage_form_unspecified")
    elif left != right:
        flags.append("dosage_form_differs")
    if len(left) > 1 or len(right) > 1:
        flags.append("multiple_form_words_require_review")
    def numbers(value):
        return set(re.findall(r"\d+(?:\.\d+)?", pack_free(value)))
    if numbers(source) != numbers(target):
        flags.append("numeric_name_tokens_differ")
    if PACK.search(source) and PACK.search(target) and literal_key(PACK.search(source)[0]) != literal_key(PACK.search(target)[0]):
        flags.append("package_size_strings_differ")
    return flags


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_products():
    identities = {}
    with CORPUS.open(encoding="utf-8") as handle:
        for line in handle:
            if "Product identity (CSV fields)" in line:
                row = json.loads(line)
                if row["source_type"] == "retailer_monograph":
                    identities[row["entity"]] = row
    products = []
    with NETMEDS.open(encoding="utf-8-sig", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle), 1):
            identity = identities[row["med_name"]]
            products.append({
                "row": number, "name": row["med_name"], "url": row["med_url"],
                "generic": row["generic_name"], "manufacturer": row["drug_manufacturer"],
                "aliases": identity["aliases"], "source_id": identity["source_id"],
            })
    assert len(products) == len(identities) == 23939
    return products


def read_groups(dataset):
    groups = defaultdict(list)
    if dataset == "az_india":
        with AZ.open(encoding="utf-8-sig", newline="") as handle:
            for number, row in enumerate(csv.DictReader(handle), 1):
                composition = "+".join(row[key].strip() for key in ["short_composition1", "short_composition2"] if row[key].strip())
                groups[row["name"]].append({
                    "row": number, "id": row["id"], "composition": composition,
                    "manufacturer": row["manufacturer_name"], "package": row["pack_size_label"],
                })
    else:
        for number, row in enumerate(pq.read_table(HF).to_pylist(), 1):
            groups[row["name"]].append({"row": number, "id": str(number), "composition": row["composition"]})
    return groups


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def match_groups(dataset, groups, index, products, output, reverse):
    counts, compositions, flags_count = Counter(), Counter(), Counter()
    matched_rows = pair_count = unique_target = source_conflicts = clean_names = 0
    examples = []
    with (output / f"{dataset}_crosswalk.jsonl").open("w", encoding="utf-8") as raw, (output / f"{dataset}_name_summary.csv").open("w", encoding="utf-8-sig", newline="") as flat:
        writer = csv.writer(flat)
        writer.writerow(["source_name", "source_rows", "method", "netmeds_candidates", "composition_conflict", "all_variants_reported_fields_agree_targets"])
        for name, rows in sorted(groups.items()):
            variants = sorted({row["composition"] for row in rows})
            conflict = len({literal_key(value) for value in variants}) > 1
            source_conflicts += conflict
            method, numbers = index.match(name)
            counts[method] += 1
            matched_rows += len(rows) if numbers else 0
            unique_target += len(numbers) == 1
            results, agreements = [], 0
            for number in numbers:
                target = products[number - 1]
                outcomes = [compare_composition(value, target["generic"]) for value in variants]
                flags = review_flags(name, target["name"], conflict, len(numbers))
                if method == "brand_variant_candidate":
                    flags.append("brand_only_review_candidate")
                if any(value != "reported_fields_agree" for value in outcomes):
                    flags.append("composition_requires_review")
                all_agree = not conflict and all(value == "reported_fields_agree" for value in outcomes)
                agreements += all_agree
                pair_count += 1
                compositions.update(outcomes)
                flags_count.update(flags)
                reverse[number][dataset]["any"] += 1
                if method != "brand_variant_candidate":
                    reverse[number][dataset]["name_specific"] += 1
                    if all_agree and not flags:
                        reverse[number][dataset]["unflagged_field_agreement"] += 1
                results.append({
                    "netmeds_row": number, "netmeds_source_id": target["source_id"],
                    "netmeds_name": target["name"], "netmeds_url": target["url"],
                    "netmeds_reported_generic": target["generic"],
                    "composition_comparisons": [{"source_composition": v, "status": status} for v, status in zip(variants, outcomes)],
                    "review_flags": flags, "clinical_equivalence_verified": False,
                })
            if len(numbers) == 1 and results and not results[0]["review_flags"]:
                clean_names += 1
            record = {
                "dataset": dataset, "source_name": name, "source_rows": [row["row"] for row in rows],
                "source_ids": [row["id"] for row in rows], "source_compositions": variants,
                "source_manufacturers": sorted({row.get("manufacturer", "") for row in rows} - {""}),
                "source_packages": sorted({row.get("package", "") for row in rows} - {""}),
                "source_composition_conflict": conflict, "name_match_method": method,
                "candidate_count": len(numbers), "candidates": results, "runtime_enabled": False,
            }
            raw.write(json.dumps(record, ensure_ascii=False) + "\n")
            writer.writerow([name, len(rows), method, len(numbers), conflict, agreements])
            if name in {"Ascoril LS Syrup", "Ascoril LS Junior Syrup", "Ascoril LS Drops", "Dolo 650 Tablet", "Augmentin 625 Duo Tablet", "Basalog 100IU/ml Injection", "Gestone Injection", "Scabiped Lotion"}:
                examples.append(record)
    write_json(output / f"{dataset}_examples.json", examples)
    total = len(groups)
    assert sum(counts.values()) == total
    return {
        "source_rows": sum(len(rows) for rows in groups.values()), "unique_exact_names": total,
        "name_methods": {method: counts[method] for method in METHODS},
        "names_with_any_candidate": total - counts["unmatched"],
        "names_with_name_specific_candidate": total - counts["unmatched"] - counts["brand_variant_candidate"],
        "names_with_one_candidate": unique_target,
        "names_with_multiple_candidates": total - counts["unmatched"] - unique_target,
        "source_rows_with_any_candidate": matched_rows, "candidate_pairs": pair_count,
        "names_with_conflicting_reported_composition_strings": source_conflicts,
        "unique_name_specific_candidates_with_unflagged_field_agreement": clean_names,
        "composition_comparison_counts_per_candidate_and_source_variant": dict(compositions),
        "review_flag_counts_per_candidate_pair": dict(flags_count),
        "clinical_equivalence_accuracy": None, "runtime_enabled": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output already contains results; choose a new directory")
    args.output.mkdir(parents=True, exist_ok=True)
    begin = time.perf_counter()
    artifacts = []
    for path, expected in SOURCE_HASHES.items():
        digest = sha256(path)
        if digest != expected:
            raise ValueError(f"Raw snapshot changed: {path.name}")
        artifacts.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest, "bytes": path.stat().st_size})
    csv.field_size_limit(10_000_000)
    products = read_products()
    index = MatchIndex(products)
    reverse = defaultdict(lambda: defaultdict(Counter))
    summaries = {}
    for dataset in ["az_india", "hf_india"]:
        groups = read_groups(dataset)
        summaries[dataset] = match_groups(dataset, groups, index, products, args.output, reverse)
        del groups
        print(dataset, json.dumps(summaries[dataset]["name_methods"]), flush=True)
    coverage = {}
    for dataset in ["az_india", "hf_india"]:
        coverage[dataset] = {
            category: sum(bool(reverse[row["row"]][dataset][category]) for row in products)
            for category in ["any", "name_specific", "unflagged_field_agreement"]
        }
    coverage["both_name_specific"] = sum(all(reverse[row["row"]][d]["name_specific"] for d in summaries) for row in products)
    coverage["either_name_specific"] = sum(any(reverse[row["row"]][d]["name_specific"] for d in summaries) for row in products)
    with (args.output / "netmeds_reverse_coverage.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["netmeds_row", "source_id", "netmeds_name", "az_name_specific_names", "hf_name_specific_names", "az_brand_or_name_candidates", "hf_brand_or_name_candidates"])
        for row in products:
            refs = reverse[row["row"]]
            writer.writerow([row["row"], row["source_id"], row["name"], refs["az_india"]["name_specific"], refs["hf_india"]["name_specific"], refs["az_india"]["any"], refs["hf_india"]["any"]])
    result = {
        "completed_utc": datetime.now(timezone.utc).isoformat(), "seconds": time.perf_counter() - begin,
        "master_products": len(products), "datasets": summaries, "master_coverage": coverage,
        "raw_artifacts": artifacts, "identity_alias_corpus": {"path": CORPUS.relative_to(ROOT).as_posix(), "sha256": sha256(CORPUS)},
        "matcher_sha256": sha256(Path(__file__).resolve()), "clinical_equivalence_accuracy": None,
        "scope": "Offline candidate links only. Runtime corpus, aliases, OCR and sources are not changed.",
        "limitations": [
            "Name-specific links can still be ambiguous across packs or contain field differences.",
            "Brand candidates preserve variants but may differ in dosage form or strength; all require review.",
            "Reported-field agreement is literal after case/whitespace/order/decimal formatting normalization, not clinical verification.",
            "No ingredient synonyms or mass-unit conversions are inferred; concentrations retain denominators and percent bases.",
            "A-Z has only two composition fields and may omit ingredients; subset agreement is reported separately.",
            "Manufacturer strings and source package metadata are retained, not used to establish equivalence.",
            "The input tables overlap and do not constitute independent clinical confirmation.",
        ],
    }
    write_json(args.output / "summary.json", result)
    write_report(result, args.output)
    print(json.dumps({"coverage": coverage, "seconds": result["seconds"]}, indent=2))


def write_report(result, output):
    rel = output.relative_to(ROOT).as_posix()
    lines = [
        "# Aster medicine dataset crosswalk",
        "",
        f"Matched both Indian datasets to the **{result['master_products']:,}-product Netmeds snapshot**. Run: {result['completed_utc']}.",
        "",
        "**These are offline candidate links, not verified clinical equivalences or new runtime aliases.** "
        "The raw datasets and Aster's active clinical library are preserved. Names, source rows/IDs, compositions, candidate products and review flags remain traceable.",
        "",
        "| Measure — unique exact source names | A-Z India | Hugging Face India |",
        "|---|---:|---:|",
    ]
    az, hf = result["datasets"]["az_india"], result["datasets"]["hf_india"]
    for label, key in [("Input rows", "source_rows"), ("Unique exact source names", "unique_exact_names")]:
        lines.append(f"| {label} | {az[key]:,} | {hf[key]:,} |")
    for method in METHODS:
        lines.append(f"| {method.replace('_', ' ')} | {az['name_methods'][method]:,} | {hf['name_methods'][method]:,} |")
    for label, key in [("Any name or brand candidate", "names_with_any_candidate"), ("Name-specific candidate (excludes brand-only)", "names_with_name_specific_candidate"), ("Exactly one candidate", "names_with_one_candidate"), ("Multiple candidates", "names_with_multiple_candidates"), ("Source names with composition-string conflicts", "names_with_conflicting_reported_composition_strings"), ("Unique candidate with reported field agreement and no flags", "unique_name_specific_candidates_with_unflagged_field_agreement")]:
        lines.append(f"| {label} | {az[key]:,} | {hf[key]:,} |")
    lines += [
        "",
        "Methods are mutually exclusive per source name, tried in table order. Counts use distinct exact source names, not source rows or new medicines. "
        "Names with one candidate still require evidence review. The final row measures syntactic field agreement only; it is not a clinical accuracy score.",
        "",
        "## How the comparison works",
        "",
        "1. Compare exact names, then case/whitespace names, then aliases already extracted from Netmeds source text.",
        "2. Compare candidate keys after trailing-pack removal and unit-space/plural-form normalization. Strength numbers and release/variant qualifiers remain.",
        "3. Generate review candidates with exact brand/qualifier keys while ignoring numbers and form words. Junior, SR/CR/SF, route and flavour tokens remain. No fuzzy spelling search is used.",
        "4. Preserve every candidate; flag ambiguous targets, differing forms/numbers, incomplete compositions and source conflicts. No first-candidate selection occurs.",
        "5. Compare reported ingredient/amount strings with concentrations intact. No synonym, concentration, unit conversion or missing-ingredient repair is applied.",
        "",
        "The conservative matcher can miss equivalent products with different spellings, qualifiers or units. "
        "A detected difference is a source-string difference, not proof that an ingredient or label is medically wrong. "
        "A-Z's two composition fields can be incomplete, so matching a subset never establishes the complete ingredient list.",
        "",
        "## Netmeds master coverage",
        "",
        "| Unique Netmeds rows reached | A-Z India | Hugging Face India |",
        "|---|---:|---:|",
    ]
    coverage = result["master_coverage"]
    for key in ["any", "name_specific", "unflagged_field_agreement"]:
        lines.append(f"| {key.replace('_', ' ')} | {coverage['az_india'][key]:,} | {coverage['hf_india'][key]:,} |")
    lines += [
        "",
        f"Both Indian datasets have name-specific candidates for **{coverage['both_name_specific']:,}** master products; "
        f"at least one does for **{coverage['either_name_specific']:,}**. Candidate coverage is not independently verified coverage.",
        "",
        "## Reported composition comparisons",
        "",
        "Counts below are per candidate product and distinct source composition string; several comparisons can come from one source name.",
        "",
        "| Outcome | A-Z India | Hugging Face India |",
        "|---|---:|---:|",
    ]
    outcomes = sorted(set(az["composition_comparison_counts_per_candidate_and_source_variant"]) | set(hf["composition_comparison_counts_per_candidate_and_source_variant"]))
    for status in outcomes:
        lines.append(f"| {status.replace('_', ' ')} | {az['composition_comparison_counts_per_candidate_and_source_variant'].get(status,0):,} | {hf['composition_comparison_counts_per_candidate_and_source_variant'].get(status,0):,} |")
    lines += ["", "## Ascoril LS example", ""]
    examples = json.loads((output / "hf_india_examples.json").read_text(encoding="utf-8"))
    example = next(row for row in examples if row["source_name"] == "Ascoril LS Syrup")
    for candidate in example["candidates"]:
        lines.append(f"- `{example['source_name']}` → `{candidate['netmeds_name']}`: {', '.join(candidate['review_flags']) or 'no syntactic flags'}; "
                     f"composition outcomes {', '.join(c['status'] for c in candidate['composition_comparisons'])}.")
    lines += [
        "",
        "The Syrup/Expectorant naming gap can be linked for review. It is not resolved as a runtime alias. "
        "The A-Z record omits the third ingredient supplied by the HF and Netmeds rows; "
        "HF reports `/5ml` while the Netmeds generic field omits that denominator. "
        "Those differences must be checked against current product information before any formulation equivalence is asserted.",
        "",
        "## Files and reproducibility",
        "",
        f"- [Summary]({rel}/summary.json).",
        f"- [A-Z full crosswalk]({rel}/az_india_crosswalk.jsonl) and [name summary CSV]({rel}/az_india_name_summary.csv).",
        f"- [HF full crosswalk]({rel}/hf_india_crosswalk.jsonl) and [name summary CSV]({rel}/hf_india_name_summary.csv).",
        f"- [Netmeds reverse coverage CSV]({rel}/netmeds_reverse_coverage.csv).",
        f"- [Selected A-Z examples]({rel}/az_india_examples.json), [HF examples]({rel}/hf_india_examples.json).",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe scripts/match_medicine_datasets.py --output artifacts/evaluation/NEW_CROSSWALK_RUN",
        ".\\.venv\\Scripts\\python.exe -m pytest -q tests/test_medicine_crosswalk.py",
        "```",
        "",
        f"Run took {result['seconds']:.2f} seconds. Raw snapshot, alias corpus and matcher hashes are recorded in the summary. "
        "No medical factual accuracy or clinical equivalence metric is claimed. Source licensing/review metadata stays separate: "
        "matching another table does not transfer its permission basis or approval status.",
    ]
    (ROOT / "MEDICINE_DATASET_CROSSWALK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
