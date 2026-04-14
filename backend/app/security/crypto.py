"""Encryption helpers for storing secrets at rest.

We only encrypt per-user API keys stored in Firestore. Values are marked with a
prefix so we can distinguish plaintext legacy values from encrypted ones.

Encryption is enabled when `Settings.SETTINGS_ENCRYPTION_KEY` is set.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


_PREFIX = "enc:"


def _derive_fernet_key(secret: str) -> bytes:
    # Fernet requires a 32-byte urlsafe base64-encoded key.
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Optional[Fernet]:
    secret = (get_settings().SETTINGS_ENCRYPTION_KEY or "").strip()
    if not secret:
        return None
    return Fernet(_derive_fernet_key(secret))


def is_encrypted(value: Optional[str]) -> bool:
    return bool(value) and isinstance(value, str) and value.startswith(_PREFIX)


def encrypt_str(plaintext: Optional[str]) -> str:
    value = (plaintext or "").strip()
    if not value:
        return ""

    f = _get_fernet()
    if f is None:
        # Encryption disabled; store plaintext.
        return value

    token = f.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_str(ciphertext: Optional[str]) -> str:
    if not ciphertext:
        return ""

    if not is_encrypted(ciphertext):
        return ciphertext

    f = _get_fernet()
    if f is None:
        raise RuntimeError("Encrypted settings present but SETTINGS_ENCRYPTION_KEY is not configured")

    token = ciphertext[len(_PREFIX) :]
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError("Failed to decrypt settings value (invalid token)") from e
