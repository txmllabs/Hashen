"""Optional ed25519 signature verification for scripts."""

from __future__ import annotations

# SCRIPT_SIGNATURE_INVALID reason code
SCRIPT_SIGNATURE_INVALID = "SCRIPT_SIGNATURE_INVALID"


def verify_script_signature(
    script_content: bytes,
    signature_b64: str | None,
    public_key_b64: str | None,
) -> tuple[bool, str | None]:
    """
    If signature and public_key provided, verify ed25519 signature; else (True, None).
    Returns (ok, reason). On failure: (False, SCRIPT_SIGNATURE_INVALID).
    Requires cryptography package for ed25519.
    """
    if not signature_b64 or not public_key_b64:
        return True, None
    try:
        import base64

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        key_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        pub = Ed25519PublicKey.from_public_bytes(key_bytes)
        pub.verify(sig_bytes, script_content)
        return True, None
    except ImportError:
        return False, SCRIPT_SIGNATURE_INVALID
    except Exception:
        return False, SCRIPT_SIGNATURE_INVALID
