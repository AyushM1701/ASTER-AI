import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.adapters.ocr import OCRAdapter  # noqa: E402
from backend.app.adapters.ollama import OllamaAdapter  # noqa: E402
from backend.app.config import Settings  # noqa: E402
from backend.app.services.compute import ComputeGate  # noqa: E402
from backend.app.services.retrieval import ReferenceStore  # noqa: E402
from backend.app.services.xray import XrayService  # noqa: E402


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.release_manifest:
        from aster_release.release import verify_package
        result = verify_package(args.release_manifest.parent)
        print(json.dumps({k: v for k, v in result.items() if k != "manifest"}, indent=2))
        return
    if args.offline:
        parser.error("--offline requires --release-manifest; source verification probes local services")
    settings = Settings()
    references = ReferenceStore(settings)
    ollama = OllamaAdapter(settings)
    report = {
        "references": references.manifest(),
        "corpus_error": references.error,
        "ocr_available": OCRAdapter(settings, vision=ollama).ready(),
        "handwriting_enabled": settings.enable_handwriting_ocr,
        "ollama": ollama.ready(),
        "attachment_classifier": ollama.ready(settings.vision_model),
        "general_chat": settings.enable_general_chat,
        "xray": XrayService(settings, ComputeGate(settings), references).health(),
        "answer_mode": settings.answer_mode,
    }
    ollama.close()
    print(json.dumps(report, indent=2))
    if references.error or settings.answer_mode == "ollama" and not report["ollama"]["available"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
