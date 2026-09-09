from __future__ import annotations

"""
Token encryption for Gmail OAuth credentials.

Uses Fernet symmetric encryption from the `cryptography` library
(already a project dependency).

Key is read from the GOOGLE_TOKEN_ENCRYPTION_KEY environment variable.

Key format: a URL-safe base64-encoded 32-byte key, which you can generate with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

SECURITY RULES:
- Never log tokens.
- Never return tokens to the frontend.
- Never hardcode the key.
- Rotate keys only with planned token re-encryption.
"""

import os
import logging
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_DEV_WARNING_ISSUED = False

# Location of the persisted dev key — inside backend/var/ which is .gitignore'd.
# Using a stable on-disk key means --reload restarts don't destroy stored tokens.
_DEV_KEY_FILE = Path(__file__).resolve().parents[3] / "var" / "gmail_dev.key"


def _get_fernet() -> Fernet:
    """
    Return a Fernet instance keyed from GOOGLE_TOKEN_ENCRYPTION_KEY.

    In development (key absent), generate a per-process key and warn loudly.
    In production, a missing key raises RuntimeError.
    """
    global _DEV_WARNING_ISSUED

    key = os.getenv("GOOGLE_TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ("production", "prod"):
            raise RuntimeError(
                "GOOGLE_TOKEN_ENCRYPTION_KEY must be set in production. "
                "Run: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        # Development fallback: generate a stable per-process key.
        # Tokens will not survive a server restart, which is acceptable in dev.
        if not _DEV_WARNING_ISSUED:
            logger.warning(
                "GOOGLE_TOKEN_ENCRYPTION_KEY not set. "
                "Using an ephemeral per-process key for development. "
                "Gmail connections will not survive server restarts."
            )
            _DEV_WARNING_ISSUED = True
        return _get_dev_fernet()

    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError(
            "GOOGLE_TOKEN_ENCRYPTION_KEY is not a valid Fernet key. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        ) from exc


# In-memory cache of the dev key (loaded from disk on first use)
_dev_key: bytes | None = None


def _get_dev_fernet() -> Fernet:
    """
    Return a stable development Fernet instance.

    Key is persisted to _DEV_KEY_FILE so that uvicorn --reload restarts do not
    regenerate it and invalidate tokens already stored in the database.
    The file lives in backend/var/ which is .gitignore'd.
    """
    global _dev_key
    if _dev_key is not None:
        return Fernet(_dev_key)

    # Try to load from disk first (survives --reload)
    try:
        if _DEV_KEY_FILE.exists():
            _dev_key = _DEV_KEY_FILE.read_bytes().strip()
            return Fernet(_dev_key)
    except Exception:
        pass  # if corrupt, generate a fresh one below

    # Generate and persist a new key
    _dev_key = Fernet.generate_key()
    try:
        _DEV_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DEV_KEY_FILE.write_bytes(_dev_key)
    except Exception:
        logger.warning(
            "Could not persist development Gmail key to %s. "
            "Tokens will be lost on next restart. "
            "Set GOOGLE_TOKEN_ENCRYPTION_KEY in .env to fix this permanently.",
            _DEV_KEY_FILE,
        )
    return Fernet(_dev_key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64-encoded ciphertext string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """
    Decrypt a ciphertext string. Raises ValueError on invalid/tampered data.
    Never logs the plaintext.
    """
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Token decryption failed — may be invalid or tampered.") from exc
