"""
test_voice_bridge.py — Unit tests for WO-V13.1 VoiceBridge
===========================================================
Tests: VoiceCue, parse_voice_cue, get_npc_speaker_id,
       VoiceBridge toggle/synthesize/speak, SpeakRequest model,
       VOICE_CUE_TABLE completeness.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from codex.services.voice_bridge import (
    VoiceBridge,
    VoiceCue,
    VOICE_CUE_TABLE,
    NPC_VOICE_POOLS,
    get_npc_speaker_id,
    parse_voice_cue,
)


class TestVoiceCueDefaults(unittest.TestCase):
    """T1: VoiceCue defaults are sane."""

    def test_defaults(self):
        cue = VoiceCue(tag="test")
        self.assertEqual(cue.tag, "test")
        self.assertIsNone(cue.speaker_id)
        self.assertEqual(cue.length_scale, 1.0)
        self.assertAlmostEqual(cue.noise_scale, 0.333)
        self.assertAlmostEqual(cue.noise_w_scale, 0.333)


class TestParseVoiceCue(unittest.TestCase):
    """T2-T4: Voice cue parsing."""

    def test_extracts_known_tag(self):
        """T2: parse_voice_cue extracts known tag."""
        text, cue = parse_voice_cue("[Gravelly] Welcome to my forge, stranger.")
        self.assertIsNotNone(cue)
        self.assertEqual(cue.tag, "Gravelly")
        self.assertEqual(text, "Welcome to my forge, stranger.")
        self.assertAlmostEqual(cue.length_scale, 1.1)
        self.assertAlmostEqual(cue.noise_scale, 0.6)

    def test_returns_none_for_unknown_tag(self):
        """T3: parse_voice_cue returns None for unknown tag."""
        text, cue = parse_voice_cue("[Excited] This is not a known cue.")
        self.assertIsNone(cue)
        self.assertEqual(text, "[Excited] This is not a known cue.")

    def test_handles_empty_text(self):
        """T4: parse_voice_cue handles empty/no-bracket text."""
        text, cue = parse_voice_cue("")
        self.assertEqual(text, "")
        self.assertIsNone(cue)

        text2, cue2 = parse_voice_cue("No brackets here.")
        self.assertEqual(text2, "No brackets here.")
        self.assertIsNone(cue2)

    def test_case_insensitive(self):
        """parse_voice_cue is case-insensitive for tag lookup."""
        text, cue = parse_voice_cue("[HUSHED] Be quiet.")
        self.assertIsNotNone(cue)
        self.assertEqual(cue.tag, "Hushed")
        self.assertEqual(text, "Be quiet.")


class TestGetNPCSpeakerId(unittest.TestCase):
    """T5-T7: NPC speaker ID determinism and pool routing."""

    def test_deterministic(self):
        """T5: get_npc_speaker_id is deterministic."""
        sid1 = get_npc_speaker_id("Bran the Smith", "merchant")
        sid2 = get_npc_speaker_id("Bran the Smith", "merchant")
        self.assertEqual(sid1, sid2)

    def test_stays_in_bounds(self):
        """T6: get_npc_speaker_id stays in pool bounds."""
        for name in ["Alice", "Bob", "Xyzzy", "A" * 100, ""]:
            for role in NPC_VOICE_POOLS:
                sid = get_npc_speaker_id(name, role)
                pool = NPC_VOICE_POOLS[role]
                self.assertIn(sid, pool)

    def test_uses_role_pool(self):
        """T7: get_npc_speaker_id uses role pool."""
        sid = get_npc_speaker_id("Narrator", "narrator")
        self.assertEqual(sid, 24)  # narrator pool has only [24]

    def test_unknown_role_uses_default(self):
        """Unknown role falls back to default pool."""
        sid = get_npc_speaker_id("Test", "unknown_role")
        self.assertIn(sid, NPC_VOICE_POOLS["default"])


class TestVoiceBridgeToggle(unittest.TestCase):
    """T8: VoiceBridge.enabled toggle."""

    def test_default_enabled(self):
        vb = VoiceBridge()
        self.assertTrue(vb.enabled)

    def test_toggle(self):
        vb = VoiceBridge()
        vb.enabled = False
        self.assertFalse(vb.enabled)
        vb.enabled = True
        self.assertTrue(vb.enabled)


class TestVoiceBridgeSynthesize(unittest.TestCase):
    """T9-T10: VoiceBridge.synthesize."""

    def test_builds_correct_payload(self):
        """T9: VoiceBridge.synthesize builds correct payload (mocked HTTP)."""
        vb = VoiceBridge()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b"RIFF_WAV_DATA")

        mock_session_ctx = AsyncMock()
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_ctx)
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("codex.services.voice_bridge.aiohttp.ClientSession",
                   return_value=mock_session_ctx):
            result = asyncio.run(
                vb.synthesize("Hello", speaker_id=24, length_scale=1.2)
            )

        self.assertEqual(result, b"RIFF_WAV_DATA")
        call_args = mock_session.post.call_args
        payload = call_args.kwargs.get("json", call_args[1].get("json", {}))
        self.assertEqual(payload["text"], "Hello")
        self.assertEqual(payload["speaker_id"], 24)
        self.assertEqual(payload["length_scale"], 1.2)

    def test_returns_none_on_error(self):
        """T10: VoiceBridge.synthesize returns None on HTTP error."""
        vb = VoiceBridge()

        mock_resp = AsyncMock()
        mock_resp.status = 500

        mock_session_ctx = AsyncMock()
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_ctx)
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("codex.services.voice_bridge.aiohttp.ClientSession",
                   return_value=mock_session_ctx):
            result = asyncio.run(
                vb.synthesize("Hello")
            )
        self.assertIsNone(result)


class TestVoiceBridgeSpeakDiscord(unittest.TestCase):
    """T11: VoiceBridge.speak_discord no-ops when disabled."""

    def test_noop_when_disabled(self):
        """T11: speak_discord does nothing when disabled."""
        vb = VoiceBridge()
        vb.enabled = False
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = True
        # Should not raise, should not enqueue
        asyncio.run(
            vb.speak_discord("test", mock_vc)
        )
        self.assertTrue(vb._queue.empty())


class TestVoiceBridgeSpeakTerminal(unittest.TestCase):
    """T12: VoiceBridge.speak_terminal pipes to subprocess (mocked)."""

    @patch("codex.services.voice_bridge.shutil.which", return_value="/usr/bin/aplay")
    @patch("codex.services.voice_bridge.subprocess.Popen")
    def test_pipes_to_aplay(self, mock_popen, mock_which):
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_popen.return_value = mock_proc

        VoiceBridge.speak_terminal(b"WAV_DATA")

        mock_popen.assert_called_once()
        mock_proc.stdin.write.assert_called_once_with(b"WAV_DATA")
        mock_proc.stdin.close.assert_called_once()

    @patch("codex.services.voice_bridge.shutil.which", return_value=None)
    @patch("codex.services.voice_bridge.subprocess.Popen")
    def test_skips_when_no_aplay(self, mock_popen, mock_which):
        VoiceBridge.speak_terminal(b"WAV_DATA")
        mock_popen.assert_not_called()

    def test_skips_empty_bytes(self):
        VoiceBridge.speak_terminal(b"")  # Should not raise


@unittest.skipUnless(
    __import__("importlib").util.find_spec("fastapi"),
    "fastapi not installed (optional, in requirements_mouth.txt)")
class TestSpeakRequest(unittest.TestCase):
    """T13-T14: SpeakRequest model."""

    def test_accepts_modulation_params(self):
        """T13: SpeakRequest accepts modulation params."""
        from codex.services.mouth import SpeakRequest
        req = SpeakRequest(
            text="Hello",
            speaker_id=24,
            length_scale=1.2,
            noise_scale=0.5,
            noise_w_scale=0.4,
        )
        self.assertEqual(req.text, "Hello")
        self.assertEqual(req.speaker_id, 24)
        self.assertEqual(req.length_scale, 1.2)
        self.assertEqual(req.noise_scale, 0.5)
        self.assertEqual(req.noise_w_scale, 0.4)

    def test_backward_compat(self):
        """T14: SpeakRequest backward compat (text-only)."""
        from codex.services.mouth import SpeakRequest
        req = SpeakRequest(text="Hello world")
        self.assertEqual(req.text, "Hello world")
        self.assertIsNone(req.speaker_id)
        self.assertIsNone(req.length_scale)
        self.assertIsNone(req.noise_scale)
        self.assertIsNone(req.noise_w_scale)


class TestVoiceCueTable(unittest.TestCase):
    """T15: VOICE_CUE_TABLE has all 7 entries."""

    def test_has_all_entries(self):
        expected = {"hushed", "urgent", "gravelly", "solemn", "cheerful", "menacing", "narrator"}
        self.assertEqual(set(VOICE_CUE_TABLE.keys()), expected)

    def test_all_entries_are_voice_cues(self):
        for key, cue in VOICE_CUE_TABLE.items():
            self.assertIsInstance(cue, VoiceCue)
            self.assertTrue(cue.length_scale > 0)
            self.assertTrue(cue.noise_scale >= 0)
            self.assertTrue(cue.noise_w_scale >= 0)


if __name__ == "__main__":
    unittest.main()
