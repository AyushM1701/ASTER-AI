import shutil
from pathlib import Path

import pytesseract
from PIL import ImageOps

from backend.app.errors import AppError
from backend.app.native import native_subprocess


class OCRAdapter:
    def __init__(self, settings, vision=None):
        self.settings = settings
        self.vision = vision
        packaged = settings.app_env == "packaged"
        self.executable = settings.tesseract_cmd or (None if packaged else shutil.which("tesseract"))
        windows_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
        if not packaged and not self.executable and windows_path.is_file():
            self.executable = str(windows_path)
        if self.executable:
            pytesseract.pytesseract.tesseract_cmd = self.executable

    def ready(self):
        return bool(self.executable and Path(self.executable).is_file())

    def extract(self, image):
        printed = self.extract_printed(image)
        if not self.settings.enable_handwriting_ocr or self.vision is None:
            return printed
        try:
            result = self.vision.transcribe(image)
            lines = result.raw_text.splitlines()
            if any(n >= len(lines) for n in result.uncertain_line_numbers):
                raise ValueError("Uncertainty annotation is outside the transcription")
            uncertain_lines = (
                list(range(len(lines)))
                if result.style == "uncertain"
                else result.uncertain_line_numbers
            )
            uncertain_lines = sorted(
                set(uncertain_lines)
                | {
                    index
                    for index, line in enumerate(lines)
                    if "[unreadable]" in line.casefold() or line.strip().casefold() == "unreadable"
                }
            )
            if result.style == "printed" and not uncertain_lines:
                printed["style"] = "printed"
                if (
                    " ".join(result.raw_text.split()).casefold()
                    != " ".join(printed["raw_text"].split()).casefold()
                ):
                    printed["warnings"] = [
                        "The two local readers disagree. Compare every field with the original; "
                        "do not infer a medicine name or dose from either reader."
                    ]
                return printed
            for index in uncertain_lines:
                # Preserve an explicit label while preventing ambiguous tokens
                # from becoming medication candidates.
                prefix = lines[index].split(":", 1)[0] + ": " if ":" in lines[index] else ""
                lines[index] = prefix + "[unreadable]"
            warnings = [
                "Experimental local handwriting transcription. It can misread or invent text. "
                "Verify names, doses, decimals, units and instructions with the original. "
                "Ask the prescriber or pharmacist to clarify anything illegible."
            ]
            if uncertain_lines or result.style == "uncertain":
                warnings.append(
                    "Uncertain text was left unreadable; do not guess or use it for treatment."
                )
            return {
                "raw_text": "\n".join(lines),
                "words": [],
                "engine": "local_vision",
                "style": result.style,
                "model": self.settings.vision_model,
                "comparison_text": printed["raw_text"],
                "uncertain_line_numbers": uncertain_lines,
                "warnings": warnings,
                "score_semantics": "No calibrated handwriting confidence or invented word boxes.",
            }
        except (AppError, ValueError, TypeError, AttributeError):
            printed["warnings"] = [
                "Handwriting reader unavailable or failed validation. This is printed-text OCR only. "
                "Do not rely on it for handwriting; obtain a clearer copy or professional clarification."
            ]
            return printed

    def extract_printed(self, image):
        if not self.ready():
            raise AppError(
                503,
                "error",
                "Tesseract is missing. Install English data and configure TESSERACT_CMD.",
            )
        try:
            with native_subprocess():
                result = pytesseract.image_to_data(
                    ImageOps.grayscale(image),
                    lang="eng",
                    config="--psm 6",
                    output_type=pytesseract.Output.DICT,
                    timeout=self.settings.ocr_timeout_seconds,
                )
            lines, boxes = {}, []
            for i, text in enumerate(result["text"]):
                if not text.strip():
                    continue
                group = (result["block_num"][i], result["par_num"][i], result["line_num"][i])
                lines.setdefault(group, []).append(text)
                boxes.append(
                    {
                        "text": text,
                        "bbox": [
                            result["left"][i],
                            result["top"][i],
                            result["width"][i],
                            result["height"][i],
                        ],
                        "engine_score": float(result["conf"][i]),
                        "engine": "tesseract",
                    }
                )
            return {
                "raw_text": "\n".join(" ".join(v) for v in lines.values())[:12000],
                "words": boxes[:1000],
                "engine": "tesseract",
                "score_semantics": "Engine signal, not probability the medicine is correct.",
            }
        except (RuntimeError, pytesseract.TesseractError, OSError) as exc:
            raise AppError(
                503, "error", "Local OCR failed or timed out. Try a clearer printed image."
            ) from exc
