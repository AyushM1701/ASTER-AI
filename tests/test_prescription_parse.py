"""Prescription line parsing: copy what is written, never infer."""
import pytest

from backend.app.services.prescription_parse import normalized, parse_line, parse_prescription


@pytest.mark.parametrize("line, expected", [
    ("Tab. Amoxicillin 500 mg 1-0-1 x 5 days after food",
     {"formulation": "Tab", "medicine_name": "Amoxicillin", "strength": "500 mg", "frequency": "1-0-1", "duration": "x 5 days", "instructions": "after food"}),
    ("Cap Omeprazole 20mg OD before breakfast for 14 days",
     {"formulation": "Cap", "medicine_name": "Omeprazole", "strength": "20mg", "frequency": "OD", "duration": "for 14 days", "instructions": "before breakfast"}),
    ("Syp. Paracetamol 250mg/5ml 5 ml TDS x 3 days",
     {"formulation": "Syp", "medicine_name": "Paracetamol", "strength": "250mg/5ml", "dose": "5 ml", "frequency": "TDS", "duration": "x 3 days"}),
    ("Inj. Ceftriaxone 1 g IV BD", {"formulation": "Inj", "medicine_name": "Ceftriaxone", "strength": "1 g", "route": "IV", "frequency": "BD"}),
    ("Chlorhexidine 0.2% mouthwash 10 ml twice daily for 1 week",
     {"medicine_name": "Chlorhexidine", "strength": "0.2%", "formulation": "mouthwash", "frequency": "twice daily", "duration": "for 1 week"}),
])
def test_common_lines(line, expected):
    parsed = parse_line(line)
    for key, value in expected.items():
        assert parsed.get(key) == value, (key, parsed)


def test_missing_parts_are_not_invented():
    parsed = parse_line("Tab. Metformin 500 mg")
    assert "frequency" not in parsed and "duration" not in parsed and "dose" not in parsed


def test_unreadable_and_non_medicine_lines():
    assert parse_line("[unreadable]") is None
    assert parse_line("Dr. A. Sharma, MBBS") is None
    assert "medicine_name" not in (parse_line("Tab. [unreadable] 500 mg BD") or {})


def test_labelled_sheet_and_grouping():
    groups = parse_prescription("Medicine: Example\nStrength: 5 mg\nRoute: oral\nMedicine: [unreadable]\nStrength: 10 mg")
    assert groups[0]["medicine_name"][0] == "Example" and groups[1]["medicine_name"][0] is None


def test_normalisation_hints_are_separate():
    assert normalized("frequency", "BD") == "twice daily"
    assert normalized("frequency", "1-0-1").startswith("morning 1")
    assert normalized("formulation", "Tab") == "tablet" and normalized("strength", "5 mg") is None


def test_ocr_rotation_and_quality_feedback():
    import shutil

    import pytest
    from PIL import Image, ImageFilter

    from backend.app.adapters.ocr import OCRAdapter, image_quality
    from backend.app.config import Settings

    adapter = OCRAdapter(Settings(_env_file=None))
    if not adapter.ready() and not shutil.which("tesseract"):
        pytest.skip("Tesseract not installed")
    image = Image.open("data/samples/synthetic_prescription.png").convert("RGB")
    for angle in (90, 180, 270):
        result = adapter.extract_printed(image.rotate(angle, expand=True))
        assert result["rotation_applied"] == angle and "Metformin" in result["raw_text"]
        assert result["lines"] and all("bbox" in line for line in result["lines"])
    assert image_quality(image)["warnings"] == []
    assert any("blurred" in w for w in image_quality(image.filter(ImageFilter.GaussianBlur(4)))["warnings"])


def test_ocr_works_with_release_style_tessdata(tmp_path, monkeypatch):
    """The packaged tessdata holds only *.traineddata (no configs/ folder), as in the release."""
    import shutil
    from pathlib import Path

    import pytest
    from PIL import Image

    from backend.app.adapters.ocr import OCRAdapter
    from backend.app.config import Settings

    adapter = OCRAdapter(Settings(_env_file=None))
    source = Path("C:/Program Files/Tesseract-OCR/tessdata")
    if not adapter.ready() or not (source / "eng.traineddata").is_file():
        pytest.skip("Tesseract not installed")
    for name in ("eng.traineddata", "osd.traineddata"):
        shutil.copy2(source / name, tmp_path / name)
    monkeypatch.setenv("TESSDATA_PREFIX", str(tmp_path))
    result = adapter.extract_printed(Image.open("data/samples/synthetic_prescription.png").convert("RGB"))
    assert "Metformin" in result["raw_text"] and result["lines"]
