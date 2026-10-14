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

# Fallback OpenAI-compatible API Configuration (YourselfAI / Gemini)
YOURSELFAI_API_KEY = os.getenv("YOURSELFAI_API_KEY", "")
YOURSELFAI_BASE_URL = os.getenv("YOURSELFAI_BASE_URL", "https://yourselfai.org/v1")
YOURSELFAI_MODEL = os.getenv("YOURSELFAI_MODEL", "gemini-3.8-flash-high")
YOURSELFAI_IMAGE_MODEL = os.getenv("YOURSELFAI_IMAGE_MODEL", "gemini-3.1-flash-image")
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "180.0"))

# AI 架构模式控制: "hybrid" (黄金混合推荐: 云端Gemini剧本 + 本地RTX4070原画), "local" (全本地), "cloud" (全云端)
AI_MODE = os.getenv("AI_MODE", "hybrid").lower().strip()

# --- [阶段一: 本地大模型 LLM (Ollama OpenAI 兼容协议)] ---
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen2.5vl:7b")
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "ollama")

# 根据 AI_MODE 动态决定主线大模型接入点
if AI_MODE == "local":
    ACTIVE_TEXT_BASE_URL = LOCAL_LLM_BASE_URL
    ACTIVE_TEXT_MODEL = LOCAL_LLM_MODEL
    ACTIVE_TEXT_API_KEY = LOCAL_LLM_API_KEY
elif AI_MODE == "hybrid":
    # 黄金混合模式: 使用极速高质的 Gemini 3.8 Flash High 生成不重复黄金分镜
    ACTIVE_TEXT_BASE_URL = YOURSELFAI_BASE_URL
    ACTIVE_TEXT_MODEL = YOURSELFAI_MODEL
    ACTIVE_TEXT_API_KEY = YOURSELFAI_API_KEY
else:
    ACTIVE_TEXT_BASE_URL = MUSE_BASE_URL
    ACTIVE_TEXT_MODEL = MODEL_TEXT
    ACTIVE_TEXT_API_KEY = MUSE_API_KEY

# --- [阶段三: 本地艺术原画扩散 (ComfyUI / SD / LoRA)] ---
LOCAL_IMAGE_BACKEND = os.getenv("LOCAL_IMAGE_BACKEND", "comfyui").lower().strip()
LOCAL_COMFYUI_URL = os.getenv("LOCAL_COMFYUI_URL", "http://127.0.0.1:8188")
LOCAL_IMAGE_CHECKPOINT = os.getenv("LOCAL_IMAGE_CHECKPOINT", "sd_xl_base_1.0.safetensors")
LOCAL_IMAGE_STEPS = int(os.getenv("LOCAL_IMAGE_STEPS", "20"))
LOCAL_IMAGE_CFG = float(os.getenv("LOCAL_IMAGE_CFG", "7.0"))
LOCAL_IMAGE_SAMPLER = os.getenv("LOCAL_IMAGE_SAMPLER", "euler_ancestral")
LOCAL_IMAGE_SCHEDULER = os.getenv("LOCAL_IMAGE_SCHEDULER", "karras")
LOCAL_COMFYUI_WORKFLOW = os.getenv("LOCAL_COMFYUI_WORKFLOW", "")
LOCAL_IMAGE_TIMEOUT_SECONDS = float(os.getenv("LOCAL_IMAGE_TIMEOUT_SECONDS", "180.0"))




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

# Motion Mode Configuration (TASK-5.0: I2V Hybrid Motion)
DEFAULT_MOTION_MODE = os.getenv("MOTION_MODE", "static")  # static / i2v-tier1 / i2v-all

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
