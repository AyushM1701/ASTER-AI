# Third-party materials in Aster

Aster's own code is MIT licensed by its owner. This does not license third-party material. A public release is blocked until every shipped component has a reviewed entry in `packaging/asset-rights.csv` and its exact license/attribution text is included. This document records the development inventory, not completed redistribution approval.

| Component | Origin / license indication | Release decision |
|---|---|---|
| Python / Tcl/Tk / PyInstaller bootloader | PSF / Tcl-Tk licenses / PyInstaller exception | Exact frozen notices pending |
| FastAPI, uvicorn, httpx, Pydantic, NumPy and retrieval dependencies | Individual installed wheel metadata | Exact dependency and native library review pending |
| Ollama v0.35.1 standalone runtime | Ollama repository MIT; accompanying native libraries have separate terms | Exact archive notice review pending |
| Qwen3-VL 2B Instruct | Qwen model card Apache-2.0; exact packaged quantized lineage also needs review | Pending |
| all-MiniLM-L6-v2 | Model card Apache-2.0; revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Pending exact notice copy |
| Tesseract 5.5.3 Windows build, English traineddata and DLLs | Tesseract Apache-2.0; Windows DLLs have individual licenses | Pending DLL audit |
| DM Sans / Manrope | OFL notices in `frontend/web/fonts` | Preserve both notices; package review pending |
| Lucide icons | ISC notice in `frontend/web/icons` | Preserve notice; package review pending |
| Medical references and medicine catalogues | Each immutable release's `sources.yaml`; retailer and dataset provenance varies | Public redistribution not yet approved |
| Teaching articles and chapters | Mixture of CC BY, CC BY-SA, CC BY-NC, CC BY-NC-SA and public-domain claims | Per-source conditions and attribution review pending |
| X-ray checkpoints and images | Research acquisition permissions do not establish redistribution | Excluded from default packaged profile |

Local validation packages are non-distributable engineering artifacts. Source tests, dataset uploader license declarations, user acquisition attestations and freely accessible webpages are not substitutes for redistribution permission or clinical validation.
