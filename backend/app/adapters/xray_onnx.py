"""Torch-free X-ray research model + input gates (ONNX Runtime + scikit-image).

Preprocessing is ported verbatim from TorchXRayVision 1.4.0 (Apache-2.0):
normalize(maxval=255) -> centre crop -> skimage resize to 224 (mode='constant',
preserve_range=True). Network outputs were checked against the original torch
checkpoints at export (see data/models/xray/onnx/export-manifest.json).
"""
import hashlib
import json
import warnings
from pathlib import Path

import numpy as np

from backend.app.adapters.xray_gates import colourfulness

SELECTED = ("Cardiomegaly", "Effusion", "Lung Opacity")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def preprocess(image, size=224):
    from skimage.transform import resize

    pixels = np.asarray(image.convert("L"), dtype=np.float32)
    pixels = (2 * (pixels / 255.0) - 1.0) * 1024
    pixels = pixels[None, ...]
    _, y, x = pixels.shape
    crop = min(y, x)
    start_x, start_y = x // 2 - crop // 2, y // 2 - crop // 2
    pixels = pixels[:, start_y:start_y + crop, start_x:start_x + crop]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pixels = resize(pixels, (1, size, size), mode="constant", preserve_range=True).astype(np.float32)
    tensor = pixels[None, ...]
    if tensor.shape != (1, 1, size, size) or not np.isfinite(tensor).all():
        raise ValueError("Invalid preprocessing tensor")
    return tensor


def op_norm(probabilities, thresholds):
    out = np.full_like(probabilities, 0.5)
    for i, threshold in enumerate(thresholds):
        if threshold is None:
            continue
        p = probabilities[..., i]
        out[..., i] = np.where(p < threshold, p / (threshold * 2), 1.0 - (1.0 - p) / ((1 - threshold) * 2))
    return out


class OnnxXray:
    model_id = "densenet121-res224-all"
    preprocessing_version = "xrv-8bit-center224-v1"
    score_semantics = "Operating-point-normalized research score; not a calibrated probability."

    def __init__(self, gates_config, weights_dir, threads=4):
        import onnxruntime as ort

        weights_dir = Path(weights_dir)
        self.config = json.loads(Path(gates_config).read_text(encoding="utf-8"))
        export = json.loads((weights_dir / "onnx" / "export-manifest.json").read_text(encoding="utf-8"))
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.log_severity_level = 3
        sessions = {}
        for name in ("densenet", "autoencoder", "view"):
            meta = export["files"][name]
            path = weights_dir / meta["file"]
            if not path.is_file() or _sha256(path) != meta["sha256"]:
                raise ValueError(f"{name} model missing or hash mismatch")
            sessions[name] = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        self.sessions = sessions
        self.labels = export["labels"]
        self.thresholds_op = export["op_threshs"]
        self.weight_hash = export["source"]["classifier"]["sha256"]
        self.thresholds = self.config["thresholds"]

    def _run(self, name, tensor):
        return self.sessions[name].run(None, {"image": tensor})[0]

    def predict(self, image, tensor=None):
        tensor = preprocess(image) if tensor is None else tensor
        logits = self._run("densenet", tensor)
        scores = op_norm(1 / (1 + np.exp(-logits)), self.thresholds_op)
        if scores.shape != (1, len(self.labels)) or not np.isfinite(scores).all():
            raise ValueError("Invalid model output")
        return [{"name": label, "score": float(scores[0, i]), "calibrated_probability": None}
                for i, label in enumerate(self.labels) if label in SELECTED]

    def all_scores(self, image, tensor=None):
        tensor = preprocess(image) if tensor is None else tensor
        scores = op_norm(1 / (1 + np.exp(-self._run("densenet", tensor))), self.thresholds_op)[0]
        return {label: float(scores[i]) for i, label in enumerate(self.labels) if label}

    def measure(self, image, tensor=None):
        tensor = preprocess(image) if tensor is None else tensor
        ae_error = float(self._run("autoencoder", tensor)[0])
        logits = self._run("view", tensor)[0]
        probs = np.exp(logits - logits.max())
        probs = probs / probs.sum()
        return {"ae_error": ae_error, "frontal_probability": float(probs[0]), "lateral_probability": float(probs[1]),
                "colourfulness": colourfulness(image)}

    def assess(self, image, quality, adult_attested):
        from backend.app.adapters.xray_gates import XrayGates

        measures = self.measure(image)
        return XrayGates.decide(self.thresholds, self.config, image, quality, measures, adult_attested)
