#!/usr/bin/env python3
"""
read_aloud.py — Have Mimir read any text file or PDF aloud via Piper TTS
=========================================================================

Uses the same Piper voice model as Mimir (en_US-libritts_r-medium).
Can read the Burnwillow Sourcebook, vault PDFs, or any text file.

Usage:
    python scripts/read_aloud.py                          # Read sourcebook
    python scripts/read_aloud.py --file vault/dnd5e/SOURCE/phb.pdf
    python scripts/read_aloud.py --file docs/burnwillow_sourcebook.md
    python scripts/read_aloud.py --chapter 3              # Start from Chapter 3
    python scripts/read_aloud.py --list                   # List all chapters
    python scripts/read_aloud.py --save audiobook.wav     # Save to file
    python scripts/read_aloud.py --dry-run                # Preview text only
"""

import argparse
import io
import re
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

SOURCEBOOK = Path(__file__).resolve().parent.parent / "docs" / "burnwillow_sourcebook.md"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "piper"
MODEL_PATH = MODEL_DIR / "en_US-libritts_r-medium.onnx"

_voice = None


def load_voice():
    """Load Piper voice model (lazy singleton)."""
    global _voice
    if _voice is not None:
        return True
    try:
        from piper import PiperVoice
        if not MODEL_PATH.exists():
            print(f"Voice model not found: {MODEL_PATH}")
            return False
        _voice = PiperVoice.load(str(MODEL_PATH))
        return True
    except ImportError:
        print("piper-tts not installed. Run: pip install piper-tts")
        return False


def clean_for_speech(text: str) -> str:
    """Convert markdown/Rich markup to plain speech-friendly text."""
    text = re.sub(r'\[/?[^\]]*\]', '', text)      # Rich markup
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)       # italic
    text = re.sub(r'`(.+?)`', r'\1', text)         # code
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\|', ' ', text)                # tables
    text = re.sub(r'-{3,}', '', text)              # rulers
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def split_chapters(text: str) -> list:
    """Split text into (title, content) chapter pairs."""
    chapters = []
    parts = re.split(r'^(# .+)$', text, flags=re.MULTILINE)
    title, body = "Introduction", ""
    for part in parts:
        if part.startswith('# '):
            if body.strip():
                chapters.append((title, body.strip()))
            title = part.strip('# \n')
            body = ""
        else:
            body += part
    if body.strip():
        chapters.append((title, body.strip()))
    return chapters


def load_pdf_text(pdf_path: Path) -> str:
    """Extract all text from a PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("pypdf not installed. Run: pip install pypdf")
        sys.exit(1)
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"Page {i+1}.\n{text.strip()}")
    return "\n\n".join(pages)


def speak(text: str, save_path: str = None) -> bool:
    """Synthesize and play/save speech."""
    if not _voice or not text.strip():
        return False
    try:
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            if hasattr(_voice, 'synthesize_wav'):
                _voice.synthesize_wav(text, wf)
            else:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(_voice.config.sample_rate)
                for chunk in _voice.synthesize(text):
                    wf.writeframes(chunk.audio_int16_bytes)
        buf.seek(0)

        if save_path:
            with open(save_path, 'ab') as f:
                f.write(buf.read())
            return True

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp:
            tmp.write(buf.read())
            tmp.flush()
            subprocess.run(['paplay', tmp.name], timeout=60, capture_output=True)
        return True
    except Exception as e:
        print(f"  [TTS error: {e}]")
        return False


def split_paragraphs(text: str, max_len: int = 500) -> list:
    """Split text into speakable chunks."""
    paragraphs = []
    for block in text.split('\n\n'):
        block = block.strip()
        if not block or len(block) < 5:
            continue
        if len(block) > max_len:
            sentences = re.split(r'(?<=[.!?])\s+', block)
            chunk = ""
            for s in sentences:
                if len(chunk) + len(s) > max_len and chunk:
                    paragraphs.append(chunk.strip())
                    chunk = s
                else:
                    chunk = (chunk + " " + s).strip()
            if chunk.strip():
                paragraphs.append(chunk.strip())
        else:
            paragraphs.append(block)
    return paragraphs


def main():
    parser = argparse.ArgumentParser(description="Mimir reads aloud via Piper TTS")
    parser.add_argument("--file", type=str, help="Path to .md or .pdf file (default: sourcebook)")
    parser.add_argument("--chapter", type=int, help="Start from chapter N")
    parser.add_argument("--list", action="store_true", help="List chapters")
    parser.add_argument("--save", type=str, help="Save audio to WAV file")
    parser.add_argument("--dry-run", action="store_true", help="Print text only")
    args = parser.parse_args()

    # Determine source file
    source = Path(args.file) if args.file else SOURCEBOOK
    if not source.exists():
        print(f"File not found: {source}")
        sys.exit(1)

    # Load text
    if source.suffix.lower() == ".pdf":
        print(f"Loading PDF: {source.name}...")
        raw_text = load_pdf_text(source)
        chapters = [("Full Document", raw_text)]
    else:
        raw_text = source.read_text(encoding='utf-8')
        chapters = split_chapters(raw_text)

    if args.list:
        for i, (title, body) in enumerate(chapters, 1):
            words = len(body.split())
            mins = words // 150
            print(f"  {i:>2}. {title} ({words} words, ~{mins} min)")
        print(f"\n  Total: {sum(len(b.split()) for _, b in chapters)} words")
        return

    if not args.dry_run:
        if not load_voice():
            sys.exit(1)
        print(f"Voice: {MODEL_PATH.stem}")

    start = max(0, (args.chapter or 1) - 1)

    print(f"\n{'='*50}")
    print(f"  Reading: {source.name}")
    print(f"  Starting: {chapters[start][0]}")
    print(f"  Chapters: {len(chapters) - start}")
    print(f"{'='*50}\n")

    for i in range(start, len(chapters)):
        title, body = chapters[i]
        clean = clean_for_speech(body)
        paragraphs = split_paragraphs(clean)

        print(f"\n--- {title} ({len(paragraphs)} paragraphs) ---\n")
        if not args.dry_run:
            speak(title)

        for j, para in enumerate(paragraphs):
            print(f"  [{j+1}/{len(paragraphs)}] {para[:80]}...")
            if args.dry_run:
                continue
            speak(para, save_path=args.save)
            time.sleep(0.3)

    print("\n--- End ---")


if __name__ == "__main__":
    main()
