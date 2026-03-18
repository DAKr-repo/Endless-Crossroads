"""
tests/test_save_crypto.py — WO-V71.0 Save File Encryption Tests
================================================================
Tests for:
  - encrypt/decrypt round-trip
  - magic-header detection
  - load_save_file auto-detection (plain vs encrypted)
  - ensure_key idempotency
  - save_to_file env-var gate
  - backward compatibility (plain save loads when encryption enabled)
  - wrong-key error path
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from codex.core.save_crypto import (
    MAGIC_HEADER,
    decrypt_save,
    encrypt_save,
    ensure_key,
    is_encrypted,
    load_save_file,
    save_to_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_key() -> bytes:
    """Return a deterministic 32-byte key for test isolation."""
    return b"test_key_for_unit_tests_12345678"  # exactly 32 bytes


_SAMPLE_SAVE = {
    "player": "Asha",
    "hp": 14,
    "turn": 7,
    "items": ["sword", "shield"],
}


# ===========================================================================
# TestEncryptDecrypt — round-trip correctness
# ===========================================================================

class TestEncryptDecrypt:
    """Round-trip encrypt → decrypt must recover the original dict."""

    def test_round_trip_explicit_key(self):
        """encrypt then decrypt with the same explicit key returns original data."""
        key = _make_key()
        ciphertext = encrypt_save(_SAMPLE_SAVE, key=key)
        result = decrypt_save(ciphertext, key=key)
        assert result == _SAMPLE_SAVE

    def test_encrypted_output_starts_with_magic_header(self):
        """encrypt_save output must begin with MAGIC_HEADER."""
        key = _make_key()
        ciphertext = encrypt_save(_SAMPLE_SAVE, key=key)
        assert ciphertext.startswith(MAGIC_HEADER)

    def test_encrypted_output_is_bytes(self):
        """encrypt_save always returns bytes."""
        key = _make_key()
        result = encrypt_save({"x": 1}, key=key)
        assert isinstance(result, bytes)

    def test_decrypt_wrong_key_raises_value_error(self):
        """Decrypting with a different key produces corrupted JSON → ValueError."""
        key_a = b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 32 bytes
        key_b = b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"  # 32 bytes
        ciphertext = encrypt_save(_SAMPLE_SAVE, key=key_a)
        with pytest.raises(ValueError, match="(?i)invalid JSON|wrong key"):
            decrypt_save(ciphertext, key=key_b)

    def test_decrypt_missing_header_raises_value_error(self):
        """Attempting to decrypt plain JSON raises ValueError (no magic header)."""
        plain = json.dumps(_SAMPLE_SAVE).encode("utf-8")
        key = _make_key()
        with pytest.raises(ValueError):
            decrypt_save(plain, key=key)


# ===========================================================================
# TestIsEncrypted — header detection
# ===========================================================================

class TestIsEncrypted:
    """is_encrypted() must reliably distinguish encrypted from plain files."""

    def test_detects_magic_header(self):
        """is_encrypted returns True for encrypted bytes."""
        key = _make_key()
        ciphertext = encrypt_save({"a": 1}, key=key)
        assert is_encrypted(ciphertext) is True

    def test_returns_false_for_plain_json(self):
        """is_encrypted returns False for plain JSON bytes."""
        plain = json.dumps({"a": 1}).encode("utf-8")
        assert is_encrypted(plain) is False

    def test_returns_false_for_empty_bytes(self):
        """is_encrypted returns False for an empty byte string."""
        assert is_encrypted(b"") is False

    def test_returns_false_for_partial_header(self):
        """A truncated magic header is not treated as encrypted."""
        partial = MAGIC_HEADER[:4]
        assert is_encrypted(partial) is False


# ===========================================================================
# TestLoadSaveFile — auto-detection
# ===========================================================================

class TestLoadSaveFile:
    """load_save_file must transparently handle both plain and encrypted files."""

    def test_load_plain_json(self, tmp_path):
        """load_save_file reads plain JSON files correctly."""
        save_file = tmp_path / "save.json"
        save_file.write_text(json.dumps(_SAMPLE_SAVE), encoding="utf-8")
        result = load_save_file(save_file)
        assert result == _SAMPLE_SAVE

    def test_load_encrypted_file(self, tmp_path):
        """load_save_file decrypts an encrypted file when given the correct key."""
        key = _make_key()
        save_file = tmp_path / "save.enc"
        save_file.write_bytes(encrypt_save(_SAMPLE_SAVE, key=key))
        result = load_save_file(save_file, key=key)
        assert result == _SAMPLE_SAVE

    def test_backward_compat_plain_save_loads_when_encryption_enabled(
        self, tmp_path, monkeypatch
    ):
        """Old plain-JSON saves still load even when CODEX_ENCRYPT_SAVES=1."""
        monkeypatch.setenv("CODEX_ENCRYPT_SAVES", "1")
        save_file = tmp_path / "legacy.json"
        save_file.write_text(json.dumps(_SAMPLE_SAVE), encoding="utf-8")
        # load_save_file checks header, not env var — so plain JSON always works
        result = load_save_file(save_file)
        assert result == _SAMPLE_SAVE


# ===========================================================================
# TestEnsureKey — key persistence
# ===========================================================================

class TestEnsureKey:
    """ensure_key must be idempotent: same key returned on every call."""

    def test_creates_key_file_on_first_call(self, tmp_path):
        """ensure_key writes a .save_key file if one does not exist."""
        key = ensure_key(saves_dir=tmp_path)
        assert (tmp_path / ".save_key").exists()
        assert len(key) == 32

    def test_returns_same_key_on_second_call(self, tmp_path):
        """Second call returns the identical bytes without regenerating."""
        key1 = ensure_key(saves_dir=tmp_path)
        key2 = ensure_key(saves_dir=tmp_path)
        assert key1 == key2

    def test_creates_saves_dir_if_missing(self, tmp_path):
        """ensure_key creates the saves directory when it does not exist."""
        new_dir = tmp_path / "nested" / "saves"
        assert not new_dir.exists()
        ensure_key(saves_dir=new_dir)
        assert new_dir.exists()


# ===========================================================================
# TestSaveToFile — env-var gate
# ===========================================================================

class TestSaveToFile:
    """save_to_file must respect CODEX_ENCRYPT_SAVES."""

    def test_writes_plain_json_when_encryption_disabled(self, tmp_path, monkeypatch):
        """When CODEX_ENCRYPT_SAVES is unset, output is plain JSON."""
        monkeypatch.delenv("CODEX_ENCRYPT_SAVES", raising=False)
        dest = tmp_path / "save.json"
        save_to_file(dest, _SAMPLE_SAVE)
        raw = dest.read_bytes()
        assert not is_encrypted(raw)
        assert json.loads(raw) == _SAMPLE_SAVE

    def test_writes_encrypted_when_enabled(self, tmp_path, monkeypatch):
        """When CODEX_ENCRYPT_SAVES=1, output has MAGIC_HEADER."""
        key = _make_key()
        monkeypatch.setenv("CODEX_ENCRYPT_SAVES", "1")
        dest = tmp_path / "save.enc"
        save_to_file(dest, _SAMPLE_SAVE, key=key)
        raw = dest.read_bytes()
        assert is_encrypted(raw)

    def test_round_trip_via_save_and_load(self, tmp_path, monkeypatch):
        """save_to_file (encrypted) → load_save_file recovers original data."""
        key = _make_key()
        monkeypatch.setenv("CODEX_ENCRYPT_SAVES", "1")
        dest = tmp_path / "save.enc"
        save_to_file(dest, _SAMPLE_SAVE, key=key)
        result = load_save_file(dest, key=key)
        assert result == _SAMPLE_SAVE
