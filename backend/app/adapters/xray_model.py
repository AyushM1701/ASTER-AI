import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np


def preprocess(image):
    import torch
    import torchxrayvision as xrv

    pixels = np.asarray(image.convert("L"), dtype=np.float32)
    pixels = xrv.datasets.normalize(pixels, 255)[None, ...]
    pixels = xrv.datasets.XRayCenterCrop()(pixels)
    pixels = xrv.datasets.XRayResizer(224)(pixels)
    tensor = torch.from_numpy(np.asarray(pixels, dtype=np.float32))[None, ...]
    if tuple(tensor.shape) != (1, 1, 224, 224) or not torch.isfinite(tensor).all():
        raise ValueError("Invalid preprocessing tensor")
    return tensor


class XrayAdapter:
    model_id = "densenet121-res224-all"
    preprocessing_version = "xrv-8bit-center224-v1"
    score_semantics = "Operating-point-normalized research score; not a calibrated probability."

    def __init__(self, settings):
        import torchxrayvision as xrv

        manifest = json.loads(settings.xray_weights_manifest.read_text(encoding="utf-8"))
        if (
            manifest["model_id"] != self.model_id
            or manifest["preprocessing_version"] != self.preprocessing_version
            or manifest["library_version"] != importlib.metadata.version("torchxrayvision")
        ):
            raise ValueError("Model manifest version mismatch")
        path = Path(manifest["weights_path"])
        if not path.is_absolute():
            path = (settings.xray_weights_manifest.parent / path).resolve()
        expected_name = xrv.models.model_urls[self.model_id]["weights_url"].rsplit("/", 1)[-1]
        if not path.is_file() or path.name != expected_name:
            raise ValueError("Expected cached checkpoint is absent")
        self.weight_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if self.weight_hash != manifest["sha256"]:
            raise ValueError("Checkpoint hash mismatch")
        self.model = xrv.models.DenseNet(weights=self.model_id, cache_dir=str(path.parent))
        self.model.eval()
        self.labels = getattr(self.model, "pathologies", getattr(self.model, "targets", []))
        if not self.labels or list(self.labels) != manifest["labels"]:
            raise ValueError("Checkpoint label order mismatch")
        if getattr(self.model, "op_threshs", None) is None:
            raise ValueError("Expected operating-point normalization is absent")

    def predict(self, image):
        import torch

        with torch.inference_mode():
            scores = self.model(preprocess(image)).detach().cpu().numpy()
        if scores.shape != (1, len(self.labels)) or not np.isfinite(scores).all():
            raise ValueError("Invalid model output shape or nonfinite scores")
        selected = {"Cardiomegaly", "Effusion", "Lung Opacity"}
        return [
            {"name": label, "score": float(scores[0, i]), "calibrated_probability": None}
            for i, label in enumerate(self.labels)
            if label in selected
        ]
