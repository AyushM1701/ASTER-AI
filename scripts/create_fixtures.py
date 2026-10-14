import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LINES = [
    "SYNTHETIC DOCUMENT - NOT A PRESCRIPTION",
    "",
    "For testing transcription and confirmation only.",
    "No patient. No prescriber. No medical approval.",
    "",
    "Medicine: Metformin hydrochloride",
    "Strength: 500 mg",
    "Formulation: immediate-release tablet",
    "Route: oral",
    "Frequency: sample instruction only",
    "Instructions: Verify with the original document.",
    "",
    "Duration intentionally omitted. Leave unreadable.",
]


def sample_bytes():
    image = Image.new("RGB", (1400, 1050), "#fafafa")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = (
        ImageFont.truetype(str(font_path), 36)
        if font_path.is_file()
        else ImageFont.load_default(size=36)
    )
    for i, line in enumerate(LINES):
        draw.text((70, 70 + i * 65), line, font=font, fill="#20252b")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main():
    folder = ROOT / "data/samples"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "synthetic_prescription.png").write_bytes(sample_bytes())
    (folder / "synthetic_ground_truth.json").write_text(
        json.dumps(
            {
                "raw_text": "\n".join(line for line in LINES if line),
                "fields": {
                    "medicine_name": "Metformin hydrochloride",
                    "strength": "500 mg",
                    "formulation": "immediate-release tablet",
                    "route": "oral",
                    "frequency": "sample instruction only",
                    "duration": None,
                    "instructions": "Verify with the original document.",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Created clearly labelled synthetic OCR fixture.")


if __name__ == "__main__":
    main()
