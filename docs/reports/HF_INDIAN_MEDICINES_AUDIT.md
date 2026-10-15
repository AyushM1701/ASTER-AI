# Hugging Face Indian medicines — ingestion audit

Subsequent update: the user authorized secondary AI use with an unverified-data caution. A selected, crosswalk-checked subset is included in [Aster's secondary medicine layer](SECONDARY_MEDICINE_DATA.md). The audit below records the acquisition assessment; the full candidate catalogue remains unverified and is not automatically promoted.

Dataset [dmedhi/indian-medicines](https://huggingface.co/datasets/dmedhi/indian-medicines); pinned revision `a9f49cbc2f086110b455915ddacad136c7d4634e`. Audited 2026-10-07T13:50:24.076217+00:00.

Downloaded, checksum-verified and staged locally. **Not activated in Aster's clinical retrieval.** The exact-name candidate index is unverified, not connected to runtime retrieval or OCR repair. These measurements describe data integrity and overlap, not clinical accuracy.

| Check | Result |
|---|---:|
| Rows | 11,825 |
| Unique exact product names | 11,498 |
| Unique names after case/whitespace normalization | 11,498 |
| Extra rows repeating a name | 327 |
| Exact duplicate complete rows | 84 |
| Duplicate clinical fields ignoring image URL | 323 |
| Names with conflicting composition strings | 3 |
| Names with different clinical field strings | 4 |
| Rows containing an explicit unknown composition amount | 77 |
| Null / blank fields | 0 / 0 |
| Parquet checksum and exact schema | Passed |
| Images downloaded | 0 |
| Qualified clinical accuracy | Not measured |

The five columns are `name`, `composition`, `uses`, `side_effects`, `image_url`. Composition strings and short uses/side-effect fields could support product reference candidates after verification. They are incomplete medicine monographs: no contraindications, interactions, warnings, current product-label links, manufacturer identity or per-product review dates are supplied.

## Licence and provenance

The [pinned dataset card](https://huggingface.co/datasets/dmedhi/indian-medicines/blob/a9f49cbc2f086110b455915ddacad136c7d4634e/README.md) declares no licence and provides schema metadata without a source narrative. No licence file appears in the repository listing. This is missing evidence, not a conclusion that the dataset has no rights. Image links use `onemg.gumlet.io`; Tata 1mg origin is inferred from that host, not documented by the uploader. A similar mirror's licence cannot automatically be transferred to this repository. Hugging Face's verified commit marker concerns the commit, not medical review or content licensing. The upload was last modified 2024-12-24; that does not establish the clinical source date.

The user's prior verification/licensing confirmation was recorded for `drowsyng/medicines-dataset`. It has not been silently reused as an attestation for a different uploader and inferred upstream source.

## Exact-name conflicts

The following names have more than one composition string after whitespace/case normalization. This flags data inconsistency; it does not establish which composition is medically correct. All rows remain in the raw snapshot and the candidate index marks these names as conflicted:

- Basalog 100IU/ml Injection: source rows 1196, 1423.
- Gestone Injection: source rows 2885, 3151.
- Scabiped Lotion: source rows 9282, 9467.

Different clinical strings occur for: Basalog 100IU/ml Injection, Gestone Injection, Scabiped Lotion, Tegliptin Tablet. Differences may reflect units, incomplete amounts or wording; the audit does not treat them as proven clinical contradictions. Embedded `(NA)` amounts are retained as unknown, even though the composition field itself is nonblank.

## Overlap with Aster's other tables

| Source | Exact name overlap | Case/whitespace overlap | Names absent after normalization |
|---|---:|---:|---:|
| active_netmeds_csv | 6 | 7 | 11,491 |
| earlier_az_catalogue | 11,208 | 11,216 | 282 |

Overlap is based only on strings. Absence can reflect pack sizes, spellings and naming conventions; it is not a count of new medicines. No brand/ingredient/form equivalence or cross-source composition match was inferred.

## Ascoril LS and next ingestion step

This table contains separate exact names `Ascoril LS Syrup`, `Ascoril LS Junior Syrup` and `Ascoril LS Drops`. That may address the earlier Syrup-name gap after independent product verification. It does not establish equivalence to Netmeds' Expectorant entry; those names and concentrations must remain separate. Clinical promotion needs a recorded permission/source basis, conflict resolution against current product information, and a new versioned release with retrieval/abstention evaluation. All conflicting names should remain excluded from clinical evidence until resolved.

## Reproduce

The audit uses Aster's existing PyArrow and requests packages. No extra runtime dependency was installed:

```powershell
.\.venv\Scripts\python.exe scripts/audit_hf_indian_medicines.py --download
# Omit --download to audit the already downloaded snapshot offline.
```

The requested Hugging Face loader can load the same immutable version in an environment with `datasets` installed. This is loading reference data, not training Qwen. [Hugging Face documents the revision parameter](https://huggingface.co/docs/datasets/loading#hugging-face-hub):

```python
from datasets import load_dataset
ds = load_dataset(
    "dmedhi/indian-medicines",
    revision="a9f49cbc2f086110b455915ddacad136c7d4634e",
    split="train",
)
```

Parquet SHA-256: `8d6d4f5e19ce637093183c246829247dcfa6a2373082f8a2b000e00b0146bee2`.

[Machine-readable audit](../../data/knowledge_v2/hf_indian_medicines_audit.json), [unverified exact-name candidates](../../data/knowledge_v2/hf_indian_medicine_candidates.json), [audit script](../../scripts/audit_hf_indian_medicines.py).
