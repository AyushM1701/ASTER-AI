import io
import warnings

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.app.errors import AppError


def decoded_budget(data, settings):
    # Inspect only the header before load/convert/preview allocations. Reserve
    # decoded RGB + worst-case PNG preview plus incoming bytes and framing.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                pixels = image.width * image.height
                if pixels > settings.max_image_pixels:
                    raise AppError(413, "unsupported_input", "Image has too many pixels.")
                return len(data) + pixels * 6 + 65536
    except AppError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise AppError(415, "unsupported_input", "Use a valid PNG or JPEG image.") from exc


def decode_image(data, settings, *, xray=False):
    if len(data) > settings.max_upload_bytes:
        raise AppError(413, "unsupported_input", "Image exceeds the upload byte limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {"PNG", "JPEG"} or getattr(original, "n_frames", 1) != 1:
                    raise AppError(415, "unsupported_input", "Use one still PNG or JPEG image.")
                if original.width * original.height > settings.max_image_pixels:
                    raise AppError(413, "unsupported_input", "Image has too many pixels.")
                if min(original.size) < 32:
                    raise AppError(422, "quality_rejected", "Image is too small to read.")
                if xray and original.mode not in {"L", "RGB"}:
                    raise AppError(
                        415, "unsupported_input", "Research adapter accepts only 8-bit images."
                    )
                original.verify()
            with Image.open(io.BytesIO(data)) as source:
                source.load()
                working = source.copy() if xray else ImageOps.exif_transpose(source)
                working = working.convert("RGB")
                # New pixels only: strip metadata from session preview.
                clean = Image.fromarray(np.asarray(working).copy())
                output = io.BytesIO()
                clean.save(output, format="PNG")
                return clean, output.getvalue()
    except AppError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise AppError(
            415, "unsupported_input", "Image could not be decoded. Use a valid PNG or JPEG."
        ) from exc


def quality_measurements(image):
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    dynamic_range = float(np.percentile(gray, 99) - np.percentile(gray, 1))
    saturation = float(((gray <= 1) | (gray >= 254)).mean())
    blur_proxy = float(np.var(np.diff(gray, axis=0)) + np.var(np.diff(gray, axis=1)))
    return {
        "width": image.width,
        "height": image.height,
        "aspect_ratio": image.width / image.height,
        "dynamic_range": dynamic_range,
        "saturation_fraction": saturation,
        "blur_proxy": blur_proxy,
        "semantics": "Technical measurements; not diagnostic-quality certification.",
    }
