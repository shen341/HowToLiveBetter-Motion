"""TTS Client wrapper for Cloudflare Edge-TTS endpoint.
Generates MP3 audio for narration segments and extracts audio durations.
"""

import os
import time
from typing import Optional

import requests
from moviepy import AudioFileClip

from src.config import (
    TTS_API_URL,
    TTS_PITCH,
    TTS_SPEED,
    TTS_STYLE,
    TTS_VOICE,
)


class TTSClient:
    """Client for generating text-to-speech audio via Cloudflare Worker TTS."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        pitch: Optional[str] = None,
        style: Optional[str] = None,
    ):
        self.api_url = api_url or TTS_API_URL
        self.voice = voice or TTS_VOICE
        self.speed = speed if speed is not None else TTS_SPEED
        self.pitch = pitch or TTS_PITCH
        self.style = style or TTS_STYLE

    def generate_speech(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        max_retries: int = 3,
    ) -> float:
        """
        Generate MP3 speech for the given text, save to output_path,
        and return the exact audio duration in seconds.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        target_voice = voice or self.voice
        target_speed = speed if speed is not None else self.speed

        payload = {
            "input": text,
            "voice": target_voice,
            "speed": target_speed,
            "pitch": self.pitch,
            "style": self.style,
        }
        headers = {"Content-Type": "application/json"}

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                if response.status_code == 200 and len(response.content) > 500:
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    # Read exact audio duration using MoviePy AudioFileClip
                    audio_clip = AudioFileClip(output_path)
                    duration = float(audio_clip.duration)
                    audio_clip.close()
                    return duration
                else:
                    err_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    if attempt == max_retries:
                        raise RuntimeError(f"TTS service returned error: {err_msg}")
            except Exception as e:
                if attempt == max_retries:
                    raise RuntimeError(f"TTS request failed after {max_retries} attempts: {e}") from e
                time.sleep(1.5 * attempt)

        raise RuntimeError("Failed to generate speech audio.")
