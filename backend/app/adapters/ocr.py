import io
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
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

    def ready(self):
        return bool(self.executable and Path(self.executable).is_file())

    def extract(self, image):
        printed = self.extract_printed(image)
        if not self.settings.enable_handwriting_ocr or self.vision is None:
            return printed
        shared = {key: printed[key] for key in ("upright_image", "rotation_applied", "quality", "lines") if key in printed}
        try:
            result = self.vision.transcribe(printed.get("upright_image", image))
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
                **shared,
                "raw_text": "\n".join(lines),
                "words": [],
                "engine": "local_vision",
                "style": result.style,
                "model": self.settings.vision_model,
                "comparison_text": printed["raw_text"],
                "uncertain_line_numbers": uncertain_lines,
                "warnings": printed.get("quality", {}).get("warnings", []) + warnings,
                "score_semantics": "No calibrated handwriting confidence or invented word boxes.",
            }
        except (AppError, ValueError, TypeError, AttributeError):
            printed["warnings"] = [
                "Handwriting reader unavailable or failed validation. This is printed-text OCR only. "
                "Do not rely on it for handwriting; obtain a clearer copy or professional clarification."
            ]
            return printed

    def _run(self, image, args):
        """Run Tesseract on stdin/stdout: no temporary image or text files are written."""
        buffer = io.BytesIO()
        ImageOps.grayscale(image).save(buffer, format="PNG")
        environment = dict(os.environ)
        command = [self.executable, "stdin", "stdout", *args]
        try:
            with native_subprocess():
                result = subprocess.run(command, input=buffer.getvalue(), capture_output=True, env=environment,
                                        timeout=self.settings.ocr_timeout_seconds,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("ocr_timeout") from exc
        if result.returncode != 0:
            raise RuntimeError("ocr_failed")
        return result.stdout.decode("utf-8", "replace")

    def _data(self, image):
        columns = {key: [] for key in ("block_num", "par_num", "line_num", "left", "top", "width", "height", "conf", "text")}
        # Inline variables, not the "tsv" config file: the bundled tessdata has no configs/ folder.
        lines = self._run(image, ["--psm", "6", "-l", "eng", "-c", "tessedit_create_tsv=1",
                                  "-c", "tessedit_create_txt=0"]).splitlines()
        header = lines[0].split("\t") if lines else []
        for line in lines[1:]:
            values = dict(zip(header, line.split("\t"), strict=False))
            if values.get("level") != "5":
                continue
            for key in columns:
                raw = values.get(key, "")
                columns[key].append(raw if key == "text" else float(raw) if key == "conf" else int(raw or 0))
        return columns

    @staticmethod
    def _score(result):
        confidences = [float(c) for c, t in zip(result["conf"], result["text"], strict=True) if t.strip() and float(c) >= 0]
        return (sum(confidences) / len(confidences) if confidences else 0.0) * min(1.0, len(confidences) / 8)

    def orient(self, image, search=True):
        """Return (upright image, degrees rotated clockwise). OSD first, then a bounded search."""
        try:
            osd = self._run(image, ["--psm", "0", "-c", "min_characters_to_try=5"])
            rotate = int(re.search(r"Rotate:\s*(\d+)", osd).group(1))
            confidence = float(re.search(r"Orientation confidence:\s*([\d.]+)", osd).group(1))
            if rotate and confidence >= 2.0:
                return image.rotate(-rotate, expand=True), rotate
            if rotate and confidence >= 0.5:
                # Low-confidence suggestion: keep it only if the text reads clearly better.
                small = image.copy()
                small.thumbnail((1400, 1400))
                original = self._score(self._data(small))
                candidate = self._score(self._data(small.rotate(-rotate, expand=True)))
                if candidate > original * 1.2:
                    return image.rotate(-rotate, expand=True), rotate
            return image, 0
        except (RuntimeError, OSError, AttributeError, ValueError):
            if not search:
                return image, 0
        best, best_angle, best_score = image, 0, None
        small = image.copy()
        small.thumbnail((1200, 1200))
        for angle in (0, 90, 180, 270):
            try:
                score = self._score(self._data(small.rotate(-angle, expand=True)))
            except (RuntimeError, OSError):
                continue
            if best_score is None or score > best_score * 1.25:
                best_score, best_angle = score, angle
        if best_angle:
            best = image.rotate(-best_angle, expand=True)
        return best, best_angle

    def extract_printed(self, image):
        if not self.ready():
            raise AppError(
                503,
                "error",
                "The text reader (Tesseract) is missing. Choose Repair in Aster setup.",
            )
        try:
            quality = image_quality(image)
            image, rotation = self.orient(image, search=False)
            result = self._data(image)
            if not rotation and self._score(result) < 45:
                upright, rotation = self.orient(image)
                if rotation:
                    image = upright
                    result = self._data(image)
            lines, boxes = {}, []
            for i, text in enumerate(result["text"]):
                if not text.strip():
                    continue
                group = (result["block_num"][i], result["par_num"][i], result["line_num"][i])
                box = [result["left"][i], result["top"][i], result["width"][i], result["height"][i]]
                confidence = float(result["conf"][i])
                lines.setdefault(group, []).append((text, box, confidence))
                boxes.append({"text": text, "bbox": box, "engine_score": confidence, "engine": "tesseract"})
            line_records = []
            for words in lines.values():
                left = min(b[0] for _, b, _ in words)
                top = min(b[1] for _, b, _ in words)
                right = max(b[0] + b[2] for _, b, _ in words)
                bottom = max(b[1] + b[3] for _, b, _ in words)
                line_records.append({"text": " ".join(t for t, _, _ in words), "bbox": [left, top, right - left, bottom - top],
                                     "min_confidence": min(c for _, _, c in words)})
            return {
                "raw_text": "\n".join(line["text"] for line in line_records)[:12000],
                "words": boxes[:1000],
                "lines": line_records[:300],
                "engine": "tesseract",
                "rotation_applied": rotation,
                "upright_image": image,
                "quality": quality,
                "warnings": quality["warnings"],
                "score_semantics": "Engine signal, not probability the medicine is correct.",
            }
        except (RuntimeError, OSError, ValueError) as exc:
            raise AppError(
                503, "error", "Local OCR failed or timed out. Try a clearer, well-lit photo of the document."
            ) from exc


def image_quality(image):
    """Plain-language photo quality feedback (technical signals, not certification)."""
    gray = np.asarray(ImageOps.grayscale(image), dtype=np.float32)
    small = gray[::max(1, gray.shape[0] // 800), ::max(1, gray.shape[1] // 800)]
    laplacian = (small[1:-1, 1:-1] * 4 - small[:-2, 1:-1] - small[2:, 1:-1] - small[1:-1, :-2] - small[1:-1, 2:])
    sharpness = float(laplacian.var()) if laplacian.size else 0.0
    brightness = float(np.median(gray))
    # Ink-to-paper contrast: documents are mostly blank paper, so use the extremes.
    contrast = float(np.percentile(gray, 99.5) - np.percentile(gray, 0.5))
    warnings = []
    if min(image.size) < 600:
        warnings.append("The image resolution is low. Take the photo closer, filling the frame with the document.")
    if sharpness < 60:
        warnings.append("The photo looks blurred. Hold the camera steady and retake it in good light.")
    if brightness < 70:
        warnings.append("The photo is dark. Retake it in brighter light without shadows.")
    if contrast < 80:
        warnings.append("Text contrast is low. Make sure the whole document is in focus and evenly lit.")
    return {"sharpness": round(sharpness, 1), "brightness": round(brightness, 1), "contrast": round(contrast, 1),
            "width": image.width, "height": image.height, "warnings": warnings,
            "semantics": "Photo quality signals only; they do not confirm the text was read correctly."}
