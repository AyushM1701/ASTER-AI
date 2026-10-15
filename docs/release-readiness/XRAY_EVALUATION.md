# X-ray assistance — evaluation (15 October 2026)

**Status: research-use assistance for adult frontal chest X-rays. Not clinically validated.**
No radiologist labelled any image for this evaluation; no claim of diagnostic accuracy is made.

## What ships

- **Upload pathway:** any image classified as an X-ray in a chat can be analysed after the user confirms
  it is an adult chest X-ray. Curated hash registration remains for the bundled demo and for evaluation.
- **Gates, applied before any score is shown:**
  1. Image quality: size, proportions, dynamic range, saturation.
  2. Colour photograph check.
  3. Out-of-distribution check: the TorchXRayVision ResNet autoencoder's reconstruction error.
  4. Frontal-vs-lateral view classifier (chestViewSplit ResNet-50).
  5. Required adult attestation.
- **Scores:** TorchXRayVision DenseNet-121 `densenet121-res224-all`, operating-point-normalised research
  scores for Cardiomegaly, Effusion and Lung Opacity.
  - No normality verdict.
  - No heatmap or lesion location.
  - Each finding term gets a source-linked explanation from the library.
- **Runtime:** ONNX Runtime with ported TorchXRayVision preprocessing; no torch.
  - The exports matched the torch checkpoints on 15 real images. Maximum absolute differences: preprocessing 0, scores 7.5e-7,
    autoencoder error 4.8e-8, view probability 1.4e-6 (`packaging/export_xray_onnx.py`).

## Data (local evaluation only; not redistributed)

| Source | Use | Terms |
|---|---|---|
| NLM Montgomery County CXR set (138 images, 58 TB / 80 normal, ages) | In scope (adults), pediatric (children) | Deidentified, IRB-exempt public release; "do not share outside your research group" |
| NLM Shenzhen CXR set (220 sampled of 662: all children + random adults) | In scope (adults), pediatric (children) | As above |
| NIH ChestX-ray14 demo images (2) | In scope | CC0 (Kaggle) |
| Wikimedia Commons (94 files): lateral chest, dental panoramic, hand, skull, head CT, brain MRI, photos, mixed chest | Out of scope | Licence recorded per file (CC/PD) |

**Split.** Random 50/50 file-level split (seed 1014); there is one image per patient in the NLM sets. Thresholds were chosen on
the calibration half by keeping ≥97% of in-scope calibration images while rejecting the most out-of-scope ones.
Results below are for the **held-out test half**.

**Contamination.** As far as documented, the DenseNet "all" model was trained on NIH, CheXpert, MIMIC, PadChest, Google,
OpenI and RSNA data, not on Montgomery or Shenzhen. The two NIH demo images may be in its training data.

## Gate results (held-out test half)

| Group | Accepted / n |
|---|---|
| Montgomery adults (in scope) | 56 / 60 |
| Shenzhen adults (in scope) | 94 / 94 |
| NIH demo (in scope) | 1 / 1 |
| **In-scope acceptance** | **151 / 155 = 97.4%** |
| Lateral chest | 1 / 9 accepted |
| Dental panoramic | 0 / 10 |
| Hand X-ray | 0 / 3 |
| Skull/mandible X-ray | 0 / 8 |
| Head CT | 0 / 8 |
| Brain MRI | 0 / 1 |
| Photos | 0 / 7 |
| **Out-of-scope rejection** | **45 / 46 = 97.8%** |
| Children's chest X-rays (Montgomery + Shenzhen, both halves) | accepted 96% |

**Limits.** Image gates do **not** detect children: the adult attestation is the control. One lateral chest film passed the gates.
The out-of-scope sample is small (46 test images), and other modalities, devices and phone photos of films are untested.
Thresholds: `configs/xray_gates.json`. Full results: `evaluation/xray/gate-calibration.json`.

## Score sanity check (not an accuracy measure)

The model has no TB output. As a check that opacity-type scores rise on abnormal films, AUC was computed for
TB-labelled versus normal on 313 adult Montgomery and Shenzhen images:

- Lung Opacity: 0.84
- Consolidation: 0.81
- Nodule: 0.82
- Pleural thickening: 0.79
- Effusion: 0.76
- Cardiomegaly: 0.66

These figures do not establish the accuracy of any finding (`evaluation/xray/score-sanity.json`).

## Remaining gates

- Radiologist-labelled, held-out adult frontal chest X-rays with per-finding ground truth.
- Calibration of scores to probabilities; until then scores are not probabilities.
- Evaluation on phone photographs of films and on local devices and populations.
- Any other body region, view or modality needs its own model and evaluation.
