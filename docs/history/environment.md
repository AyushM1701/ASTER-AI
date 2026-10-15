# Verified build environment — 6 October 2026

- Windows, Python 3.13.3, project-local virtual environment.
- Intel Core i5-13450HX, 10 cores / 16 logical processors.
- Reported installed RAM: 25,463,480,320 bytes (about 23.7 GiB).
- Free C: space measured during build: 42,755,485,696 bytes (about 39.8 GiB).
- CPU baseline. GPU driver/inference was not benchmarked or assumed.
- Tesseract 5.5.3.20260724 in the standard Windows Program Files installation.
- Initial baseline had no Ollama. The later shared-model setup installed the
  project-local Ollama runtime and Qwen3-VL 2B Instruct; the current local launcher
  runs it on 127.0.0.1:11434. Optional embeddings and X-ray weights remain uncached.
- Measured dependencies in requirements.lock.txt; venv pip updated to 26.2.1.
- Services listen on 127.0.0.1:8000 and 127.0.0.1:8501, one API worker.
- The default UI is the dedicated web frontend with self-hosted fonts and icons;
  no Node runtime or frontend package installation is required to run it.

Machine data is a reproducibility snapshot; free space and process memory change.
Large model/dataset acquisition requires its own size and terms check.
