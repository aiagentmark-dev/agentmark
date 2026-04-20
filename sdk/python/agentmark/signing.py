"""agentmark.signing — Ed25519 manifest signing"""

import base64
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentmark.manifest import Manifest


def sign_manifest(private_key_bytes: bytes, manifest: "Manifest") -> str:
    """
    Sign a manifest with an Ed25519 private key.
    Returns base64-encoded signature string.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import load_der_private_key
    except ImportError:
        raise ImportError("pip install cryptography")

    private_key = load_der_private_key(private_key_bytes, password=None)
    canonical = manifest.canonical_json()
    signature = private_key.sign(canonical)
    return base64.b64encode(signature).decode()


def verify_signature(
    public_key_bytes: bytes,
    manifest: "Manifest",
    signature: str,
) -> tuple[bool, str]:
    """
    Verify a manifest signature.
    Returns (valid, reason).
    """
    try:
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        raise ImportError("pip install cryptography")

    pub = load_der_public_key(public_key_bytes)
    canonical = manifest.canonical_json()
    try:
        pub.verify(base64.b64decode(signature), canonical)
        return True, "ok"
    except InvalidSignature:
        return False, "invalid_signature"
