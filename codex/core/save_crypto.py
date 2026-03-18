"""Save file encryption for Codex game saves.

Zero-dependency encryption using base64 + XOR.
Backward compatible: unencrypted saves still load when encryption is enabled.
"""
import base64
import json
import os
from pathlib import Path
from typing import Optional

MAGIC_HEADER = b"CODEX_ENC_V1\n"
_KEY_FILE_NAME = ".save_key"


def _get_saves_dir() -> Path:
    """Get the saves directory path."""
    root = Path(__file__).resolve().parent.parent.parent
    return root / "saves"


def ensure_key(saves_dir: Optional[Path] = None) -> bytes:
    """Generate and store encryption key on first use. Returns key bytes.

    On first call the key is generated with ``os.urandom(32)`` and written
    to ``<saves_dir>/.save_key``.  Subsequent calls return the same bytes
    without generating a new key.

    Args:
        saves_dir: Override the default saves directory (used by tests).

    Returns:
        32-byte key as raw bytes.
    """
    saves_dir = saves_dir or _get_saves_dir()
    key_path = saves_dir / _KEY_FILE_NAME
    if key_path.exists():
        return key_path.read_bytes()
    key = os.urandom(32)
    saves_dir.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    return key


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR data with repeating key.

    Args:
        data: Input bytes to transform.
        key:  Key bytes (repeated cyclically to match ``data`` length).

    Returns:
        XOR-transformed bytes of the same length as ``data``.
    """
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def encrypt_save(data: dict, key: Optional[bytes] = None) -> bytes:
    """Encrypt a save dict. Returns bytes with magic header.

    Serialises *data* to compact JSON, XOR-encrypts with *key*, then
    base64-encodes the result and prepends :data:`MAGIC_HEADER`.

    Args:
        data: The save dictionary to encrypt.
        key:  Encryption key bytes.  Loaded from disk if ``None``.

    Returns:
        ``MAGIC_HEADER + base64(xor(json_bytes, key))``
    """
    if key is None:
        key = ensure_key()
    json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
    encrypted = _xor_bytes(json_bytes, key)
    encoded = base64.b64encode(encrypted)
    return MAGIC_HEADER + encoded


def decrypt_save(raw: bytes, key: Optional[bytes] = None) -> dict:
    """Decrypt save bytes. Raises ValueError if decryption fails.

    Args:
        raw: Raw bytes as read from disk (must start with MAGIC_HEADER).
        key: Encryption key bytes.  Loaded from disk if ``None``.

    Returns:
        Decrypted save dictionary.

    Raises:
        ValueError: If *raw* does not start with MAGIC_HEADER, or if the
                    decrypted payload is not valid JSON (e.g. wrong key).
    """
    if key is None:
        key = ensure_key()
    if not is_encrypted(raw):
        raise ValueError("Data does not have encryption header")
    payload = raw[len(MAGIC_HEADER):]
    decoded = base64.b64decode(payload)
    decrypted = _xor_bytes(decoded, key)
    try:
        return json.loads(decrypted.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Decryption produced invalid JSON (wrong key?): {exc}") from exc


def is_encrypted(raw: bytes) -> bool:
    """Check if raw bytes have the encryption magic header.

    Args:
        raw: Bytes to inspect.

    Returns:
        ``True`` if *raw* starts with :data:`MAGIC_HEADER`.
    """
    return raw.startswith(MAGIC_HEADER)


def is_encryption_enabled() -> bool:
    """Check if encryption is enabled via environment variable.

    Reads ``CODEX_ENCRYPT_SAVES`` from the environment.  Truthy values are
    ``"1"``, ``"true"``, and ``"yes"`` (case-insensitive after strip).

    Returns:
        ``True`` if saves should be encrypted.
    """
    return os.environ.get("CODEX_ENCRYPT_SAVES", "").strip().lower() in ("1", "true", "yes")


def load_save_file(path: Path, key: Optional[bytes] = None) -> dict:
    """Load a save file, auto-detecting encrypted vs plain JSON.

    Args:
        path: Path to the save file on disk.
        key:  Encryption key bytes.  Loaded from disk if ``None``.

    Returns:
        Parsed save dictionary.

    Raises:
        ValueError: If the file appears encrypted but decryption fails.
        json.JSONDecodeError: If the file is not valid JSON (plain mode).
    """
    raw = path.read_bytes()
    if is_encrypted(raw):
        return decrypt_save(raw, key=key)
    # Plain JSON fallback — supports old unencrypted saves
    return json.loads(raw.decode('utf-8'))


def save_to_file(path: Path, data: dict, key: Optional[bytes] = None) -> None:
    """Save data to file, encrypting if enabled.

    Respects the ``CODEX_ENCRYPT_SAVES`` environment variable.  When
    encryption is off the file is written as pretty-printed JSON so it
    remains human-readable.

    Args:
        path: Destination file path.  Parent directories are not created
              here — callers are expected to ensure the directory exists.
        data: Save dictionary to serialise.
        key:  Encryption key bytes.  Loaded from disk if ``None``.
    """
    if is_encryption_enabled():
        path.write_bytes(encrypt_save(data, key=key))
    else:
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
