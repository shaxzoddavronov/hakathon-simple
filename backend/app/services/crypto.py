from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app import config

_KEY_BY_VERSION: dict[int, bytes] = {}

_PLACEHOLDER = "REPLACE_WITH_BASE64_32_BYTE_KEY"


def _load_keys() -> None:
    if 1 in _KEY_BY_VERSION:
        return
    raw = config.settings.QM_MASTER_KEY
    if not raw or raw == _PLACEHOLDER:
        raise RuntimeError("QM_MASTER_KEY env var is not set")
    # The documented format (.env.example) is url-safe base64, often with the
    # '=' padding stripped. urlsafe_b64decode also accepts standard base64
    # (it only remaps '-_', leaving '+/' intact), so either generator works.
    s = raw.strip()
    s += "=" * (-len(s) % 4)
    try:
        key = base64.urlsafe_b64decode(s)
    except (ValueError, base64.binascii.Error) as e:
        raise RuntimeError(f"QM_MASTER_KEY must be valid base64: {e}") from e
    if len(key) != 32:
        raise RuntimeError(
            f"QM_MASTER_KEY must decode to 32 bytes (got {len(key)})"
        )
    _KEY_BY_VERSION[1] = key


def encrypt(
    plaintext: bytes | str, *, aad: bytes | None = None
) -> tuple[bytes, bytes, int]:
    _load_keys()
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    nonce = os.urandom(12)
    ct = AESGCM(_KEY_BY_VERSION[1]).encrypt(nonce, plaintext, aad)
    return ct, nonce, 1


def decrypt(
    ciphertext: bytes,
    nonce: bytes,
    *,
    key_version: int = 1,
    aad: bytes | None = None,
) -> bytes:
    _load_keys()
    if key_version not in _KEY_BY_VERSION:
        raise RuntimeError(f"Unknown key_version {key_version}")
    return AESGCM(_KEY_BY_VERSION[key_version]).decrypt(nonce, ciphertext, aad)


def generate_master_key() -> str:
    # Url-safe to match the documented format in .env.example.
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
