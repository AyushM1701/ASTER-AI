"""Build-time gate using the frozen API interpreter and included offline encoder."""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from aster_release.release import ReleaseError, contained, needs_encoder, verify_package
from aster_release.runtime import sanitized_environment


def check(package):
    root = Path(package).resolve()
    verified = verify_package(root)
    if not needs_encoder(verified["manifest"]):
        print("Lexical-only profile: no encoder is required or advertised")
        return
    with tempfile.TemporaryDirectory(prefix="aster-encoder-check-") as scratch:
        env = sanitized_environment(root, Path(scratch))
        try:
            result = subprocess.run([str(contained(root, verified["manifest"]["entrypoints"]["api"])), "--check-encoder"],
                           cwd=scratch, env=env, check=True, timeout=300,
                           capture_output=True, text=True, encoding="utf-8",
                           creationflags=subprocess.CREATE_NO_WINDOW)
            print(result.stdout, end="")
        finally:
            native_temp = Path(env["TEMP"]).resolve()
            if not native_temp.is_relative_to(Path(scratch).resolve()) or native_temp.is_symlink():
                raise ReleaseError("Encoder scratch path escapes its temporary directory")
            shutil.rmtree(native_temp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    check(parser.parse_args().package)


if __name__ == "__main__":
    main()
