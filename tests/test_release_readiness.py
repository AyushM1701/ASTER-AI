import base64
import copy
import io

import pytest

from aster_release.launcher import readiness_message, validate_inference, validate_loaded_data
from aster_release.release import ReleaseError


def profile():
    return {"settings": {"enable_teaching": True, "enable_secondary_references": True}, "data": {
        "primary": {"records": 2, "release": "primary-v1"},
        "teaching": {"records": 3, "release": "teaching-v1"},
        "secondary": {"records": 4, "release": "secondary-v1"}}}


def health():
    return {"references": {"records": 2, "library_version": "primary-v1"},
            "teaching": {"records": 3, "version": "teaching-v1"},
            "secondary_references": {"records": 4, "library_version": "secondary-v1", "available": True}}


@pytest.mark.parametrize("key", ["references", "teaching", "secondary_references"])
def test_manifest_metadata_cannot_cover_unloaded_libraries(key):
    actual = health()
    actual[key]["records"] = 0
    with pytest.raises(ReleaseError, match="failed to load exactly"):
        validate_loaded_data(actual, profile())


def test_secondary_unavailable_blocks_packaged_readiness():
    actual = health()
    actual["secondary_references"]["available"] = False
    with pytest.raises(ReleaseError, match="secondary library is unavailable"):
        validate_loaded_data(actual, profile())
    validate_loaded_data(health(), profile())


@pytest.mark.parametrize("change", [{"model": "other"}, {"done": False}, {"message": {"content": ""}}])
def test_model_catalog_presence_does_not_prove_inference(change):
    response = {"model": "pinned", "done": True, "message": {"content": "OK"}}
    invalid = copy.deepcopy(response)
    invalid.update(change)
    with pytest.raises(ReleaseError, match="readiness inference"):
        validate_inference(invalid, "pinned")
    validate_inference(response, "pinned")


def test_vision_startup_probe_is_small_valid_and_synthetic():
    from PIL import Image

    message = readiness_message(True)
    raw = base64.b64decode(message["images"][0], validate=True)
    assert len(raw) < 1024
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        assert image.format == "PNG"
        assert image.mode == "RGB"
        assert image.size == (64, 64)
        assert image.getextrema() == ((112, 112), (144, 144), (144, 144))
    assert "images" not in readiness_message(False)
