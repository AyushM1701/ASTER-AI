"""Check that a signing private key matches the committed public key and the signed release lock."""

import argparse
import base64
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aster_library.signing import (  # noqa: E402
    PUBLIC_KEY_PATH,
    load_public_key,
    verify_bytes,
    verify_file,
)

PUBLIC_FORMAT = (serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key", type=Path, help="PEM file holding the Ed25519 private key")
    args = parser.parse_args()

    # Load directly: aster_library.signing.load_or_create_private_key would create a key if the file were missing.
    key = serialization.load_pem_private_key(args.key.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        sys.exit("FAIL: the key is not an Ed25519 private key")
    public = load_public_key()
    if key.public_key().public_bytes(*PUBLIC_FORMAT) != public.public_bytes(*PUBLIC_FORMAT):
        sys.exit(f"FAIL: the key does not match {PUBLIC_KEY_PATH.relative_to(ROOT).as_posix()}")
    print(f"OK: the key matches {PUBLIC_KEY_PATH.relative_to(ROOT).as_posix()}")

    message = b"aster signing key check"
    verify_bytes(message, base64.b64encode(key.sign(message)).decode("ascii"), public)
    print("OK: a test signature verifies with the public key")

    verify_file(ROOT / "release" / "release-lock.json", public)
    print("OK: release/release-lock.json.sig verifies with the public key")


if __name__ == "__main__":
    main()
