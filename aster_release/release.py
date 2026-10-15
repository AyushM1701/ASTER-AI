"""Fail-closed offline package integrity, rights and compatibility checks."""
import fnmatch
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


class ReleaseError(ValueError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contained(root, name):
    """Reject Windows aliases, ADS, UNC, traversal and symlink escape."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ReleaseError("Unsafe package path")
    parts = name.split("/")
    reserved = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
    if (PurePosixPath(name).is_absolute()
            or any(p in {"", ".", ".."} or p.endswith((".", " ")) or reserved.match(p)
                   or any(ord(c) < 32 or c in '<>"|?*' for c in p) for p in parts)):
        raise ReleaseError("Unsafe package path")
    root = Path(root).resolve()
    target = root.joinpath(*parts)
    if not target.resolve().is_relative_to(root) or any(p.is_symlink() for p in [target, *target.parents] if p != root):
        raise ReleaseError("Package path escapes install root")
    return target


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"Missing or invalid manifest: {Path(path).name}") from exc


def needs_encoder(profile):
    settings = profile.get("settings", {})
    return (settings.get("retrieval_backend") == "hybrid"
            or settings.get("enable_teaching") and settings.get("teaching_backend", "lexical") == "hybrid")


def check_rights(profile):
    if profile.get("edition") not in {"PublicStandard", "PrivateAuthorized", "ValidationOnly"}:
        raise ReleaseError("Unknown edition")
    if profile["edition"] == "ValidationOnly":
        return
    components = profile.get("components", [])
    if not components:
        raise ReleaseError("No rights-reviewed components")
    for item in components:
        if (item.get("redistribution_allowed") is not True or item.get("decision") != "approved"
                or not all(item.get(k) for k in ("permission_basis", "reviewer", "review_date", "attribution"))):
            raise ReleaseError(f"Unresolved redistribution rights: {item.get('asset_id', 'unknown')}")


def generate_manifest(root, profile):
    root = Path(root).resolve()
    check_rights(profile)
    files = []
    seen = set()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReleaseError("Symlinks are not allowed in packages")
        if not path.is_file() or path.name == "release-manifest.json" and path.parent == root:
            continue
        name = path.relative_to(root).as_posix()
        contained(root, name)
        if name.casefold() in seen:
            raise ReleaseError("Case-colliding package paths")
        seen.add(name.casefold())
        files.append({"path": name, "size": path.stat().st_size, "sha256": sha256(path)})
    manifest = dict(profile, files=files, schema_version=1, product="Aster Medical Research", os="windows-x64")
    (root / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_package(root, expected_manifest_hash=None, *, compatibility=True):
    root = Path(root).resolve()
    manifest_path = root / "release-manifest.json"
    if expected_manifest_hash and sha256(manifest_path) != expected_manifest_hash:
        raise ReleaseError("Release manifest trust check failed")
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1 or manifest.get("os") != "windows-x64":
        raise ReleaseError("Unsupported release manifest")
    check_rights(manifest)
    expected, seen = {"release-manifest.json"}, set()
    for item in manifest["files"]:
        if manifest["edition"] != "ValidationOnly" and not any(
                fnmatch.fnmatchcase(item["path"], component.get("path_glob", ""))
                for component in manifest["components"]):
            raise ReleaseError("File has no reviewed redistribution rights: " + item["path"])
        path = contained(root, item["path"])
        if item["path"].casefold() in seen:
            raise ReleaseError("Duplicate package paths")
        seen.add(item["path"].casefold())
        expected.add(item["path"])
        if (not path.is_file() or path.stat().st_size != item["size"]
                or sha256(path) != item["sha256"]):
            raise ReleaseError(f"Package file missing or changed: {item['path']}. Repair installation.")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != expected:
        raise ReleaseError("Unlisted files in installation. Restore a clean package.")
    if compatibility:
        verify_compatibility(root, manifest)
    return {"status": "verified", "files": len(seen), "bytes": sum(x["size"] for x in manifest["files"]),
            "manifest_sha256": sha256(manifest_path), "edition": manifest["edition"], "manifest": manifest}


def verify_compatibility(root, profile):
    settings = profile.get("settings", {})
    if profile.get("edition", "ValidationOnly") != "ValidationOnly":
        required = ["Aster.exe", "runtime/ollama/ollama.exe", profile.get("entrypoints", {}).get("api", "bin/aster-api.exe"),
                    profile.get("entrypoints", {}).get("web", "bin/aster-web.exe")]
        if not all(contained(root, name).is_file() for name in required) or not profile.get("model"):
            raise ReleaseError("Distributable edition is missing frozen components or its model")
    def file(key):
        return contained(root, settings[key])
    def index_check(records, index, collection):
        digest = hashlib.sha256()
        count = 0
        with records.open(encoding="utf-8") as stream:
            for line in stream:
                digest.update(json.loads(line)["chunk_id"].encode())
                count += 1
        im = read_json(index / "manifest.json")
        if im.get("collection", collection) != collection:
            raise ReleaseError("Index collection differs from runtime settings")
        if im["snapshot_hash"] != digest.hexdigest():
            raise ReleaseError("Index/reference snapshot mismatch")
        mm = read_json(file("embedding_path") / "aster-model-manifest.json")
        if im["embedding_revision"] != mm["revision"] or im["dimension"] != 384:
            raise ReleaseError("Embedding/index revision mismatch")
        if sha256(index / "vectors.npy") != im["vectors_sha256"]:
            raise ReleaseError("Vector index changed")
        return count
    if settings.get("retrieval_backend") == "hybrid":
        count = index_check(file("corpus_path"), file("chroma_path"), settings.get("reference_collection", "medical_reference_v1"))
        if count != profile["data"]["primary"]["records"]:
            raise ReleaseError("Primary record count differs from release")
    if settings.get("enable_teaching"):
        teaching = file("teaching_release_path")
        tm = read_json(teaching / "manifest.json")
        for name, digest in tm["files"].items():
            if sha256(contained(teaching, name)) != digest:
                raise ReleaseError("Teaching release files changed")
        if settings.get("teaching_backend", "lexical") == "hybrid":
            count = index_check(teaching / "records.jsonl", file("teaching_index_path"), "medical_teaching_v1")
        else:
            with (teaching / "records.jsonl").open(encoding="utf-8") as stream:
                count = sum(1 for line in stream if line.strip())
        if count != tm["records"]:
            raise ReleaseError("Teaching record count mismatch")
        if sha256(file("teaching_explanations_path")) != settings["teaching_explanations_sha256"]:
            raise ReleaseError("Teaching explanation hash mismatch")
    if settings.get("enable_secondary_references"):
        secondary = file("secondary_reference_path")
        if sha256(secondary / "manifest.json") != settings["secondary_manifest_sha256"]:
            raise ReleaseError("Secondary release mismatch")
        sm = read_json(secondary / "manifest.json")
        if sha256(secondary / "records.jsonl") != sm["records_sha256"]:
            raise ReleaseError("Secondary records hash mismatch")
        with (secondary / "records.jsonl").open(encoding="utf-8") as stream:
            count = sum(1 for line in stream if line.strip())
        expected = profile.get("data", {}).get("secondary", {}).get("records", sm["records"])
        if count != sm["records"] or count != expected:
            raise ReleaseError("Secondary record count mismatch")
    model = profile.get("model")
    if model:
        store = contained(root, model["store"])
        mm = store / "manifests/registry.ollama.ai/library/qwen3-vl/2b-instruct"
        if sha256(mm) != model["digest"]:
            raise ReleaseError("Packaged Qwen manifest digest differs")
        parsed = read_json(mm)
        for layer in [parsed["config"], *parsed["layers"]]:
            digest = layer["digest"].removeprefix("sha256:")
            if sha256(store / "blobs" / ("sha256-" + digest)) != digest:
                raise ReleaseError("Ollama store blob mismatch")
