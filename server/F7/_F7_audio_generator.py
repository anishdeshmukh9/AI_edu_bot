"""
Podcast Audio Generator using Sarvam AI Text-to-Speech

This module converts podcast scripts into audio with two distinct voices:
- Alex: Female voice (Ritu - natural Indian female voice)
- Sam: Male voice (Arvind - natural Indian male voice)

Requires: sarvamai, pydub, requests
Install: pip install sarvamai pydub requests

Sarvam AI provides high-quality, natural-sounding voices for Indian languages
and English with Indian accents.
"""

import os
import re
from pathlib import Path
from typing import Tuple, Optional
import tempfile
import logging
import requests

logger = logging.getLogger(__name__)

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not available. Install with: pip install pydub")

# Sarvam AI Configuration
SARVAM_API_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_STREAM_URL = "https://api.sarvam.ai/text-to-speech/stream"

# Voice configuration for hosts
VOICE_CONFIG = {
    "Alex": {
        "speaker": "pooja",  # Female voice
        "pace": 1.2,  # Slightly faster for enthusiasm
        "temperature": 0.7,  # More expressive
    },
    "Sam": {
        "speaker": "ratan",  # Male voice
        "pace": 1.1,  # Normal pace for explanations
        "temperature": 0.6,  # Slightly less variation
    }
}

# Common TTS parameters
DEFAULT_TTS_PARAMS = {
    "target_language_code": "en-IN",  # English with Indian accent
    "model": "bulbul:v3",
    "speech_sample_rate": 22050,
    "enable_preprocessing": True,
}


def parse_podcast_script(script: str) -> list[Tuple[str, str]]:
    """
    Parse podcast script into list of (speaker, text) tuples
    
    Args:
        script: Raw script text with "Alex:" and "Sam:" labels
        
    Returns:
        List of (speaker, dialogue) tuples
    """
    lines = []
    current_speaker = None
    current_text = []
    
    for line in script.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Check if line starts with speaker label
        if line.startswith('Alex:'):
            # Save previous speaker's text if exists
            if current_speaker and current_text:
                lines.append((current_speaker, ' '.join(current_text)))
            current_speaker = 'Alex'
            current_text = [line[5:].strip()]  # Remove "Alex:" prefix
            
        elif line.startswith('Sam:'):
            # Save previous speaker's text if exists
            if current_speaker and current_text:
                lines.append((current_speaker, ' '.join(current_text)))
            current_speaker = 'Sam'
            current_text = [line[4:].strip()]  # Remove "Sam:" prefix
            
        else:
            # Continuation of current speaker's text
            if current_speaker:
                current_text.append(line)
    
    # Add final speaker's text
    if current_speaker and current_text:
        lines.append((current_speaker, ' '.join(current_text)))
    
    return lines


def create_speech_segment_sarvam(
    text: str, 
    speaker: str, 
    api_key: Optional[str] = None
) -> AudioSegment:
    """
    Create audio segment using Sarvam AI TTS (streaming)
    
    Args:
        text: Text to convert to speech
        speaker: Speaker name (Alex or Sam)
        api_key: Sarvam AI API key (defaults to SARVAM_API_KEY env var)
        
    Returns:
        AudioSegment with the speech
    """
    if not PYDUB_AVAILABLE:
        raise ImportError("pydub is required. Install with: pip install pydub")
    
    # Get API key
    if api_key is None:
        api_key = os.getenv("SARVAM_API_KEY")
    
    if not api_key:
        raise ValueError(
            "Sarvam API key not found. Set SARVAM_API_KEY environment variable "
            "or pass api_key parameter"
        )
    
    # Get voice configuration for this speaker
    voice_config = VOICE_CONFIG.get(speaker, VOICE_CONFIG["Alex"])
    
    # Prepare request
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "speaker": voice_config["speaker"],
        "pace": voice_config["pace"],
        "temperature": voice_config["temperature"],
        "output_audio_codec": "mp3",
        **DEFAULT_TTS_PARAMS
    }
    
    # Create temporary file for this segment
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Stream the audio response
        logger.debug(f"Generating audio for {speaker}: {text[:50]}...")
        
        with requests.post(
            SARVAM_STREAM_URL, 
            headers=headers, 
            json=payload, 
            stream=True,
            timeout=60
        ) as response:
            response.raise_for_status()
            
            # Save streamed audio to file
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        # Load audio segment
        audio = AudioSegment.from_mp3(tmp_path)
        
        # Add small pause after each segment (0.5 seconds)
        pause = AudioSegment.silent(duration=500)
        audio = audio + pause
        
        return audio
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Sarvam AI API: {e}")
        raise RuntimeError(f"Failed to generate speech with Sarvam AI: {e}")
    
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception as e:
                logger.warning(f"Could not remove temp file {tmp_path}: {e}")


def generate_podcast_audio(
    script: str, 
    output_path: str,
    api_key: Optional[str] = None
) -> int:
    """
    Generate complete podcast audio from script using Sarvam AI
    
    Args:
        script: Podcast script with speaker labels
        output_path: Path to save the final MP3 file
        api_key: Sarvam AI API key (optional, uses env var if not provided)
        
    Returns:
        Duration in seconds
    """
    if not PYDUB_AVAILABLE:
        raise ImportError("pydub is required. Install with: pip install pydub")
    
    logger.info("🎙️ Starting podcast audio generation with Sarvam AI...")
    
    # Parse script into segments
    segments = parse_podcast_script(script)
    logger.info(f"📝 Parsed {len(segments)} dialogue segments")
    
    if not segments:
        raise ValueError("No valid dialogue segments found in script")
    
    # Create audio segments
    full_audio = AudioSegment.empty()
    
    for idx, (speaker, text) in enumerate(segments, 1):
        logger.info(f"🔊 Generating audio for segment {idx}/{len(segments)} ({speaker})")
        
        # Skip empty text
        if not text.strip():
            logger.warning(f"Skipping empty segment {idx}")
            continue
        
        try:
            # Generate speech for this segment
            segment_audio = create_speech_segment_sarvam(text, speaker, api_key)
            
            # Append to full audio
            full_audio += segment_audio
            
        except Exception as e:
            logger.error(f"Error generating segment {idx}: {e}")
            # Continue with other segments instead of failing completely
            continue
    
    if len(full_audio) == 0:
        raise RuntimeError("No audio segments were generated successfully")
    
    # Export final audio
    logger.info(f"💾 Exporting podcast to {output_path}")
    full_audio.export(output_path, format="mp3", bitrate="128k")
    
    # Calculate duration
    duration_seconds = int(len(full_audio) / 1000)  # Convert milliseconds to seconds
    
    logger.info(f"✅ Podcast generated successfully! Duration: {duration_seconds}s")
    
    return duration_seconds


def test_sarvam_connection(api_key: Optional[str] = None) -> bool:
    """
    Test connection to Sarvam AI API
    
    Args:
        api_key: Sarvam AI API key (optional)
        
    Returns:
        True if connection successful, False otherwise
    """
    if api_key is None:
        api_key = os.getenv("SARVAM_API_KEY")
    
    if not api_key:
        logger.error("No API key provided")
        return False
    
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": "Test",
        "speaker": "ritu",
        "pace": 1.0,
        "temperature": 0.6,
        "output_audio_codec": "mp3",
        **DEFAULT_TTS_PARAMS
    }
    
    try:
        response = requests.post(
            SARVAM_STREAM_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=10
        )
        response.raise_for_status()
        logger.info("✅ Sarvam AI connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Sarvam AI connection test failed: {e}")
        return False


# Example usage documentation
USAGE_EXAMPLE = """
# Example usage:

import os
from _F7_audio_generator import generate_podcast_audio, test_sarvam_connection

# Set your Sarvam AI API key
os.environ["SARVAM_API_KEY"] = "your-api-key-here"

# Test connection (optional)
if test_sarvam_connection():
    print("API connection successful!")

# Generate podcast
script = \"\"\"
Alex: Hey everyone! Today we're talking about Python programming.
Sam: That's right! Python is one of the most popular languages today.
Alex: So Sam, why is Python so popular?
Sam: Great question! Python is known for its simplicity and readability...
\"\"\"

output_file = "podcast.mp3"
duration = generate_podcast_audio(script, output_file)
print(f"Podcast generated: {duration} seconds")

# Alternative: pass API key directly
duration = generate_podcast_audio(
    script, 
    output_file, 
    api_key="your-api-key-here"
)
"""