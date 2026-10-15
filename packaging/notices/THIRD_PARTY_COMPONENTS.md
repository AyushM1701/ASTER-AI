# Third-party components shipped with Aster v2 releases

Aster's own source code is MIT-licensed (see `LICENSE`). The components below keep their own licences;
licence texts are in `notices/licenses/` and, for frozen Python packages, `notices/python-packages/`.
No component author endorses Aster. Nothing here is clinical validation.

| Component | Version / revision | Licence | Source | How Aster obtains it |
|---|---|---|---|---|
| Ollama runtime (CPU libraries; CUDA libraries for the GPU profile) | v0.35.1 | MIT; bundled native libraries keep the licences in `runtime/ollama/lib/ollama/*LICENSE*` (llama.cpp MIT, CUTLASS/cuDNN/NVTX NVIDIA terms, etc.) | https://github.com/ollama/ollama/releases/tag/v0.35.1 | Release asset repackaged without modification |
| Qwen3-VL-2B-Instruct (Q4_K_M GGUF via Ollama) | Ollama `qwen3-vl:2b-instruct`, manifest pinned in `release-lock.json` | Apache-2.0 | https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct | Release asset (fallback: registry.ollama.ai), SHA-256 pinned |
| Qwen3-4B (Q4_K_M GGUF via Ollama) — quality-cpu / enhanced-gpu profiles | Ollama `qwen3:4b-q4_K_M` | Apache-2.0 | https://huggingface.co/Qwen/Qwen3-4B | As above |
| all-MiniLM-L6-v2 (ONNX) | 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 | Apache-2.0 | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 | Published ONNX file, unmodified |
| nli-deberta-v3-xsmall cross-encoder (int8 ONNX) | a150876415327c80daeff35ca6f68f5ed8cf5c24 | Apache-2.0 (DeBERTa-v3 base: MIT) | https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall | Published ONNX file, unmodified |
| MedCPT Cross-Encoder (int8 ONNX) | 71caf65d4927987813984f54c284405a13fcca49 | Public domain (US Government work, NCBI/NLM) | https://huggingface.co/ncbi/MedCPT-Cross-Encoder | Exported to ONNX and int8-quantised by Aster's build (see model manifest) |
| TorchXRayVision DenseNet-121 `densenet121-res224-all`, ResNet autoencoder `101-elastic` | torchxrayvision 1.4.0 release v1 assets | Apache-2.0 | https://github.com/mlmed/torchxrayvision | Exported to ONNX by Aster's build; source checkpoints SHA-256 pinned in `configs/xray_gates.json` |
| chestViewSplit ResNet-50 view classifier | torchxrayvision release v1 asset | Apache-2.0 | https://github.com/xinario/chestViewSplit | Exported to ONNX by Aster's build |
| Tesseract OCR + English and OSD traineddata | 5.5.3 (UB Mannheim Windows build) | Apache-2.0; Leptonica BSD-2-Clause; image libraries (libpng, zlib, libjpeg-turbo, libtiff, libwebp, OpenJPEG, giflib, ICU, others) under their permissive licences | https://github.com/tesseract-ocr/tesseract, https://github.com/UB-Mannheim/tesseract | Repackaged DLLs and traineddata, unmodified |
| Python runtime, Tcl/Tk | CPython 3.13 | PSF License Agreement; Tcl/Tk BSD-style | https://www.python.org | Frozen by PyInstaller |
| PyInstaller bootloader | 6.22.3 | GPL-2.0 with the bootloader exception (permits distributing frozen applications) | https://pyinstaller.org | Build tool |
| Python packages (FastAPI, Starlette, Uvicorn, Pydantic, HTTPX, NumPy, SciPy, scikit-image, Pillow, ONNX Runtime, tokenizers, cryptography, pypdf, pypdfium2/PDFium, pytesseract, PyYAML, defusedxml, psutil, Beautiful Soup and their dependencies) | pinned in `packaging/requirements-runtime-v2.in` | MIT / BSD / Apache-2.0 / HPND / PSF — per package | PyPI | Licence files copied to `notices/python-packages/` at build time |
| DM Sans, Manrope fonts | — | SIL Open Font License 1.1 | Google Fonts | `frontend/web/fonts/*` with licence files |
| Lucide icons | — | ISC (Feather-derived portions MIT) | https://lucide.dev | `frontend/web/icons/Lucide-LICENSE.txt` |
| NIH ChestX-ray14 image 00000001_000.png (startup self-test and demo) | — | CC0 (Kaggle distribution); NIH requests attribution: Wang X. et al., "ChestX-ray8", CVPR 2017 | https://nihcc.app.box.com/v/ChestXray-NIHCC | `data/samples/nih-demo-00000001_000.png` |
| Medical reference library packs | see each pack's `NOTICE.md` and `documents.jsonl` | Per document (CC0, CC BY, CC BY-SA, US public domain; NC pack: CC BY-NC / CC BY-NC-SA) | MedlinePlus, openFDA, Europe PMC/PMC OA, OpenStax, existing Aster MBBS/MDS sources | Built by Aster's library pipeline; separate archives |
