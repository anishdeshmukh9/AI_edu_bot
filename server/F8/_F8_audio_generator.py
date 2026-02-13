# F8/_F8_audio_generator.py

import os
import tempfile
from pydub import AudioSegment
import requests
import logging

logger = logging.getLogger(__name__)

SARVAM_STREAM_URL = "https://api.sarvam.ai/text-to-speech/stream"

DEFAULT_TTS_PARAMS = {
    "target_language_code": "en-IN",
    "model": "bulbul:v3",
    "speech_sample_rate": 22050,
    "enable_preprocessing": True,
}

KRISHNA_VOICE = {
    "speaker": "ratan",   # calm, deep male voice
    "pace": 0.95,
    "temperature": 0.5,
}

def generate_gita_audio(text: str) -> str:
    """
    Converts Krishna guidance text into an MP3 file.
    Returns local file path.
    """

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise ValueError("SARVAM_API_KEY not set")

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "speaker": KRISHNA_VOICE["speaker"],
        "pace": KRISHNA_VOICE["pace"],
        "temperature": KRISHNA_VOICE["temperature"],
        "output_audio_codec": "mp3",
        **DEFAULT_TTS_PARAMS
    }

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_path = tmp_file.name
    tmp_file.close()

    with requests.post(
        SARVAM_STREAM_URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=90
    ) as r:
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    return tmp_path