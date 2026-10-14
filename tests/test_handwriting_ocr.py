import json
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image

from backend.app.adapters.ocr import OCRAdapter
from backend.app.adapters.ollama import OllamaAdapter
from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.services.documents import parse_fields


def printed_result():
    return {
        "raw_text": "Medicine: Printedname\nStrength: 50 mg",
        "words": [],
        "engine": "tesseract",
        "score_semantics": "not confidence",
    }


class Vision:
    def __init__(self, style="handwritten", uncertain=None):
        self.style, self.uncertain = style, uncertain or []

    def transcribe(self, image):
        return SimpleNamespace(
            style=self.style,
            raw_text="Medicine: Testname\nStrength: 5 mg\nDuration: [unreadable]",
            uncertain_line_numbers=self.uncertain,
        )


def test_handwritten_transcription_uses_vision_and_has_no_invented_boxes(monkeypatch):
    adapter = OCRAdapter(Settings(enable_handwriting_ocr=True), vision=Vision())
    monkeypatch.setattr(adapter, "extract_printed", lambda image: printed_result())
    result = adapter.extract(Image.new("RGB", (512, 512), "white"))
    assert result["engine"] == "local_vision"
    assert "Testname" in result["raw_text"]
    assert result["words"] == []
    assert result["comparison_text"] == printed_result()["raw_text"]
    assert result["warnings"]


def test_uncertain_medicine_line_is_not_a_candidate(monkeypatch):
    adapter = OCRAdapter(Settings(enable_handwriting_ocr=True), vision=Vision(uncertain=[0]))
    monkeypatch.setattr(adapter, "extract_printed", lambda image: printed_result())
    result = adapter.extract(Image.new("RGB", (512, 512), "white"))
    fields = {f["kind"]: f for f in parse_fields(result["raw_text"], provenance=result["engine"])}
    assert fields["medicine_name"]["candidate_value"] is None
    assert fields["duration"]["candidate_value"] is None
    assert fields["strength"]["candidate_value"] == "5 mg"
    assert fields["strength"]["provenance"] == "local_vision"


def test_uncertain_style_cannot_create_medication_candidates(monkeypatch):
    adapter = OCRAdapter(Settings(enable_handwriting_ocr=True), vision=Vision(style="uncertain"))
    monkeypatch.setattr(adapter, "extract_printed", lambda image: printed_result())
    result = adapter.extract(Image.new("RGB", (512, 512), "white"))
    assert all(f["candidate_value"] is None for f in parse_fields(result["raw_text"]))


def test_printed_reader_still_preserves_explicit_uncertainty(monkeypatch):
    adapter = OCRAdapter(
        Settings(enable_handwriting_ocr=True), vision=Vision(style="printed", uncertain=[1])
    )
    monkeypatch.setattr(adapter, "extract_printed", lambda image: printed_result())
    result = adapter.extract(Image.new("RGB", (512, 512), "white"))
    fields = {f["kind"]: f for f in parse_fields(result["raw_text"])}
    assert fields["strength"]["candidate_value"] is None


def test_printed_marker_is_preserved_without_uncertainty_annotation(monkeypatch):
    vision = Vision(style="printed")
    monkeypatch.setattr(
        vision,
        "transcribe",
        lambda image: SimpleNamespace(
            style="printed",
            raw_text="Medicine: Testname\nStrength: [unreadable]",
            uncertain_line_numbers=[],
        ),
    )
    adapter = OCRAdapter(Settings(enable_handwriting_ocr=True), vision=vision)
    monkeypatch.setattr(adapter, "extract_printed", lambda image: printed_result())
    result = adapter.extract(Image.new("RGB", (512, 512), "white"))
    fields = {f["kind"]: f for f in parse_fields(result["raw_text"])}
    assert fields["strength"]["candidate_value"] is None


@pytest.mark.parametrize(
    "question",
    [
        "Tell me if my X-ray is normal.",
        "Determine whether my scan is abnormal.",
        "Can you check if this X-ray is normal?",
    ],
)
def test_personal_image_normality_requires_professional_review(question):
    from backend.app.services.policy import check_policy

    assert check_policy(question)["status"] == "unsupported_input"


def test_general_radiology_education_is_not_blocked():
    from backend.app.services.policy import check_policy

    assert check_policy("Explain what normality means in a radiology report in general.") is None


def test_unknown_uncertainty_line_abstains(monkeypatch):
    adapter = OCRAdapter(Settings(enable_handwriting_ocr=True), vision=Vision(uncertain=[99]))
    monkeypatch.setattr(adapter, "extract_printed", lambda image: printed_result())
    result = adapter.extract(Image.new("RGB", (512, 512), "white"))
    assert result["raw_text"] == printed_result()["raw_text"]
    assert any(
        "unavailable" in w.casefold() or "validation" in w.casefold() for w in result["warnings"]
    )


def test_vision_outage_falls_back_visibly(monkeypatch):
    vision = Vision()
    monkeypatch.setattr(
        vision, "transcribe", lambda image: (_ for _ in ()).throw(AppError(503, "error", "missing"))
    )
    adapter = OCRAdapter(Settings(enable_handwriting_ocr=True), vision=vision)
    monkeypatch.setattr(adapter, "extract_printed", lambda image: printed_result())
    result = adapter.extract(Image.new("RGB", (512, 512), "white"))
    assert result["engine"] == "tesseract"
    assert result["warnings"]


@pytest.mark.parametrize(
    "raw", ["Medicine: [unreadable]", "Medicine: unreadable", "Strength: [unreadable] mg"]
)
def test_parser_never_treats_unreadable_marker_as_medicine_or_strength(raw):
    fields = parse_fields(raw)
    assert all(f["candidate_value"] is None for f in fields)


def test_local_vision_request_uses_pixels_and_strict_transcription_prompt():
    settings = Settings()
    adapter = OllamaAdapter(settings)
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "style": "handwritten",
                            "raw_text": "Testname 5 mg",
                            "uncertain_line_numbers": [],
                        }
                    )
                }
            },
        )

    adapter.client.close()
    adapter.client = httpx.Client(
        base_url=settings.ollama_base_url, transport=httpx.MockTransport(respond)
    )
    result = adapter.transcribe(Image.new("RGB", (512, 512), "white"))
    assert result.style == "handwritten"
    assert requests[0]["messages"][1]["images"]
    assert "Do not guess" in requests[0]["messages"][0]["content"]
    assert requests[0]["options"]["temperature"] == 0
    adapter.close()
