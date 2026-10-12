"""Configuration and environment variable loader for HowToLiveBetter-Motion."""

import os
from dotenv import load_dotenv

# Load .env if present
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

MUSE_API_KEY = os.getenv("MUSE_API_KEY", "")
MUSE_BASE_URL = os.getenv("MUSE_BASE_URL", "https://yourselfai.org/muse/v1")

MODEL_TEXT = os.getenv("MODEL_TEXT", "muse-spark")
MODEL_IMAGE = os.getenv("MODEL_IMAGE", "muse-image")
MODEL_VIDEO = os.getenv("MODEL_VIDEO", "muse-video")

# TTS Voice configuration (Cloudflare Edge-TTS Worker)
TTS_API_URL = os.getenv(
    "TTS_API_URL",
    "https://tts-voice-magic.shimizuhiro874-28e.workers.dev/v1/audio/speech"
)
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-YunzeNeural")
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))
TTS_PITCH = os.getenv("TTS_PITCH", "0")
TTS_STYLE = os.getenv("TTS_STYLE", "general")

# Rate Limiting & Retry Configuration (TASK-4.3)
RATE_LIMIT_MUSE_RPM = int(os.getenv("RATE_LIMIT_MUSE_RPM", "30"))  # Muse AI Requests Per Minute
RATE_LIMIT_TTS_RPM = int(os.getenv("RATE_LIMIT_TTS_RPM", "60"))    # Edge-TTS Requests Per Minute
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))           # Max retry attempts for transient errors
API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "2.0"))       # Initial backoff delay (seconds)

# Platform Video Preset Configuration (TASK-4.4)
DEFAULT_PLATFORM_PRESET = os.getenv("PLATFORM_PRESET", "default")   # default / xhs / douyin / wechat / bilibili

OUTPUT_RAW_ASSETS_DIR = os.path.join(ROOT_DIR, "output", "raw_assets")
OUTPUT_FINAL_VIDEOS_DIR = os.path.join(ROOT_DIR, "output", "final_videos")
BACKGROUP_MUSIC_DIR = os.path.join(ROOT_DIR, "backgroup_music")
ASSETS_BGM_DIR = os.path.join(ROOT_DIR, "assets", "bgm")
ASSETS_FONTS_DIR = os.path.join(ROOT_DIR, "assets", "fonts")

# Ensure essential output and asset directories exist
os.makedirs(OUTPUT_RAW_ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_FINAL_VIDEOS_DIR, exist_ok=True)
os.makedirs(BACKGROUP_MUSIC_DIR, exist_ok=True)
os.makedirs(ASSETS_BGM_DIR, exist_ok=True)
os.makedirs(ASSETS_FONTS_DIR, exist_ok=True)
