"""Export local source and readable knowledge; never embed private stores or credentials."""

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "Architecture and Source.md"
INVENTORY = ROOT / "architecture-source-inventory.jsonl"
REPORT = ROOT / "architecture-source-report.json"
OUTPUTS = {ARCHIVE, INVENTORY, REPORT}
TEXT_EXTENSIONS = {
    ".py", ".js", ".cjs", ".mjs", ".css", ".html", ".md", ".txt", ".json",
    ".jsonl", ".yaml", ".yml", ".toml", ".ps1", ".csv", ".tsv", ".xml",
    ".svg", ".ini", ".cfg", ".spec", ".bat", ".sh", ".sql", ".sha256",
    ".lock", ".env", ".gitignore", ".rst", ".in", ".nsi", ".iss",
}
SECRET_PATTERNS = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}|\bgh[pousr]_[A-Za-z0-9]{30,}|"
    rb"\bAKIA[A-Z0-9]{16}\b"
)


def classify(relative):
    parts = relative.parts
    low = [part.lower() for part in parts]
    name = low[-1]
    if (name.startswith(".env") and name != ".env.example") or name in {
        "secrets.toml", "credentials.json", "credentials.yaml", "id_rsa", "id_ed25519",
    } or name.endswith((".key", ".pfx", ".p12")):
        return "private", "credential-bearing file; content and hash omitted"
    if len(parts) > 1 and low[0] == "data" and low[1] in {"private", "workspaces"}:
        return "private", "private configuration or saved user workspace"
    if low[0] in {"runtime", "tmp"} or low[:2] == ["artifacts", "runtime"]:
        return "runtime", "temporary runtime content may contain user/session data"
    if low[0] in {".venv", ".impeccable", ".git", "node_modules"}:
        return "dependency", "installed dependencies or tool environment"
    if any(part in {"__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"} for part in low):
        return "cache", "generated cache or installed dependencies"
    if low[:2] == ["artifacts", "release"] or low[:3] == ["data", "models", "ollama-runtime"]:
        return "distribution", "generated distribution or external runtime assets"
    if "raw" in low or "acquired" in low or name.endswith(".download"):
        return "raw_acquisition", "raw acquisition; extracted/normalized data and rights records embedded separately"
    if relative.suffix.lower() in TEXT_EXTENSIONS or name in {"license", "notice", ".gitignore", ".env.example"}:
        return "text", "complete readable file"
    return "binary", "binary or non-source asset; original remains at its listed path"


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def paths():
    for base, dirs, files in os.walk(ROOT, followlinks=False):
        dirs.sort(key=str.casefold)
        for name in sorted(files, key=str.casefold):
            path = Path(base) / name
            if path not in OUTPUTS:
                yield path


def text_payload(raw):
    if b"\x00" in raw[:8192] and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise UnicodeError("binary NUL bytes")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        value = raw.decode("utf-16")
        return value, value.encode("utf-8"), "utf-16 (converted to UTF-8)"
    value = raw.decode("utf-8")
    return value, raw, "utf-8 (original bytes preserved)"


def create():
    if shutil.disk_usage(ROOT).free < 8 * 1024**3:
        raise RuntimeError("Archive requires at least 8 GiB free disk space")
    started = datetime.now(timezone.utc).isoformat()
    counts = collections.Counter()
    sizes = collections.Counter()
    errors = []
    changed = []
    embedded_lines = 0
    embedded_bytes = 0
    source_files = 0
    architecture = (ROOT / "docs/ARCHITECTURE.md").read_bytes()
    with ARCHIVE.open("wb") as output, INVENTORY.open("w", encoding="utf-8", newline="\n") as inventory:
        output.write(b"# Architecture and Source\n\n")
        output.write(f"Generated UTC: {started}\n\n".encode())
        output.write(architecture)
        output.write(b"\n\n# Complete embedded file contents\n\n")
        for index, path in enumerate(paths(), 1):
            relative = path.relative_to(ROOT)
            entry = {"path": relative.as_posix()}
            category, reason = classify(relative)
            entry.update(category=category, reason=reason)
            try:
                before = path.stat()
                entry["bytes"] = before.st_size
                if path.is_symlink():
                    entry.update(category="symlink", reason="symlink; target not traversed")
                elif category == "text":
                    raw = path.read_bytes()
                    if SECRET_PATTERNS.search(raw):
                        entry.update(category="private", reason="credential signature detected; content and hash omitted")
                    else:
                        entry["sha256"] = hashlib.sha256(raw).hexdigest()
                        try:
                            value, payload, encoding = text_payload(raw)
                        except UnicodeError:
                            entry.update(category="binary", reason="file is not supported Unicode text")
                        else:
                            entry["encoding"] = encoding
                            entry["lines"] = len(value.splitlines())
                            fence = b"`" * max(3, 1 + max((len(match) for match in re.findall(rb"`+", payload)), default=0))
                            header = (
                                f"\n\n## File: {relative.as_posix()}\n\n"
                                f"Original bytes: {len(raw)}; lines: {entry['lines']}; "
                                f"SHA-256: `{entry['sha256']}`; encoding: {encoding}.\n\n"
                            )
                            output.write(header.encode("utf-8"))
                            output.write(fence + b"\n")
                            entry["payload_offset"] = output.tell()
                            entry["payload_bytes"] = len(payload)
                            entry["payload_sha256"] = hashlib.sha256(payload).hexdigest()
                            output.write(payload)
                            output.write(b"\n" + fence + b"\n")
                            entry["embedded"] = True
                            embedded_bytes += len(payload)
                            embedded_lines += entry["lines"]
                            if relative.parts[0] in {"backend", "frontend", "aster_release", "scripts", "tests", "packaging", "configs", ".github"}:
                                source_files += 1
                elif category in {"binary", "raw_acquisition"}:
                    entry["sha256"] = sha_file(path)
                after = path.stat()
                if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                    entry["changed_during_export"] = True
                    changed.append(entry["path"])
            except OSError as error:
                entry.update(category="read_error", reason=type(error).__name__)
                errors.append(entry["path"])
            entry.setdefault("embedded", False)
            counts[entry["category"]] += 1
            sizes[entry["category"]] += entry.get("bytes", 0)
            inventory.write(json.dumps(entry, ensure_ascii=True) + "\n")
            if index % 10000 == 0:
                print(f"Inventoried {index} files; embedded {embedded_bytes / 1024**2:.1f} MiB", flush=True)
        output.write(b"\n\n# Complete workspace inventory\n\n")
        output.write(b"Every discovered file follows. Omitted content has an explicit category and reason. Private, dependency, cache, distribution and runtime hashes are intentionally omitted. Generated archive/inventory/report files are excluded from their own input.\n\n")
        inventory.flush()
        with INVENTORY.open("rb") as source:
            output.write(b"```jsonl\n")
            shutil.copyfileobj(source, output, 4 * 1024 * 1024)
            output.write(b"```\n")
        summary = {
            "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
            "workspace": str(ROOT), "archive": str(ARCHIVE), "inventory": str(INVENTORY),
            "files": sum(counts.values()), "categories": dict(counts), "category_bytes": dict(sizes),
            "embedded_files": counts["text"], "embedded_source_config_test_files": source_files,
            "embedded_lines": embedded_lines, "embedded_payload_bytes": embedded_bytes,
            "read_errors": errors, "changed_during_export": changed,
            "self_excluded": [path.name for path in sorted(OUTPUTS)],
        }
        output.write(b"\n# Export summary\n\n```json\n")
        output.write(json.dumps(summary, indent=2).encode())
        output.write(b"\n```\n")
    summary["archive_bytes"] = ARCHIVE.stat().st_size
    summary["archive_sha256"] = sha_file(ARCHIVE)
    summary["inventory_sha256"] = sha_file(INVENTORY)
    REPORT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


def verify():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    verified = 0
    mismatches = []
    with ARCHIVE.open("rb") as archive, INVENTORY.open(encoding="utf-8") as inventory:
        for line in inventory:
            entry = json.loads(line)
            if not entry["embedded"]:
                continue
            archive.seek(entry["payload_offset"])
            remaining = entry["payload_bytes"]
            digest = hashlib.sha256()
            while remaining:
                chunk = archive.read(min(4 * 1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                digest.update(chunk)
            if remaining or digest.hexdigest() != entry["payload_sha256"]:
                mismatches.append(entry["path"])
            verified += 1
    checks = {
        "verified_embedded_files": verified, "payload_mismatches": mismatches,
        "archive_hash_matches": sha_file(ARCHIVE) == report["archive_sha256"],
        "inventory_hash_matches": sha_file(INVENTORY) == report["inventory_sha256"],
        "embedded_count_matches": verified == report["embedded_files"],
    }
    report["verification"] = checks
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2), flush=True)
    if mismatches or not all(checks[key] for key in ("archive_hash_matches", "inventory_hash_matches", "embedded_count_matches")):
        raise RuntimeError("Archive verification failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.verify_only:
        create()
    verify()
