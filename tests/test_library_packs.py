"""Library pack integrity, activation, rollback, update isolation and retrieval."""
import json
import zipfile
from pathlib import Path

import pytest

from aster_library import index as index_module
from aster_library import install, signing
from aster_library.model import chunk_paragraphs, edition_for, normalize_license

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data/models/minilm/onnx/model.onnx").exists(), reason="MiniLM ONNX not installed")


@pytest.fixture
def keys(tmp_path, monkeypatch):
    monkeypatch.setenv("ASTER_SIGNING_KEY", str(tmp_path / "key.pem"))
    monkeypatch.setenv("ASTER_EMBED_CACHE", str(tmp_path / "cache.sqlite"))
    monkeypatch.setattr(signing, "PUBLIC_KEY_PATH", tmp_path / "public.pem")
    signing.load_or_create_private_key()
    return signing.load_public_key()


def make_pack(root, pack_id, texts, keys):
    pack = root / pack_id
    pack.mkdir(parents=True)
    units = [{"unit_id": f"{pack_id}-{i}", "doc_id": f"doc{i}", "title": "Periodontitis review", "section": "Overview",
              "text": text, "text_sha256": str(i), "content_class": "professional", "evidence_type": "review",
              "license": "CC-BY-4.0", "url": "https://example.org", "acquired": "2026-10-14", "jurisdiction": "International",
              "publication_status": "published"} for i, text in enumerate(texts)]
    (pack / "units.jsonl").write_text("".join(json.dumps(u) + "\n" for u in units), encoding="utf-8")
    (pack / "documents.jsonl").write_text("", encoding="utf-8")
    manifest = {"schema_version": 2, "pack_id": pack_id, "version": "t", "edition": "core", "created": "2026-10-14T00:00:00Z",
                "counts": {"documents": 0, "units": len(units), "by_content_class": {"professional": len(units)}},
                "freshness": {"professional": {"review_after_days": 730, "warn_after_days": 1825}}, "files": {}}
    for name in ("units.jsonl", "documents.jsonl"):
        manifest["files"][name] = {"sha256": install.sha256_file(pack / name), "bytes": (pack / name).stat().st_size}
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    signing.sign_file(pack / "manifest.json")
    index_module.build_index(pack, log=lambda *_: None)
    return pack


TEXTS = ["Periodontitis is a chronic inflammatory disease of the tooth-supporting tissues driven by dysbiotic plaque biofilm.",
         "Scaling and root planing removes subgingival calculus and reduces probing pocket depth.",
         "Guided tissue regeneration uses a barrier membrane to exclude epithelium from the healing defect."]


def test_install_activate_search_and_rollback(tmp_path, keys):
    built = tmp_path / "built"
    a = make_pack(built, "pack-a", TEXTS, keys)
    b = make_pack(built, "pack-b", TEXTS[:2], keys)
    library = tmp_path / "library"
    install.install_pack_dir(a, library, keys)
    install.install_pack_dir(b, library, keys)
    install.activate(library, ["pack-a"], keys)
    install.activate(library, ["pack-b"], keys)
    assert json.loads((library / "last-known-good.json").read_text())["packs"] == ["pack-a"]
    assert install.rollback(library, keys) == ["pack-a"]
    assert json.loads((library / "active.json").read_text())["packs"] == ["pack-a"]

    from backend.app.services.library import LibraryStore

    store = LibraryStore(library)
    assert store.status == "ready"
    hits = store.search("How does a membrane help periodontal regeneration?", audience="study", k=2)
    assert hits and "barrier membrane" in hits[0].text
    assert store.freshness()["professional"]["state"] in {"current", "review_due", "outdated_warning"}
    store.close()


def test_tampered_pack_is_rejected_and_last_known_good_used(tmp_path, keys):
    built = tmp_path / "built"
    a = make_pack(built, "pack-a", TEXTS, keys)
    b = make_pack(built, "pack-b", TEXTS[:2], keys)
    library = tmp_path / "library"
    for pack in (a, b):
        install.install_pack_dir(pack, library, keys)
    install.activate(library, ["pack-a"], keys)
    install.activate(library, ["pack-b"], keys)
    # Corrupt the active pack's index after activation (disk damage / tampering).
    target = library / "packs" / "pack-b" / "index" / "dense.f16.npy"
    target.write_bytes(target.read_bytes()[:-8])
    with pytest.raises(install.InstallError):
        install.quality_check(library / "packs" / "pack-b", keys)
    from backend.app.services.library import LibraryStore

    store = LibraryStore(library)
    assert store.status == "ready" and store.used_fallback and store.packs[0].pack_id == "pack-a"
    store.close()


def test_failed_update_leaves_active_selection(tmp_path, keys):
    built = tmp_path / "built"
    a = make_pack(built, "pack-a", TEXTS, keys)
    library = tmp_path / "library"
    install.install_pack_dir(a, library, keys)
    install.activate(library, ["pack-a"], keys)

    def bad_fetch(url, dest, sha256, size):
        Path(dest).write_bytes(b"not the pack")

    manifest = {"schema_version": 1, "packs": [{"pack_id": "pack-new", "edition": "core", "url": "https://x/p.zip",
                                                 "sha256": "0" * 64, "bytes": 12}]}
    with pytest.raises(install.InstallError):
        install.apply_update(library, manifest, bad_fetch, keys)
    assert json.loads((library / "active.json").read_text())["packs"] == ["pack-a"]


def test_update_manifest_signature_is_required(tmp_path, keys):
    raw = json.dumps({"schema_version": 1, "packs": [{"pack_id": "x"}]}).encode()
    with pytest.raises(install.InstallError):
        install.verify_update_manifest(raw, "AAAA", keys)
    key = signing.load_or_create_private_key()
    import base64

    good = base64.b64encode(key.sign(raw)).decode()
    assert install.verify_update_manifest(raw, good, keys)["packs"][0]["pack_id"] == "x"
    with pytest.raises(install.InstallError):
        install.verify_update_manifest(raw + b" ", good, keys)


@pytest.mark.parametrize("name", ["../evil.txt", "a/../../evil.txt", "C:/evil.txt"])
def test_safe_extract_rejects_traversal(tmp_path, name):
    archive = tmp_path / "x.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(name, "x")
    with pytest.raises(install.InstallError):
        install.safe_extract(archive, tmp_path / "out")


def test_licence_editions_and_chunking():
    assert normalize_license("http://creativecommons.org/licenses/by/4.0/") == "CC-BY-4.0"
    assert normalize_license("https://creativecommons.org/licenses/by-nc-sa/3.0/igo/") == "CC-BY-NC-SA-3.0-IGO"
    assert normalize_license("cc by-nc-nd") == "CC-BY-NC-ND-4.0"
    assert edition_for("CC-BY-4.0") == "default" and edition_for("CC-BY-NC-SA-4.0") == "noncommercial"
    assert edition_for("CC-BY-NC-ND-4.0") is None and edition_for(None) is None
    chunks = chunk_paragraphs(["a" * 600, "b" * 600, "c" * 50], target=1000)
    assert len(chunks) == 2 and chunks[0][0] == 0


def test_in_app_update_endpoint_activates_signed_pack(tmp_path, keys):
    import base64
    import functools
    import http.server
    import threading

    from fastapi.testclient import TestClient

    from backend.app.config import Settings
    from backend.app.main import create_app

    built = tmp_path / "built"
    a = make_pack(built, "pack-a", TEXTS, keys)
    b = make_pack(built, "pack-b", TEXTS[:2], keys)
    library = tmp_path / "library"
    install.install_pack_dir(a, library, keys)
    install.activate(library, ["pack-a"], keys)
    served = tmp_path / "served"
    served.mkdir()
    archive = served / "pack-b.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for path in b.rglob("*"):
            if path.is_file():
                handle.write(path, (Path("pack-b") / path.relative_to(b)).as_posix())
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(served))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    manifest = {"schema_version": 1, "channel": "test", "packs": [{"pack_id": "pack-b", "edition": "core", "bytes": archive.stat().st_size,
                                                                     "sha256": install.sha256_file(archive), "url": base + "/pack-b.zip"}]}
    raw = json.dumps(manifest).encode()
    (served / "library-latest.json").write_bytes(raw)
    key = signing.load_or_create_private_key()
    (served / "library-latest.json.sig").write_text(base64.b64encode(key.sign(raw)).decode())
    settings = Settings(_env_file=None, answer_engine="grounded", library_root=library, enable_teaching=False,
                        library_update_url=base + "/library-latest.json", corpus_path=tmp_path / "none.jsonl")
    try:
        with TestClient(create_app(settings)) as client:
            assert client.post("/v1/library/update", json={"network_consent": False}).status_code == 422
            result = client.post("/v1/library/update", json={"network_consent": True, "include_noncommercial": False})
            assert result.status_code == 200, result.text
            assert [p["pack_id"] for p in result.json()["library"]["packs"]] == ["pack-b"]
            assert json.loads((library / "last-known-good.json").read_text())["packs"] == ["pack-a"]
            (served / "library-latest.json").write_bytes(raw + b" ")  # tampered manifest
            assert client.post("/v1/library/update", json={"network_consent": True}).status_code == 502
    finally:
        server.shutdown()


def test_openfda_salt_forms_match_but_combinations_do_not():
    from aster_library.providers.openfda_labels import same_ingredient

    assert same_ingredient("METFORMIN HYDROCHLORIDE", "metformin")
    assert same_ingredient("METFORMIN HCL", "metformin")
    assert same_ingredient("LEVOTHYROXINE SODIUM ANHYDROUS", "levothyroxine")
    assert same_ingredient("Amoxicillin", "amoxicillin")
    assert not same_ingredient("SITAGLIPTIN AND METFORMIN HYDROCHLORIDE", "metformin")
    assert not same_ingredient("AMLODIPINE AND ATORVASTATIN", "atorvastatin")
    assert not same_ingredient("METFORMIN ER 500 MG", "metformin")
