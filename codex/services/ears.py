"""
codex_ears.py - The Ears Service (Local Cloud STT)
===================================================
Persistent HTTP microservice running faster-whisper for
speech-to-text transcription on the Raspberry Pi 5.

WO 084-A | Part of the Local Cloud architecture
Port: 5000 | Model: base.en | Quantization: int8
"""

import asyncio
import os
import re
import json
import tempfile
import requests
from contextlib import asynccontextmanager
from typing import Dict, Any

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import uvicorn

from codex.core.butler import CodexButler

# --- Global State ---
MODEL = None
BUTLER = CodexButler()
_transcribe_semaphore = asyncio.Semaphore(1)

# --- Voice Intelligence Constants ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mimir"
OLLAMA_TIMEOUT = 30  # seconds — Pi 5 needs headroom for longer prompts

VOICE_SYSTEM_PROMPT = (
    "You are Codex, a concise philosopher and voice assistant. "
    "Respond in 1-2 short sentences suitable for text-to-speech. "
    "Do not use markdown, bullet points, code blocks, or special characters. "
    "Speak naturally as if in conversation. "
    "If you do not know something, say so briefly."
)

OLLAMA_FALLBACK = "I heard you, but I could not think of a response. Try again."


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for loading the faster-whisper model at startup.
    """
    global MODEL
    try:
        from faster_whisper import WhisperModel
        print("EARS: Loading faster-whisper model (base.en, int8)...")
        MODEL = WhisperModel("base.en", device="cpu", compute_type="int8")
        print("EARS: Model loaded successfully")
        print("EARS: Online on :5000")
        yield
    finally:
        print("EARS: Shutting down...")
        MODEL = None


app = FastAPI(
    title="C.O.D.E.X. Ears Service",
    description="Speech-to-Text microservice using faster-whisper",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN access needed for push-to-talk from player devices
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

from codex.paths import TEMPLATES_DIR
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def comms_page(request: Request):
    """Serve the Comms Link push-to-talk interface."""
    return templates.TemplateResponse("comms.html", {"request": request})


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        JSON with service status, model name, and compute type
    """
    return {
        "status": "online",
        "model": "base.en",
        "compute": "int8"
    }


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Transcribe uploaded audio file to text.

    Args:
        file: Audio file (WAV format recommended)

    Returns:
        JSON with transcribed text, language, and duration

    Raises:
        HTTPException: 500 if transcription fails
    """
    global MODEL

    if MODEL is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded yet. Service may be starting up."
        )

    async with _transcribe_semaphore:
        temp_path = None

        try:
            # Create temporary file for uploaded audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                # Write uploaded content to temp file
                content = await file.read()
                temp_file.write(content)

            # Run transcription off the event loop
            segments, info = await asyncio.to_thread(
                MODEL.transcribe, temp_path, beam_size=1
            )

            # Extract text from segments generator
            text = " ".join(seg.text.strip() for seg in segments)

            return {
                "text": text,
                "language": info.language,
                "duration": info.duration
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {str(e)}"
            )

        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    print(f"EARS: Warning - failed to clean up {temp_path}: {cleanup_error}")


def _query_ollama(text: str) -> str:
    """Query Ollama for a voice-mode response. Returns text or fallback."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": text,
        "system": VOICE_SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "num_predict": 128,
            "temperature": 0.7,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        if resp.status_code != 200:
            print(f"EARS: Ollama returned {resp.status_code}")
            return OLLAMA_FALLBACK
        content = resp.json().get("response", "").strip()
        # Strip <think> tags from reasoning models
        if "<think>" in content:
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content if content else OLLAMA_FALLBACK
    except requests.exceptions.Timeout:
        print("EARS: Ollama timeout — returning fallback")
        return OLLAMA_FALLBACK
    except requests.exceptions.ConnectionError:
        print("EARS: Ollama not reachable — returning fallback")
        return OLLAMA_FALLBACK
    except Exception as e:
        print(f"EARS: Ollama error — {e}")
        return OLLAMA_FALLBACK


@app.post("/relay_speech")
async def relay_speech(request: Request) -> Response:
    """
    Voice Intelligence Relay.

    Pipeline:
      1. Receive transcribed text
      2. Check Mimir (Butler) reflexes — dice, time, ping, status
      3. If no reflex: query Codex (Ollama) for conversational response
      4. Send response text to Mouth (TTS) and return WAV
    """
    try:
        body = await request.json()
        user_text = body.get("text", "").strip()

        if not user_text:
            raise HTTPException(status_code=400, detail="No text provided")

        # --- Step 1: Mimir Reflex Check ---
        response_text = BUTLER.check_reflex(user_text)
        source = "mimir"

        if response_text is not None:
            response_text = CodexButler.voice_clean(response_text)
            print(f"EARS: Mimir reflex hit: '{user_text}' -> '{response_text}'")
        else:
            # --- Step 2: Codex (Ollama) Fallback ---
            source = "codex"
            print(f"EARS: No reflex, consulting Codex: '{user_text}'")
            response_text = _query_ollama(user_text)
            print(f"EARS: Codex responded ({len(response_text)} chars)")

        # --- Step 3: Send to Mouth (TTS) ---
        try:
            tts_response = requests.post(
                "http://localhost:5001/speak",
                json={"text": response_text},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )

            if tts_response.status_code == 200:
                return Response(
                    content=tts_response.content,
                    media_type="audio/wav",
                    headers={
                        "X-Voice-Source": source,
                        "X-Voice-Text": response_text[:100].encode("ascii", "replace").decode(),
                    },
                )
            else:
                print(f"EARS: Mouth error {tts_response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"EARS: Mouth unavailable — {e}")

        # --- Fallback: return text as JSON if Mouth is down ---
        return JSONResponse(
            content={"text": response_text, "source": source, "tts": False},
            status_code=200,
            headers={"X-Voice-Source": source},
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"EARS: Relay error — {e}")
        raise HTTPException(status_code=500, detail=f"Relay failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
