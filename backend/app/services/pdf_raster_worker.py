"""Isolated, bounded PDF -> PNG rasteriser for scanned prescriptions/reports.

Reads PDF bytes on stdin, renders at most ``max_pages`` pages (each capped in
pixels), stacks them vertically and writes one PNG to stdout. Runs in its own
process under a memory-limited Job Object; no network or disk writes. Encrypted
PDFs, forms/JavaScript are not executed (PDFium renders page content only).

``library <n,n,...>`` mode renders the listed 1-based pages of a My Library
book separately for OCR: each is written as a 4-byte page number, a 4-byte
length and a grayscale PNG (big-endian), in the order requested.
"""
import io
import sys

MAX_BYTES = 20_971_520
MAX_SIDE = 2200
MAX_TOTAL_PIXELS = 18_000_000
# OCR reads book pages best near 300 dpi; one page is rendered at a time.
LIBRARY_DPI = 300
LIBRARY_MAX_SIDE = 3600
LIBRARY_MAX_PAGES = 16


def library_pages(data, numbers):
    import struct

    import pypdfium2 as pdfium

    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError:
        sys.stderr.write("unreadable_or_encrypted")
        return 3
    for number in numbers:
        if not 1 <= number <= len(pdf):
            continue
        try:
            page = pdf[number - 1]
            width, height = page.get_size()
            scale = min(LIBRARY_DPI / 72, LIBRARY_MAX_SIDE / max(width, height, 1))
            image = page.render(scale=scale, grayscale=True).to_pil().convert("L")
            page.close()
        except pdfium.PdfiumError:
            continue  # one damaged page is reported as unreadable; the rest of the batch is still rendered
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        sys.stdout.buffer.write(struct.pack(">II", number, buffer.tell()) + buffer.getvalue())
        sys.stdout.buffer.flush()
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    library = bool(argv) and argv[0] == "library"
    if library:
        numbers = [int(n) for n in argv[1].split(",")][:LIBRARY_MAX_PAGES] if len(argv) > 1 else []
    else:
        max_pages = max(1, min(int(argv[0]) if argv else 3, 5))
    if not getattr(sys, "frozen", False):
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from backend.app.services.pdf_worker import (
        LIBRARY_MAX_BYTES,
        LIBRARY_MEMORY_BYTES,
        bound_memory,
    )

    if library:
        bound_memory(LIBRARY_MEMORY_BYTES)
    else:
        bound_memory()
    max_bytes = LIBRARY_MAX_BYTES if library else MAX_BYTES
    data = sys.stdin.buffer.read(max_bytes + 1)
    if len(data) > max_bytes or not data.startswith(b"%PDF"):
        sys.stderr.write("invalid_input")
        return 2
    if library:
        return library_pages(data, numbers)
    import pypdfium2 as pdfium
    from PIL import Image

    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError:
        sys.stderr.write("unreadable_or_encrypted")
        return 3
    if len(pdf) < 1:
        sys.stderr.write("no_pages")
        return 3
    pages = []
    total = 0
    for index in range(min(len(pdf), max_pages)):
        page = pdf[index]
        width, height = page.get_size()
        scale = min(200 / 72, MAX_SIDE / max(width, height, 1))
        image = page.render(scale=scale, grayscale=True).to_pil().convert("L")
        total += image.width * image.height
        if total > MAX_TOTAL_PIXELS:
            break
        pages.append(image)
    width = max(p.width for p in pages)
    sheet = Image.new("L", (width, sum(p.height for p in pages) + 16 * (len(pages) - 1)), 255)
    offset = 0
    for page in pages:
        sheet.paste(page, (0, offset))
        offset += page.height + 16
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG")
    sys.stdout.buffer.write(buffer.getvalue())
    return 0


if __name__ == "__main__":
    sys.exit(main())
