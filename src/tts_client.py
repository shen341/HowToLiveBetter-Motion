"""TTS Client wrapper for Cloudflare Edge-TTS endpoint.
Generates MP3 audio for narration segments and extracts audio durations.
"""

import os
import time
from typing import Optional

import requests
from moviepy import AudioFileClip

from src.config import (
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    RATE_LIMIT_TTS_RPM,
    TTS_API_URL,
    TTS_PITCH,
    TTS_SPEED,
    TTS_STYLE,
    TTS_VOICE,
)
from src.rate_limiter import TokenBucketLimiter, retry_with_backoff


class TTSClient:
    """Client for generating text-to-speech audio via Cloudflare Worker TTS with rate limiting and exponential backoff."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        pitch: Optional[str] = None,
        style: Optional[str] = None,
        rate_limit_rpm: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ):
        self.api_url = api_url or TTS_API_URL
        self.voice = voice or TTS_VOICE
        self.speed = speed if speed is not None else TTS_SPEED
        self.pitch = pitch or TTS_PITCH
        self.style = style or TTS_STYLE
        self.rate_limit_rpm = rate_limit_rpm if rate_limit_rpm is not None else RATE_LIMIT_TTS_RPM
        self.max_retries = max_retries if max_retries is not None else API_MAX_RETRIES
        self.retry_delay = retry_delay if retry_delay is not None else API_RETRY_DELAY

        self.limiter = TokenBucketLimiter(rate_per_minute=self.rate_limit_rpm)

    def generate_speech(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> float:
        """
        Generate MP3 speech for the given text, save to output_path,
        and return the exact audio duration in seconds.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        target_voice = voice or self.voice
        target_speed = speed if speed is not None else self.speed
        effective_retries = max_retries if max_retries is not None else self.max_retries

        payload = {
            "input": text,
            "voice": target_voice,
            "speed": target_speed,
            "pitch": self.pitch,
            "style": self.style,
        }
        headers = {"Content-Type": "application/json"}

        def _do_tts_request() -> float:
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
            elif response.status_code != 200:
                response.raise_for_status()
                raise RuntimeError(f"TTS service returned error: HTTP {response.status_code}")
            else:
                raise RuntimeError(f"TTS returned empty or invalid audio ({len(response.content)} bytes)")

        return retry_with_backoff(
            _do_tts_request,
            max_retries=effective_retries,
            initial_delay=self.retry_delay,
            service_name="Cloudflare-TTS",
            limiter=self.limiter,
        )

