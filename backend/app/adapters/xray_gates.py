"""Input gates for user-uploaded chest X-rays (before any finding score is shown).

Gates, in order:
  1. technical quality (size, aspect, dynamic range, saturation, colour)
  2. out-of-distribution check: TorchXRayVision ResNet autoencoder (101-elastic)
     reconstruction error relative to calibrated chest-X-ray range
  3. view: xinario chestViewSplit ResNet-50 (Frontal vs Lateral)
  4. adult: required user attestation (no age model is shipped by default)

Thresholds live in configs/xray_gates.json with their calibration provenance.
Weights are loaded only from verified local files; nothing is downloaded here.
"""
import hashlib
import json
from pathlib import Path

import numpy as np


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def xrv_tensor(image, size=224):
    """XRV preprocessing: 8-bit -> [-1024, 1024], centre crop, resize."""
    import torch
    import torchxrayvision as xrv

    pixels = np.asarray(image.convert("L"), dtype=np.float32)
    pixels = xrv.datasets.normalize(pixels, 255)[None, ...]
    pixels = xrv.datasets.XRayCenterCrop()(pixels)
    pixels = xrv.datasets.XRayResizer(size)(pixels)
    return torch.from_numpy(np.asarray(pixels, dtype=np.float32))[None, ...]


def colourfulness(image):
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    rg = np.abs(rgb[..., 0] - rgb[..., 1])
    yb = np.abs(0.5 * (rgb[..., 0] + rgb[..., 1]) - rgb[..., 2])
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


class XrayGates:
    def __init__(self, config_path, weights_dir):
        import torch
        import torchvision
        import torchxrayvision as xrv

        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        weights_dir = Path(weights_dir)
        files = self.config["weights"]
        for key in ("autoencoder", "view"):
            path = weights_dir / files[key]["file"]
            if not path.is_file() or _sha256(path) != files[key]["sha256"]:
                raise ValueError(f"{key} weights missing or hash mismatch")
        self.ae = xrv.autoencoders.ResNetAE101()
        self.ae.load_state_dict(torch.load(weights_dir / files["autoencoder"]["file"], map_location="cpu", weights_only=True))
        self.ae.eval()
        self.view = torchvision.models.resnet.resnet50()
        self.view.load_state_dict(torch.load(weights_dir / files["view"]["file"], map_location="cpu", weights_only=True))
        self.view.eval()
        self.norm = torchvision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        self.thresholds = self.config["thresholds"]

    def measure(self, image):
        import torch

        tensor = xrv_tensor(image)
        with torch.inference_mode():
            reconstruction = self.ae(tensor)["out"]
            ae_error = float(torch.mean((reconstruction - tensor) ** 2) / (1024.0 ** 2))
            x = (tensor.repeat(1, 3, 1, 1) + 1024) / 2048
            logits = self.view(self.norm(x))[:, :2]
            probs = torch.softmax(logits, dim=1)[0].tolist()
        return {"ae_error": ae_error, "frontal_probability": probs[0], "lateral_probability": probs[1],
                "colourfulness": colourfulness(image)}

    def assess(self, image, quality, adult_attested):
        return self.decide(self.thresholds, self.config, image, quality, self.measure(image), adult_attested)

    @staticmethod
    def decide(t, config, image, quality, measures, adult_attested):
        reasons = []
        if min(image.size) < t["min_side"]:
            reasons.append(("quality", f"Image is too small ({image.width}×{image.height}); at least {t['min_side']} pixels per side is needed."))
        if not t["aspect_min"] <= quality["aspect_ratio"] <= t["aspect_max"]:
            reasons.append(("quality", "The image proportions do not match a chest radiograph. Upload the whole film without borders or screenshots."))
        if quality["dynamic_range"] < t["min_dynamic_range"] or quality["saturation_fraction"] > t["max_saturation"]:
            reasons.append(("quality", "Contrast is too low or too much of the image is pure black/white to assess."))
        if measures["colourfulness"] > t["max_colourfulness"]:
            reasons.append(("modality", "This looks like a colour photograph rather than a radiograph. Upload the original grayscale X-ray image."))
        if measures["ae_error"] > t["max_ae_error"]:
            reasons.append(("out_of_distribution", "This image does not resemble the chest X-rays the model was built for "
                                                   "(it may be another body part, a dental film, CT/MRI, or a photo)."))
        if measures["frontal_probability"] < t["min_frontal_probability"]:
            reasons.append(("view", "This appears to be a lateral (side) chest view. Only frontal PA/AP chest views are supported."))
        if not adult_attested:
            reasons.append(("age", "Confirm the X-ray is of an adult (18 years or older). Children's X-rays are not supported."))
        return {"accepted": not reasons, "reasons": [{"gate": g, "message": m} for g, m in reasons],
                "measurements": {k: round(v, 5) for k, v in measures.items()},
                "thresholds": t, "calibration": config.get("calibration", {})}
