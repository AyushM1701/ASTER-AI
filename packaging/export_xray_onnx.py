"""Build-time export of the pinned TorchXRayVision checkpoints to ONNX.

The runtime then needs only onnxruntime + scikit-image (no torch). The export
writes ``data/models/xray/onnx/{densenet,autoencoder,view}.onnx`` plus
``export-manifest.json`` recording the source checkpoint hashes, op thresholds,
label order and the maximum absolute difference measured against torch.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import torchvision
import torchxrayvision as xrv

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ROOT / "data/models/xray"
OUT = WEIGHTS / "onnx"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class DenseLogits(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, x):
        return self.model.classifier(self.model.features2(x))


class AutoencoderError(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, x):
        reconstruction = self.model.decode(self.model.encode(x, check_resolution=False), x.size())
        return torch.mean((reconstruction - x) ** 2, dim=(1, 2, 3)) / (1024.0 ** 2)


class ViewLogits(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, x):
        x = (x.repeat(1, 3, 1, 1) + 1024) / 2048
        return self.model((x - self.mean) / self.std)[:, :2]


def main():
    config = json.loads((ROOT / "configs/xray_gates.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    dense = xrv.models.DenseNet(weights="densenet121-res224-all", cache_dir=str(WEIGHTS)).eval()
    ae = xrv.autoencoders.ResNetAE101()
    ae.load_state_dict(torch.load(WEIGHTS / config["weights"]["autoencoder"]["file"], map_location="cpu", weights_only=True))
    ae.eval()
    view = torchvision.models.resnet.resnet50()
    view.load_state_dict(torch.load(WEIGHTS / config["weights"]["view"]["file"], map_location="cpu", weights_only=True))
    view.eval()
    sample = torch.from_numpy(np.random.default_rng(0).uniform(-1024, 1024, (1, 1, 224, 224)).astype(np.float32))
    modules = {"densenet": DenseLogits(dense), "autoencoder": AutoencoderError(ae), "view": ViewLogits(view)}
    manifest = {"source": {k: config["weights"][k] for k in ("classifier", "autoencoder", "view")},
                "labels": list(dense.pathologies), "op_threshs": [None if np.isnan(v) else float(v) for v in dense.op_threshs.numpy()],
                "preprocessing": "xrv normalize(maxval=255) -> centre crop -> skimage resize 224 (mode=constant, preserve_range)",
                "files": {}}
    import onnxruntime as ort

    for name, module in modules.items():
        module.eval()
        path = OUT / f"{name}.onnx"
        with torch.no_grad():
            expected = module(sample).numpy()
        torch.onnx.export(module, (sample,), path, input_names=["image"], output_names=["output"],
                          dynamic_axes={"image": {0: "batch"}, "output": {0: "batch"}}, opset_version=17, dynamo=False)
        actual = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"]).run(None, {"image": sample.numpy()})[0]
        manifest["files"][name] = {"file": f"onnx/{name}.onnx", "sha256": sha256(path), "bytes": path.stat().st_size,
                                   "max_abs_diff_vs_torch_random_input": float(np.max(np.abs(expected - actual)))}
        print(name, manifest["files"][name])
    (OUT / "export-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
