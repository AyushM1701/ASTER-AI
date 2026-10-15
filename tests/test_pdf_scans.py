"""Scanned PDF prescriptions share the image attachment workflow via an isolated rasteriser."""
import io
from pathlib import Path

from PIL import Image

from backend.app.api.documents import rasterise_pdf
from backend.app.services import workers

ROOT = Path(__file__).resolve().parents[1]


def sample_pdf(pages=1):
    image = Image.open(ROOT / "data/samples/synthetic_prescription.png").convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PDF", save_all=pages > 1, append_images=[image] * (pages - 1))
    return buffer.getvalue()


def test_pdf_scan_rasterises_to_png():
    png = rasterise_pdf(sample_pdf())
    rendered = Image.open(io.BytesIO(png))
    assert rendered.format == "PNG" and min(rendered.size) > 500


def test_multi_page_scan_is_bounded():
    png = rasterise_pdf(sample_pdf(pages=6), max_pages=2)
    one = Image.open(io.BytesIO(rasterise_pdf(sample_pdf(), max_pages=1)))
    two = Image.open(io.BytesIO(png))
    assert two.height < one.height * 2.2


def test_damaged_pdf_is_rejected_without_crash():
    import pytest

    from backend.app.errors import AppError

    with pytest.raises(AppError):
        rasterise_pdf(b"%PDF-1.7\n" + b"garbage" * 1000)


def test_worker_command_shapes():
    assert workers.command("pdf_raster", 3)[-1] == "3"
