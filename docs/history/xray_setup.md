# Current local X-ray setup

On 2026-10-06, the existing adult frontal chest research adapter was enabled.
The running workspace is at http://127.0.0.1:8501/.

## Try the working chat flow

1. Use **Bring an X-ray** or the link icon in the chat.
2. Select `data/xray/nih-v3/00000001_000.png` or `00000002_000.png` from this project.
3. Choose **Attach to conversation**. The vision model routes the pixels, then
   the registered source hash authorizes specialist inference.
4. The conversation displays Effusion, Cardiomegaly and Lung Opacity scores.
   They are research outputs, not probabilities, diagnoses or a normality verdict.

Images with no reviewed registration remain unsupported. For a different image,
use `scripts/register_xray.py` with reliable adult/view/de-identification and
permitted-use metadata, as described in README. Restart Aster after registration.
The review flag is an attestation; classification alone cannot supply that review.

## Installed assets and provenance

- CPU PyTorch 2.14.1+cpu and torchvision 0.29.1+cpu from the official PyTorch index.
- TorchXRayVision 1.4.0 and its image dependencies from PyPI. The complete observed
  Windows Python 3.13 environment is frozen in `requirements-xray.lock.txt`;
  `pip check` reports no dependency conflicts.
- `densenet121-res224-all` from the publisher's Hugging Face repository at revision
  `588eadcc6a744da71f8dce768bc974ec629443f5`, file `model.pt`, 28,382,008 bytes.
  Published SHA-256:
  `56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899`.
  The bytes were verified **before** TorchXRayVision loaded the checkpoint and
  placed under the exact filename its cached loader expects.
- NIH ChestX-ray14 via Kaggle `nih-chest-xrays/data`, version **3**. Only two
  images, the CSV metadata and supplied README/FAQ were acquired, not the whole
  45 GB collection. The selected records specify ages 58 and 81, PA views, and
  separate patient groups. Both original images were inspected for supported
  input and visible identifiers; this was not a diagnostic quality assessment.
- Kaggle lists CC0 Public Domain. Supplied NIH FAQ Q04 permits unrestricted use
  with acknowledgment, original repository link and paper citation. Acquisition
  hashes are in `data/xray/nih-v3/acquisition.json`; registrations are in
  `configs/xray_assets.yaml`. Dataset labels were not supplied to inference.

NIH Clinical Center source: https://nihcc.app.box.com/v/ChestXray-NIHCC

Wang X, Peng Y, Lu L, Lu Z, Bagheri M, Summers RM. *ChestX-ray8: Hospital-scale
Chest X-ray Database and Benchmarks on Weakly-Supervised Classification and
Localization of Common Thorax Diseases*. IEEE CVPR, 2017, pp. 3462–3471.
https://arxiv.org/abs/1705.02315

No NIH endorsement is implied.

## Verification and limits

`artifacts/evaluation/xray-setup/live-api.json` records readiness, two real
CPU inferences, finite scores in the selected label order, null calibrated
probabilities, owned-result retrieval, foreign-session rejection and the
unregistered-image gate. The first cold inference took approximately 4.9 seconds;
the second took 0.27 seconds on this machine. This is not a performance benchmark.
`integrity.json` records rejection of intentionally incorrect checkpoint and
image manifest hashes, without altering the production assets.

The first sample was also attached with the browser's real file chooser and
returned a pixel-based X-ray classification and real specialist scores in chat.
The existing 76-test suite passed after installation. A screenshot is saved in
`artifacts/evaluation/xray-setup/live-chat.png`.

These demonstrations establish integration only. NIH was used to train this
checkpoint, so these images cannot establish independent generalization.
The dataset's NLP report labels are imperfect, and 'No Finding' does not mean
normal. No training, fine-tuning, calibration or clinical validation was done.
The enabled model still follows the scope in `docs/xray_model_card.md`.

No model download occurs in API requests. Changes to checkpoint bytes, library
version, label order or registered image bytes invalidate the cached setup.
