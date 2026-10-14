import hashlib
import io

import pytest

from aster_release.installer import authenticated_bytes, download
from aster_release.release import ReleaseError


@pytest.mark.parametrize("range_honored", [True, False])
def test_interrupted_download_resumes_or_restarts_cleanly(tmp_path, monkeypatch, range_honored):
    path = tmp_path / "part"
    path.with_name("part.partial").write_bytes(b"abc")
    requests = []
    class Response(io.BytesIO):
        status = 206 if range_honored else 200
        headers = {"Content-Range": "bytes 3-5/6"} if range_honored else {}
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            return Response(b"def" if range_honored else b"abcdef")
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    download("https://github.com/AyushM1701/ASTER-AI/releases/download/v1/part", path,
             hashlib.sha256(b"abcdef").hexdigest(), 6)
    assert requests[0].get_header("Range") == "bytes=3-"
    assert path.read_bytes() == b"abcdef"
    assert not path.with_name("part.partial").exists()


def test_same_origin_checksum_is_not_a_trust_root():
    with pytest.raises(ReleaseError, match="authentication"):
        authenticated_bytes(b'{"schema_version": 1}', {"sha256": "0" * 64})
