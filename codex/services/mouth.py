"""
codex_mouth.py - The Mouth Service (Local Cloud TTS)
=====================================================
Persistent HTTP microservice running Piper TTS for
text-to-speech synthesis on the Raspberry Pi 5.

WO 084-B | Part of the Local Cloud architecture
Port: 5001 | Engine: piper-tts | Voice: configurable via env

Setup:
    pip install piper-tts
    # Download a voice model:
    mkdir -p models/piper
    cd models/piper
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json
"""

import os
import io
import wave
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# ============================================================================
# Dependency Check
# ============================================================================

PIPER_AVAILABLE = False
VOICE_MODEL_AVAILABLE = False
VOICE_OBJECT = None
ERROR_MESSAGE = ""

try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    ERROR_MESSAGE = (
        "piper-tts is not installed. Install with:\n"
        "  pip install piper-tts\n"
        "Or add to requirements.txt and run: pip install -r requirements_mouth.txt"
    )

# ============================================================================
# Configuration
# ============================================================================

from codex.paths import PIPER_MODEL_DIR

DEFAULT_MODEL_PATH = str(PIPER_MODEL_DIR / "en_US-libritts_r-medium.onnx")
VOICE_MODEL_PATH = os.getenv("PIPER_VOICE_MODEL", DEFAULT_MODEL_PATH)

# ============================================================================
# Request/Response Models
# ============================================================================

class SpeakRequest(BaseModel):
    text: str
    speaker_id: Optional[int] = None
    length_scale: Optional[float] = None
    noise_scale: Optional[float] = None
    noise_w_scale: Optional[float] = None
    model_path: Optional[str] = None  # Override voice model (e.g. Norwegian narrator)

class HealthResponse(BaseModel):
    status: str
    voice: Optional[str] = None
    engine: str = "piper-tts"
    error: Optional[str] = None

# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Piper voice model at startup."""
    global VOICE_OBJECT, VOICE_MODEL_AVAILABLE, ERROR_MESSAGE

    if not PIPER_AVAILABLE:
        print(f"MOUTH: ERROR - {ERROR_MESSAGE}")
        yield
        return

    # Check if model file exists
    model_path = Path(VOICE_MODEL_PATH)
    if not model_path.exists():
        ERROR_MESSAGE = (
            f"Voice model not found at: {VOICE_MODEL_PATH}\n"
            f"Download with:\n"
            f"  mkdir -p models/piper\n"
            f"  cd models/piper\n"
            f"  wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx\n"
            f"  wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json"
        )
        print(f"MOUTH: ERROR - {ERROR_MESSAGE}")
        yield
        return

    # Check for .json config file
    config_path = model_path.with_suffix(model_path.suffix + ".json")
    if not config_path.exists():
        ERROR_MESSAGE = (
            f"Voice model config not found at: {config_path}\n"
            f"Both .onnx and .onnx.json files are required."
        )
        print(f"MOUTH: ERROR - {ERROR_MESSAGE}")
        yield
        return

    try:
        print(f"MOUTH: Loading voice model from {VOICE_MODEL_PATH}...")
        VOICE_OBJECT = PiperVoice.load(str(model_path))
        VOICE_MODEL_AVAILABLE = True
        print(f"MOUTH: Online on :5001")
    except Exception as e:
        ERROR_MESSAGE = f"Failed to load voice model: {str(e)}"
        print(f"MOUTH: ERROR - {ERROR_MESSAGE}")

    yield

    # Cleanup on shutdown
    if VOICE_OBJECT:
        print("MOUTH: Shutting down...")

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="C.O.D.E.X. Mouth Service",
    description="Local Cloud Text-to-Speech using Piper",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not PIPER_AVAILABLE or not VOICE_MODEL_AVAILABLE:
        return HealthResponse(
            status="offline",
            voice=None,
            engine="piper-tts",
            error=ERROR_MESSAGE
        )

    return HealthResponse(
        status="online",
        voice=Path(VOICE_MODEL_PATH).name,
        engine="piper-tts"
    )

@app.post("/speak")
async def speak(request: SpeakRequest):
    """
    Synthesize speech from text.

    Returns WAV audio stream.
    """
    # Check if service is ready
    if not PIPER_AVAILABLE or not VOICE_MODEL_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service unavailable",
                "message": ERROR_MESSAGE
            }
        )

    if not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text field cannot be empty"
        )

    # Support alternate voice model — constrained to models directory
    voice_obj = VOICE_OBJECT
    if request.model_path and PIPER_AVAILABLE:
        import os.path as _osp
        base_path = _osp.realpath(str(Path(VOICE_MODEL_PATH).parent))
        # Use os.path.normpath + startswith (CodeQL-approved pattern)
        fullpath = _osp.normpath(_osp.join(base_path, request.model_path))
        if fullpath.startswith(base_path + os.sep) and os.path.isfile(fullpath):
            try:
                voice_obj = PiperVoice.load(fullpath)
            except Exception:
                voice_obj = VOICE_OBJECT

    import asyncio

    def _synthesize_blocking(
        text: str,
        speaker_id: Optional[int] = None,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w_scale: Optional[float] = None,
    ) -> io.BytesIO:
        """Run piper synthesis in a thread to avoid blocking the event loop."""
        # Build SynthesisConfig if modulation params are provided
        syn_config = None
        try:
            from piper.voice import SynthesisConfig
            syn_config = SynthesisConfig()
            if speaker_id is not None:
                syn_config.speaker_id = speaker_id
            if length_scale is not None:
                syn_config.length_scale = length_scale
            if noise_scale is not None:
                syn_config.noise_scale = noise_scale
            if noise_w_scale is not None:
                syn_config.noise_w = noise_w_scale
        except (ImportError, AttributeError):
            syn_config = None  # Older piper-tts — ignore modulation

        # Use voice_obj from closure (supports alternate narrator model)
        _voice = voice_obj
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, "wb") as wav_file:
            if hasattr(_voice, 'synthesize_wav'):
                kwargs = {}
                if syn_config is not None:
                    kwargs["syn_config"] = syn_config
                _voice.synthesize_wav(text, wav_file, **kwargs)
            elif hasattr(_voice, 'synthesize'):
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(_voice.config.sample_rate)
                syn_kwargs = {}
                if syn_config is not None:
                    syn_kwargs["syn_config"] = syn_config
                for audio_chunk in _voice.synthesize(text, **syn_kwargs):
                    wav_file.writeframes(audio_chunk.audio_int16_bytes)
            else:
                raise RuntimeError("PiperVoice object has no synthesize method")
        audio_buffer.seek(0)
        return audio_buffer

    try:
        audio_buffer = await asyncio.to_thread(
            _synthesize_blocking,
            request.text,
            request.speaker_id,
            request.length_scale,
            request.noise_scale,
            request.noise_w_scale,
        )

        return StreamingResponse(
            audio_buffer,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Speech synthesis failed: {str(e)}"
        )

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5001)
