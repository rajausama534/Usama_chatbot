"""Optional ElevenLabs speech for Usama; Gemini Live remains the default.
Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the Mac environment,
or elevenlabs_api_key / elevenlabs_voice_id in local config/api_keys.json.
No credentials are included in the repository. Spoken greeting alone is cached.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import requests

from memory.config_manager import load_api_keys

CACHE_DIR = Path.home() / ".usama" / "voice_cache"
WELCOME = "Hi, my name is Osama."


def get_settings() -> dict | None:
    cfg = load_api_keys()
    key = (os.getenv("ELEVENLABS_API_KEY") or cfg.get("elevenlabs_api_key") or "").strip()
    voice = (os.getenv("ELEVENLABS_VOICE_ID") or cfg.get("elevenlabs_voice_id") or "").strip()
    if not key or not voice:
        return None
    return {
        "api_key": key,
        "voice_id": voice,
        "model_id": (os.getenv("ELEVENLABS_MODEL_ID")
                     or cfg.get("elevenlabs_model_id") or "eleven_multilingual_v2").strip(),
    }


def synthesize_pcm(text: str, settings: dict) -> bytes:
    """Return mono signed 16-bit PCM at 24 kHz, suitable for Usama's output queue.

    Only the fixed startup greeting is cached; personal conversations are never
    written to the TTS cache. Never print API keys or the request headers.
    """
    phrase = str(text or "").strip()
    if not phrase:
        return b""
    cache = None
    if phrase == WELCOME:
        digest = hashlib.sha256(
            (settings["voice_id"] + "|" + settings["model_id"] + "|" + phrase).encode()
        ).hexdigest()[:24]
        cache = CACHE_DIR / (digest + ".pcm")
        try:
            saved = cache.read_bytes()
            if saved and len(saved) % 2 == 0:
                return saved
        except OSError:
            pass

    response = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech/"
        + requests.utils.quote(settings["voice_id"], safe=""),
        headers={"xi-api-key": settings["api_key"], "accept": "audio/pcm"},
        params={"output_format": "pcm_24000"},
        json={"text": phrase, "model_id": settings["model_id"]},
        timeout=(5, 25),
    )
    response.raise_for_status()
    pcm = response.content
    if not pcm or len(pcm) % 2:
        raise ValueError("ElevenLabs returned invalid PCM audio")
    if cache:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            temp = cache.with_suffix(".tmp")
            temp.write_bytes(pcm)
            temp.replace(cache)
        except OSError:
            pass
    return pcm
