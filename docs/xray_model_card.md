# Chest research model card

## Intended role

Experimental integration of TorchXRayVision `densenet121-res224-all`, with only
Cardiomegaly, Effusion and Lung Opacity selected for display. Scores describe
model outputs, not diagnoses, calibrated probabilities or diagnostic confidence.
No binary normality flag or patient advice. No clinically validated release.

## Inputs

Reviewed, permitted, de-identified 8-bit PNG/JPEG adult frontal AP/PA chest
images selected by opaque asset ID. Reliable external metadata and operator
review are necessary. No arbitrary uploads, DICOM, pediatric/lateral images,
screenshots, film photos, CT or MRI. Hash verification is repeated before inference.
Dimensions, aspect ratio, dynamic range, saturation and blur are technical
signals; they cannot certify anatomical completeness, positioning or exposure.

## Preprocessing and outputs

8-bit grayscale → XRV normalization with maximum 255 → XRV center crop → XRV
224 resize → float32 tensor [1,1,224,224], finite → eval/inference mode on CPU.
No flips or ImageNet normalization. Output ordering comes from the actual model.
The adapter expects pretrained operating-point rescaling and checks its presence;
there is no second sigmoid, softmax or score-to-confidence conversion.
Weight SHA, library version, full label list and transform version are recorded
by explicit online setup. Missing or changed assets fail closed.

## Provenance and evaluation

The all checkpoint combines multiple chest datasets; popular public evaluation
data may overlap training. Review the upstream
[model documentation](https://mlmed.org/torchxrayvision/models.html),
[library](https://github.com/mlmed/torchxrayvision), and
[model card](https://huggingface.co/torchxrayvision/densenet121-res224-all).
Library licensing does not grant permission to redistribute its training or
evaluation images. Verify checkpoint and dataset terms independently.

The local installation now caches the publisher's checkpoint at Hugging Face
revision `588eadcc6a744da71f8dce768bc974ec629443f5`. Its SHA-256 was matched to
the publisher's LFS metadata before loading; the revision, source, byte count,
library version and full label order are recorded in `configs/xray_weights.json`.
Two NIH ChestX-ray14 version 3 samples with source CSV ages 58 and 81 and PA
views have been reviewed and registered as **demo**, with input hashes and
provenance. They are not independent test data: NIH is part of the all model's
training sources. See `docs/xray_setup.md` and the acquisition record.

Real CPU inference and one real browser attachment workflow were checked. No
imaging accuracy, calibration, sensitivity/specificity, independent
generalization, subgroup performance or clinical utility is measured.
`calibrated_probability` stays null.
The evaluation CLI now binds predeclared thresholds to checkpoint and dataset
hashes, rejects partition leakage/duplicate images, excludes uncertain labels,
and reports AUROC, average precision, threshold metrics and patient-bootstrap
intervals when defined. Reliability bins describe research scores; they do not
calibrate probabilities. Failed preflight saves an explicit `not_ready` result,
and existing output directories cannot be reused.

An audit of the packaged CheXpert training table (64,540 patients) against the
expert test labels (500 patients) found zero shared identifiers. This establishes
only same-namespace metadata separation. The full checkpoint-specific training
inventory, other-source overlap and image duplicates remain unresolved.
CheXlocalize/CheXpert test images require provider access and input review.
Independent diagnostic evaluation remains pending. See
[the research evaluation report](../PCOM_RESEARCH_IMPROVEMENTS.md).
