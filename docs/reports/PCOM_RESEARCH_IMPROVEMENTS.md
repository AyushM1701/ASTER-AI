# Aster: PCOM research resources and X-ray evaluation

Report date: **8 October 2026 (India)**. Machine-readable artifacts record UTC timestamps.

The evaluation tooling and public metadata audit are implemented. Real CPU inference passed on the two installed demo images. **Independent diagnostic performance and probability calibration have not been measured.** The candidate test images require provider access, input review and complete training-overlap evidence.

## What was implemented

- `scripts/audit_xray_sources.py` snapshots public upstream documentation and expert test labels at pinned Git revisions, with SHA-256 hashes. It compares CheXpert patient identifiers and saves a research source register.
- `scripts/prepare_xray_protocol.py` creates a versioned protocol bound to the exact dataset manifest and installed checkpoint. Independent protocols begin with unresolved overlap; generating a protocol does not certify independence.
- `scripts/evaluate_xray.py` checks protocol bindings, checkpoint bytes, image provenance, supported inputs, duplicate image hashes, patient grouping and test-only partitions before evaluation.
- The evaluator calculates per-finding AUROC and average precision (the reported AUPRC convention), sensitivity, specificity, precision and confusion counts at predeclared thresholds. Missing and uncertain labels are excluded per finding.
- Confidence intervals resample complete patient clusters with replacement. Undefined denominators stay null. Intervals are withheld below 20 distinct patients or when fewer than 80% of requested replicates are defined. These are engineering guards, not sufficient clinical sample-size criteria.
- Score reliability bins and false-positive/false-negative examples are saved for eligible labelled cohorts. Reliability bins describe research scores; no probability calibrator is fitted.
- Each run requires a fresh output directory. Failed input/image checks save `preflight.json` with `not_ready`; inference errors save a failed summary. Successful runs record input/code/dependency hashes, package versions, seed and arguments.

The active model remains `densenet121-res224-all`, preprocessing `xrv-8bit-center224-v1`, checkpoint SHA-256 `56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899`. Its three displayed findings remain Cardiomegaly, Effusion and Lung Opacity. [TorchXRayVision documentation](https://mlmed.org/torchxrayvision/models.html) describes the operating-point normalization used by this checkpoint. Values are research scores, not disease probabilities.

## Training-source audit

The checkpoint filename identifies NIH, PadChest, CheXpert, MIMIC-CXR, NIH-Google, OpenI and RSNA/Kaggle source families. Published metadata and the pinned upstream training script do not establish the complete inventory for this exact checkpoint run. Reconstructing a split from current code alone would not prove the historical training split.

The public [CheXpert expert test labels](https://github.com/rajpurkarlab/cheXpert-test-set-labels) were compared against the training metadata packaged with the installed TorchXRayVision library.

| Audit measurement | Result |
| --- | ---: |
| Packaged CheXpert training rows | 223,414 |
| Distinct training patient IDs | 64,540 |
| Expert test studies | 500 |
| Distinct expert test patient IDs | 500 |
| Shared patient IDs in these two tables | **0** |

| Aster finding | Expert-label source column | Positive studies | Negative studies |
| --- | --- | ---: | ---: |
| Cardiomegaly | Cardiomegaly | 151 | 349 |
| Effusion | Pleural Effusion | 104 | 396 |
| Lung Opacity | Lung Opacity | 264 | 236 |

This comparison establishes separation only within the checked CheXpert identifier namespace. It does not exclude duplicates across sources, establish actual checkpoint membership or inspect image content. The public labels also lack age and AP/PA metadata needed by Aster's supported-input review. Label counts are metadata observations, not model scores.

Audit evidence: [audit.json](../../artifacts/evaluation/pcom-xray/source-audit/audit.json). Original snapshots and their revision/hash records are stored beside it. The packaged training CSV hash is `cdd70817ac2f13e464d2e35de78cd6831b10382c869c3824c35b44f55928becb`.

## Actual local inference results

Run: `artifacts/evaluation/pcom-xray/integration-verified/`. Two registered, reviewed NIH demo images were processed by the installed checkpoint on CPU. They have no ground-truth labels in this evaluation manifest and come from a training-source dataset.

| Demo asset | Cardiomegaly score | Effusion score | Lung Opacity score |
| --- | ---: | ---: | ---: |
| nih-v3-demo-01 | 0.609325 | 0.393224 | 0.392875 |
| nih-v3-demo-02 | 0.517685 | 0.453577 | 0.663342 |

These values demonstrate functioning inference only. They cannot determine whether a patient has a condition. `calibrated_probability` is null for every finding.

| Independent evaluation measure | Current result |
| --- | --- |
| AUROC / average precision | Not measured; null |
| Sensitivity / specificity / precision | Not measured; null |
| Patient-bootstrap diagnostic intervals | Not measured |
| Independent failure examples | Not available |
| Probability calibration | Not fitted |
| Subgroup performance / clinical utility | Not measured |

See [predictions](../../artifacts/evaluation/pcom-xray/integration-verified/predictions.json), [summary](../../artifacts/evaluation/pcom-xray/integration-verified/summary.json), [preflight](../../artifacts/evaluation/pcom-xray/integration-verified/preflight.json) and [reproducibility manifest](../../artifacts/evaluation/pcom-xray/integration-verified/run_manifest.json).

The pending independent protocol correctly refuses evaluation with the reason “Independent evaluation requires a documented training overlap exclusion review.” Its image manifest is also empty. See [saved not-ready result](../../artifacts/evaluation/pcom-xray/independent-preflight/preflight.json). Editing a review status without evidence does not resolve these requirements.

## Software verification

The complete test suite passed **180 tests**, with one existing FastAPI/Starlette test-client deprecation warning. The evaluation-specific suite passed **20 tests**. Ruff passed on the three evaluation/audit scripts and their test file. Read-only code review found the input failure handling and output reuse defects, which were reproduced with failing regression tests, fixed, and rechecked.

Mathematical fixtures verify AUROC = 0.75, average precision = 5/6 and TP/FN/FP/TN = 1/1/1/1 at a fixed 0.5 threshold. Those fixtures verify calculations; they are not medical image accuracy results. Other tests cover whole-patient bootstrap sampling with multiplicity, interval reproducibility, unknown labels, undefined metrics, invalid scores, bin boundaries, duplicate images, input binding, overlap gates and failure reports.

## Resources selected from the PCOM guide

The [PCOM AI datasets guide](https://libguides.pcom.edu/c.php?g=1386314&p=10554413) is a discovery directory. It is recorded as research provenance rather than ingested as medicine advice. The resulting [research source register](../../artifacts/evaluation/pcom-xray/source-audit/research-source-register.json) has `runtime_ingestion: false`.

| Resource | Useful role | Current limitation |
| --- | --- | --- |
| [Stanford CheXlocalize](https://aimi.stanford.edu/datasets/chexlocalize) | Priority candidate for expert-labelled chest imaging evaluation; includes the three relevant findings | Redivis image access requires an application; input and overlap review remain pending |
| [NIH expert labels](https://docs.cloud.google.com/healthcare-api/docs/resources/public-datasets/nih-chest) | Additional imaging research labels | NIH/Google sources are represented in the model; independence remains unresolved. Requester-pays cloud access is unsuitable for an assumed zero-cost download |
| [BRAX](https://physionet.org/content/brax/1.1.0/) | Possible external imaging cohort | Credentialed access, training/agreement requirements; NLP-derived labels need an explicit evaluation design |
| [WHO collections](https://www.who.int/data/collections) | Future public-health facts indexed by country, year and indicator | Population statistics do not supply medicine monographs or individual prescribing guidance |
| [MIMIC](https://mimic.mit.edu/docs/gettingstarted/) | Future clinical-text research | Credentialing, training and agreement required; historical clinical records are not current guidelines |

No gated images were downloaded, accounts created or provider agreements accepted. No clinical knowledge records were generated from patient records or a directory page.

## What is needed to run an independent benchmark

1. Apply for access at [Stanford's CheXlocalize Redivis dataset](https://stanford.redivis.com/datasets/efx9-5nspnbb4b). The access check showed metadata-only access and an “Apply for access” action. Review and accept the provider's research terms yourself; approval is controlled by the provider. [Stanford AIMI's data page](https://aimi.stanford.edu/data) describes research access and licensing.
2. After approval, obtain the permitted images and original metadata. Map study labels to eligible frontal AP/PA images; exclude lateral/pediatric or otherwise unsupported inputs. Record de-identification and supported-input review rather than inferring these from the image classifier.
3. Establish complete checkpoint-specific exclusion from training, including patient and duplicate-image checks across all relevant sources. If the inventory remains unavailable, select a checkpoint/cohort with evidence that can support independence, or explicitly label a run as potentially overlapping exploratory research.
4. Keep all images from a patient in one partition. Reserve separate development/calibration patients if thresholds or calibration will be fitted. Determine sample size and subgroup analysis before testing; the software's interval guards are not a study-design substitute.
5. Create a new reviewed asset manifest with source/license, image hashes, patient groups, binary labels and `partition: test`. Generate a new protocol and record the reviewer, rationale and overlap evidence. Do not modify the bound protocol after inspecting test results.
6. Run the frozen benchmark. Review failure examples and score reliability. Any probability calibration must be fitted on a separate eligible cohort and assessed on held-out patients before changing the app's output semantics.

## Commands

Run from the project directory. Output paths must be new for every evaluation.

```powershell
# Repeat demo inference, with diagnostic metrics withheld.
.venv\Scripts\python.exe scripts/evaluate_xray.py --dataset configs/xray_assets.yaml --protocol configs/benchmarks/nih-integration-protocol-v1.json --integration-only --output artifacts/evaluation/pcom-xray/demo-next-run

# Create a protocol after preparing a new permitted manifest.
.venv\Scripts\python.exe scripts/prepare_xray_protocol.py --dataset configs/benchmarks/reviewed-test.yaml --output configs/benchmarks/reviewed-test-protocol-v1.json

# After documenting overlap exclusion, check inputs without inference.
.venv\Scripts\python.exe scripts/evaluate_xray.py --dataset configs/benchmarks/reviewed-test.yaml --protocol configs/benchmarks/reviewed-test-protocol-v1.json --validate-only --output artifacts/evaluation/pcom-xray/test-preflight-v1

# Run the independent benchmark using a separate output directory.
.venv\Scripts\python.exe scripts/evaluate_xray.py --dataset configs/benchmarks/reviewed-test.yaml --protocol configs/benchmarks/reviewed-test-protocol-v1.json --bootstrap-repetitions 1000 --seed 17 --output artifacts/evaluation/pcom-xray/test-results-v1
```

`reviewed-test.yaml` and its protocol are future example filenames, not supplied test data. The existing `chexlocalize-pending` files intentionally remain unresolved. Aster's live chat, medicine references and English prescription OCR continue to use their existing configuration; this work adds research evaluation capability rather than retraining the model.
