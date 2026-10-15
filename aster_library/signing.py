"""Ed25519 signatures for pack/release manifests.

The private key never enters the repository. It is read from
``ASTER_SIGNING_KEY`` (PEM path) or ``~/.aster-release/aster-signing-ed25519.pem``
and created there on first use on the release machine. The public key is
committed at ``configs/release/signing-public-key.pem`` and compiled into the
application, so a downloaded manifest is authenticated by a key the user
already trusts, not by a checksum served beside it.
"""
import base64
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_KEY_PATH = ROOT / "configs" / "release" / "signing-public-key.pem"


class SignatureError(RuntimeError):
    pass


def private_key_path():
    return Path(os.environ.get("ASTER_SIGNING_KEY") or Path.home() / ".aster-release" / "aster-signing-ed25519.pem")


def load_or_create_private_key(path=None):
    path = Path(path or private_key_path())
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    PUBLIC_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_KEY_PATH.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                              serialization.PublicFormat.SubjectPublicKeyInfo))
    return key


def sign_file(path, key_path=None):
    """Write ``<path>.sig`` (base64 Ed25519 signature over the exact bytes)."""
    key = load_or_create_private_key(key_path)
    path = Path(path)
    signature = key.sign(path.read_bytes())
    Path(str(path) + ".sig").write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="ascii")


def load_public_key(pem=None):
    data = pem if pem is not None else PUBLIC_KEY_PATH.read_bytes()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise SignatureError("Unexpected public key type")
    return key


def verify_bytes(data, signature_b64, public_key=None):
    key = public_key or load_public_key()
    try:
        key.verify(base64.b64decode(signature_b64.strip(), validate=True), data)
    except (InvalidSignature, ValueError) as exc:
        raise SignatureError("Signature verification failed") from exc


def verify_file(path, public_key=None):
    path = Path(path)
    sig = Path(str(path) + ".sig")
    if not sig.exists():
        raise SignatureError(f"Missing signature for {path.name}")
    verify_bytes(path.read_bytes(), sig.read_text(encoding="ascii"), public_key)
    return True
