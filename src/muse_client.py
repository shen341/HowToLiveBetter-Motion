"""Muse AI client wrapper using OpenAI SDK format for HowToLiveBetter-Motion."""

import base64
import json
import math
import os
import re
import time
from typing import Any, Dict, Optional

import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

from src.config import (
    ACTIVE_TEXT_API_KEY,
    ACTIVE_TEXT_BASE_URL,
    ACTIVE_TEXT_MODEL,
    AI_MODE,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    API_TIMEOUT_SECONDS,
    DEFAULT_MOTION_MODE,
    LOCAL_LLM_API_KEY,
    LOCAL_LLM_BASE_URL,
    LOCAL_LLM_MODEL,
    MODEL_IMAGE,
    MODEL_TEXT,
    MODEL_VIDEO,
    MUSE_API_KEY,
    MUSE_BASE_URL,
    RATE_LIMIT_MUSE_RPM,
    YOURSELFAI_API_KEY,
    YOURSELFAI_BASE_URL,
    YOURSELFAI_IMAGE_MODEL,
    YOURSELFAI_MODEL,
)
from src.local_image_client import LocalImageClient
from src.prompt_builder import (
    STYLE_RECIPES,
    build_system_prompt,
    build_user_prompt,
    build_whiteboard_system_prompt,
    build_whiteboard_user_prompt,
    get_style_recipe,
    recommend_style_for_entry,
)
from src.rate_limiter import TokenBucketLimiter, _safe_print, retry_with_backoff

print = _safe_print


def is_whiteboard_scene(scene_index: int, total_scenes: int = 6, motion_mode: str = "static") -> bool:
    """Determine whether a scene qualifies for Whiteboard smooth motion drawing.

    Args:
        scene_index: 1-indexed scene position (e.g. 1 to 6).
        total_scenes: Total number of scenes in the storyboard.
        motion_mode:
            - 'whiteboard': Smooth whiteboard doodle animation
    """
    mode = (motion_mode or "").lower().strip()
    return mode == "whiteboard"


def is_i2v_scene(scene_index: int, total_scenes: int = 6, motion_mode: str = "static") -> bool:
    """Determine whether a scene qualifies for I2V micro-motion generation.

    Args:
        scene_index: 1-indexed scene position (e.g. 1 to 6).
        total_scenes: Total number of scenes in the storyboard.
        motion_mode:
            - 'static': Ken Burns only (no video API calls, default)
            - 'i2v-tier1': Scenes 1 & 5 only (The Hook and Action demonstration)
            - 'i2v-all': All scenes generate I2V video
            - 'whiteboard': Handdrawn smooth animation (never triggers I2V)
    """
    mode = (motion_mode or "").lower().strip()
    if mode in ("static", "none", "off", "ken_burns", "whiteboard", ""):
        return False
    if mode in ("i2v-all", "all", "full"):
        return True
    if mode in ("i2v-tier1", "tier1", "smart"):
        # Tier-1 Focus: Scene 1 (The Hook) & Scene 5 (Action demonstration in 6-scene setup)
        if total_scenes >= 5:
            return scene_index in (1, 5)
        elif total_scenes >= 3:
            return scene_index in (1, total_scenes - 1)
        else:
            return scene_index == 1
    return False


class MuseClient:
    """Client for AI API supporting script, image, and video generation with local/cloud modes, rate limiting, and exponential backoff."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        text_model: Optional[str] = None,
        ai_mode: Optional[str] = None,
        mock: bool = False,
        rate_limit_rpm: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        timeout: Optional[float] = None,
        fallback_api_key: Optional[str] = None,
        fallback_base_url: Optional[str] = None,
        fallback_image_model: Optional[str] = None,
        fallback_text_model: Optional[str] = None,
    ):
        self.ai_mode = (ai_mode or AI_MODE or "cloud").lower().strip()

        # Decide primary text API configuration based on ai_mode
        if self.ai_mode == "local":
            self.api_key = api_key or LOCAL_LLM_API_KEY or "ollama"
            self.base_url = base_url or LOCAL_LLM_BASE_URL or "http://localhost:11434/v1"
            self.text_model = text_model or LOCAL_LLM_MODEL or "qwen2.5vl:7b"
        elif self.ai_mode == "hybrid":
            self.api_key = api_key or YOURSELFAI_API_KEY or os.getenv("YOURSELFAI_API_KEY", "")
            self.base_url = base_url or YOURSELFAI_BASE_URL or os.getenv("YOURSELFAI_BASE_URL", "https://yourselfai.org/v1")
            self.text_model = text_model or YOURSELFAI_MODEL or "gemini-3.8-flash-high"
        else:
            self.api_key = api_key or MUSE_API_KEY or os.getenv("MUSE_API_KEY", "")
            self.base_url = base_url or MUSE_BASE_URL or os.getenv("MUSE_BASE_URL", "https://yourselfai.org/muse/v1")
            self.text_model = text_model or MODEL_TEXT or "muse-spark"


        self.mock = mock or not bool(self.api_key)
        self.rate_limit_rpm = rate_limit_rpm if rate_limit_rpm is not None else RATE_LIMIT_MUSE_RPM
        self.max_retries = max_retries if max_retries is not None else API_MAX_RETRIES
        self.retry_delay = retry_delay if retry_delay is not None else API_RETRY_DELAY
        self.timeout = timeout if timeout is not None else API_TIMEOUT_SECONDS

        # Fallback OpenAI-compatible API config (YourselfAI)
        self.fallback_api_key = fallback_api_key or YOURSELFAI_API_KEY or os.getenv("YOURSELFAI_API_KEY", "")
        self.fallback_base_url = fallback_base_url or YOURSELFAI_BASE_URL or os.getenv("YOURSELFAI_BASE_URL", "https://yourselfai.org/v1")
        self.fallback_image_model = fallback_image_model or YOURSELFAI_IMAGE_MODEL or os.getenv("YOURSELFAI_IMAGE_MODEL", "gemini-3.1-flash-image")
        self.fallback_text_model = fallback_text_model or YOURSELFAI_MODEL or os.getenv("YOURSELFAI_MODEL", "gemini-3.8-flash-high")

        # Phase 3: Local Image generation client (ComfyUI / LoRA)
        self.local_image_client = LocalImageClient(mock=self.mock)

        self.limiter = TokenBucketLimiter(rate_per_minute=self.rate_limit_rpm)

        if not self.mock:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
        else:
            self.client = None

        if self.fallback_api_key and not self.mock:
            self.fallback_client = OpenAI(
                api_key=self.fallback_api_key,
                base_url=self.fallback_base_url,
                timeout=self.timeout
            )
        else:
            self.fallback_client = None

    def generate_script(
        self,
        entry: Dict[str, Any],
        style_mode: str = "auto",
        scene_count: int = 6,
        motion_mode: str = "static"
    ) -> Dict[str, Any]:
        """Generate a structured storyboard JSON using local Ollama or muse-spark (with fallback to YourselfAI / rule-based).
        
        Args:
            entry: Entry data dictionary.
            style_mode: 'auto' (AI decides), 'chapter' (by chapter), or specific style ID.
            scene_count: Target number of storyboard scenes (default: 6 for Golden 6 Scenes).
            motion_mode: Motion mode ('static', 'i2v-tier1', 'i2v-all', 'whiteboard').
        """
        if motion_mode == "whiteboard" and style_mode == "auto":
            style_mode = "w1_whiteboard"

        if self.mock:
            return self._mock_script_generation(entry, style_mode=style_mode, scene_count=scene_count, motion_mode=motion_mode)

        if motion_mode == "whiteboard" or style_mode == "w1_whiteboard":
            system_prompt = build_whiteboard_system_prompt(scene_count=scene_count)
            user_prompt = build_whiteboard_user_prompt(entry, scene_count=scene_count)
        else:
            system_prompt = build_system_prompt(scene_count=scene_count)
            user_prompt = build_user_prompt(entry, style_mode=style_mode, scene_count=scene_count)

        # 1. 主路线: Local-Ollama (本地私有化), YourselfAI-Gemini (混合模式), 或 Muse-Spark (云端)
        if self.ai_mode == "local":
            service_label = f"Local-Ollama ({self.text_model})"
        elif self.ai_mode == "hybrid":
            service_label = f"YourselfAI-Gemini ({self.text_model})"
        else:
            service_label = f"Muse-Spark ({self.text_model})"


        def _do_generate_script():
            stream_resp = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                stream=True
            )
            chunks = []
            for chunk in stream_resp:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    chunks.append(chunk.choices[0].delta.content)
            return "".join(chunks)

        try:
            raw_content = retry_with_backoff(
                _do_generate_script,
                max_retries=min(self.max_retries, 2),
                initial_delay=self.retry_delay,
                service_name=service_label,
                limiter=self.limiter if self.ai_mode != "local" else None,
            )
            return self._clean_and_parse_json(
                raw_content, entry, style_mode=style_mode, scene_count=scene_count, motion_mode=motion_mode
            )
        except Exception as e:
            print(f"⚠️ [主线路 {service_label}] 遇到限速/拥堵或调用异常: {e}.")


        # 2. 备选路线: YourselfAI (OpenAI 兼容协议)
        if self.fallback_client:
            print(f"🔄 [容灾切换] 启动备选大模型: {self.fallback_base_url} [模型: {self.fallback_text_model}] 生成结构化分镜脚本...")
            try:
                def _do_fallback_script():
                    stream_resp = self.fallback_client.chat.completions.create(
                        model=self.fallback_text_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.4,
                        stream=True
                    )
                    chunks = []
                    for chunk in stream_resp:
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            chunks.append(chunk.choices[0].delta.content)
                    return "".join(chunks)
                raw_content = retry_with_backoff(
                    _do_fallback_script,
                    max_retries=2,
                    initial_delay=self.retry_delay,
                    service_name="YourselfAI-Text-Fallback",
                    limiter=None,
                )
                print(f"   ✅ [备选线路] 成功通过 {self.fallback_text_model} 生成分镜脚本！")
                return self._clean_and_parse_json(
                    raw_content, entry, style_mode=style_mode, scene_count=scene_count, motion_mode=motion_mode
                )
            except Exception as fb_err:
                print(f"⚠️ [备选线路] 分镜脚本生成亦失败: {fb_err}.")

        # 3. 兜底降级: 规则驱动本地分镜
        print("⚠️ 降级为规则驱动的本地分镜脚本生成 (Mock Fallback)...")
        return self._mock_script_generation(
            entry, style_mode=style_mode, scene_count=scene_count, motion_mode=motion_mode
        )

    def _save_image_from_response(self, response: Any, output_path: str) -> str:
        """Helper to extract b64_json or url from ImagesResponse and write to disk."""
        if not response or not hasattr(response, "data") or not response.data:
            raise ValueError("No data returned in images response.")
        image_data = response.data[0]
        if hasattr(image_data, "b64_json") and image_data.b64_json:
            img_bytes = base64.b64decode(image_data.b64_json)
            with open(output_path, "wb") as f:
                f.write(img_bytes)
        elif hasattr(image_data, "url") and image_data.url:
            resp = requests.get(image_data.url, timeout=45)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
        else:
            raise ValueError("No valid image data (b64_json or url) in response item.")
        return output_path

    def _generate_image_via_chat_completions(self, prompt: str, output_path: str) -> str:
        """Generate image via OpenAI-compatible /v1/chat/completions endpoint (e.g. gemini-3.1-flash-image)."""
        url = f"{self.fallback_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.fallback_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.fallback_image_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=max(self.timeout or 60.0, 90.0))
        if resp.status_code != 200:
            raise RuntimeError(f"Chat completion image generation failed with HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"No choices returned in chat completion response: {data}")

        message = choices[0].get("message", {})

        # 1. 优先从 message.images 中提取图像 (YourselfAI / NewAPI Gemini 生图标准返回格式)
        image_url = None
        images = message.get("images") or []
        if images and isinstance(images, list):
            item = images[0]
            if isinstance(item, dict):
                if "image_url" in item and isinstance(item["image_url"], dict):
                    image_url = item["image_url"].get("url")
                elif "url" in item:
                    image_url = item.get("url")
                elif "b64_json" in item:
                    image_url = item.get("b64_json")
            elif isinstance(item, str):
                image_url = item

        # 2. 次选从 message.content 中解析 Markdown 图片或 Data URL 字符串
        if not image_url and message.get("content"):
            content = str(message["content"]).strip()
            m_md = re.search(r'!\[.*?\]\((.*?)\)', content)
            if m_md:
                image_url = m_md.group(1).strip()
            elif content.startswith("data:image/") or content.startswith("http://") or content.startswith("https://"):
                image_url = content
            else:
                m_b64 = re.search(r'(data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+)', content)
                if m_b64:
                    image_url = m_b64.group(1)

        if not image_url:
            raise ValueError(f"No image data found in chat completion message: {message}")

        # 3. 写入目标路径 (支持 base64 data url 或远程 http 资源)
        if image_url.startswith("data:image/") or ";base64," in image_url:
            if "," in image_url:
                _, b64_str = image_url.split(",", 1)
            else:
                b64_str = image_url
            img_bytes = base64.b64decode(b64_str)
            with open(output_path, "wb") as f:
                f.write(img_bytes)
        elif image_url.startswith("http://") or image_url.startswith("https://"):
            dl_resp = requests.get(image_url, timeout=60)
            dl_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(dl_resp.content)
        else:
            try:
                img_bytes = base64.b64decode(image_url)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
            except Exception:
                raise ValueError(f"Unrecognized image data format: {image_url[:100]}")

        return output_path

    def _generate_image_via_fallback(self, prompt: str, output_path: str) -> str:
        """Generate image using fallback client with model compatibility handling."""
        model_lower = (self.fallback_image_model or "").lower()
        # Gemini 兼容生图模型 (如 gemini-3.1-flash-image) 在 YourselfAI 上是通过 /v1/chat/completions 路由提供
        if "gemini" in model_lower:
            return self._generate_image_via_chat_completions(prompt, output_path)

        try:
            resp = self.fallback_client.images.generate(
                model=self.fallback_image_model,
                prompt=prompt,
                size="1024x1792"
            )
            return self._save_image_from_response(resp, output_path)
        except Exception as err:
            err_str = str(err).lower()
            # 若提示模型不支持 /v1/images/generations，尝试转至 /v1/chat/completions 路由
            if "not supported on /v1/images" in err_str or "chat" in err_str:
                return self._generate_image_via_chat_completions(prompt, output_path)

            if any(k in err_str for k in ("size", "dimension", "not supported", "invalid")):
                try:
                    resp = self.fallback_client.images.generate(
                        model=self.fallback_image_model,
                        prompt=prompt
                    )
                    return self._save_image_from_response(resp, output_path)
                except Exception:
                    try:
                        resp = self.fallback_client.images.generate(
                            model=self.fallback_image_model,
                            prompt=prompt,
                            size="1024x1024"
                        )
                        return self._save_image_from_response(resp, output_path)
                    except Exception:
                        return self._generate_image_via_chat_completions(prompt, output_path)
            raise err

    def generate_image(self, prompt: str, output_path: str, style_id: str = "25_ghibli") -> str:
        """Generate a real 1024x1792 vertical image using muse-image with automatic fallback route.
        
        Fallback policy:
        1. Primary: Muse-Image on muse/v1.
        2. Fallback: OpenAI-compatible API on YourselfAI (gemini-3.1-flash-image) if primary fails/rate-limited.
        3. Degradation: Styled mock placeholder if all API calls fail.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.mock:
            return self._mock_image_generation(prompt, output_path, style_id)

        # 0. 本地化/混合模式: 阶段三 (本地 ComfyUI + 画风 LoRA 艺术原画)
        if self.ai_mode in ("local", "hybrid"):
            if self.local_image_client.is_available():

                print(f"      🎨 [阶段三: 本地艺术原画] 正在通过 ComfyUI (RTX 4070) 绘制 1024x1792 原画 (画风: {style_id})...")
                try:
                    def _do_local_image():
                        return self.local_image_client.generate_image(prompt, output_path, style_id=style_id)
                    retry_with_backoff(
                        _do_local_image,
                        max_retries=1,
                        initial_delay=self.retry_delay,
                        service_name="Local-ComfyUI",
                        limiter=None,
                    )
                    return output_path
                except Exception as e_local:
                    print(f"      ⚠️ [本地 ComfyUI] 生成异常 ({e_local})，自动降级至云端备选生图路线...")
            else:
                print(f"      ℹ️ [本地 ComfyUI] 服务未启动 ({self.local_image_client.base_url})，自动平滑切换至云端备选路线...")

        # 1. 尝试主线路: Muse-Image
        try:
            def _do_primary_image():
                response = self.client.images.generate(
                    model=MODEL_IMAGE,
                    prompt=prompt,
                    size="1024x1792"
                )
                return self._save_image_from_response(response, output_path)


            retry_with_backoff(
                _do_primary_image,
                max_retries=min(self.max_retries, 2),
                initial_delay=self.retry_delay,
                service_name="Muse-Image",
                limiter=self.limiter,
            )
            return output_path
        except Exception as e_primary:
            print(f"      ⚠️ [主线路 Muse-Image] 遇到限速/拥堵或调用异常: {e_primary}")

        # 2. 尝试备选线路: YourselfAI (OpenAI 兼容协议, 模型 gemini-3.1-flash-image)
        if self.fallback_client:
            print(f"      🔄 [容灾切换] 启动备选生图路线: {self.fallback_base_url} [模型: {self.fallback_image_model}]...")
            try:
                def _do_fallback_image():
                    return self._generate_image_via_fallback(prompt, output_path)

                retry_with_backoff(
                    _do_fallback_image,
                    max_retries=2,
                    initial_delay=self.retry_delay,
                    service_name="YourselfAI-Fallback-Image",
                    limiter=None,
                )
                print(f"      ✅ [备选线路] 成功通过 {self.fallback_image_model} 绘制原画就绪！")
                return output_path
            except Exception as e_fallback:
                print(f"      ⚠️ [备选线路 YourselfAI] 亦生成失败: {e_fallback}")
        else:
            if not self.fallback_api_key:
                print(f"      ℹ️ 未检测到 YOURSELFAI_API_KEY 配置，跳过备选路线。可在 .env 中添加 YOURSELFAI_API_KEY 启用备用线路。")

        # 3. 兜底降级方案: 本地风格化占位原画
        print(f"      ⚠️ 主备生图路线均未成功，降级生成风格化占位素材...")
        return self._mock_image_generation(prompt, output_path, style_id)

    def generate_video(
        self,
        prompt: str,
        output_path: str,
        image_path: Optional[str] = None,
        duration_sec: float = 3.0,
    ) -> str:
        """Generate a micro-motion video slice (I2V or synthetic) driven by the initial image frame.

        Args:
            prompt: Video motion prompt describing movement.
            output_path: Destination .mp4 file path.
            image_path: Source keyframe image path used as first frame for I2V.
            duration_sec: Target motion clip duration (default: 3.0 seconds).

        Returns:
            The generated video output path.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.mock:
            return self._mock_video_generation(prompt, output_path, image_path, duration_sec)

        def _do_generate_video():
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload: Dict[str, Any] = {
                "model": MODEL_VIDEO,
                "prompt": prompt,
                "duration": duration_sec,
                "aspect_ratio": "9:16",
            }
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                payload["image"] = f"data:image/png;base64,{img_b64}"
                payload["first_frame_image"] = payload["image"]

            video_url = None
            endpoints = [
                f"{self.base_url.rstrip('/')}/videos/generations",
                f"{self.base_url.rstrip('/')}/videos",
            ]
            last_err = None
            for ep in endpoints:
                try:
                    resp = requests.post(ep, headers=headers, json=payload, timeout=50)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "data" in data and len(data["data"]) > 0:
                            item = data["data"][0]
                            video_url = item.get("url") or item.get("b64_json")
                            break
                        elif "url" in data:
                            video_url = data["url"]
                            break
                    else:
                        last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
                except Exception as ex:
                    last_err = str(ex)

            if video_url:
                if video_url.startswith("http"):
                    r_dl = requests.get(video_url, timeout=60)
                    r_dl.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(r_dl.content)
                else:
                    vid_bytes = base64.b64decode(video_url)
                    with open(output_path, "wb") as f:
                        f.write(vid_bytes)
                return output_path

            raise RuntimeError(f"Video generation endpoint returned no URL (last error: {last_err})")

        try:
            return retry_with_backoff(
                _do_generate_video,
                max_retries=self.max_retries,
                initial_delay=self.retry_delay,
                service_name="Muse-Video",
                limiter=self.limiter,
            )
        except Exception as e:
            print(f"⚠️ Live I2V video generation failed: {e}. Falling back to styled micro-motion synthesis...")
            return self._mock_video_generation(prompt, output_path, image_path, duration_sec)

    def _clean_and_parse_json(
        self,
        raw_content: str,
        entry: Dict[str, Any],
        style_mode: str = "auto",
        scene_count: int = 6,
        motion_mode: str = "static"
    ) -> Dict[str, Any]:
        """Strip markdown fences and parse JSON robustly with multiple fallbacks."""
        clean = raw_content.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()

        obj = None
        # 1. Direct parse attempt
        try:
            obj = json.loads(clean)
        except Exception:
            pass

        # 2. Try decoding from every '{' occurrence
        if not obj:
            decoder = json.JSONDecoder()
            for idx in range(len(clean)):
                if clean[idx] == '{':
                    try:
                        cand, _ = decoder.raw_decode(clean[idx:])
                        if isinstance(cand, dict) and ("scenes" in cand or "entry_id" in cand):
                            obj = cand
                            break
                    except Exception:
                        continue

        if isinstance(obj, dict):
            # Validate and normalize style fields
            style_id = obj.get("art_style_id", "")
            if motion_mode == "whiteboard" or style_mode == "w1_whiteboard":
                style_id = "w1_whiteboard"
            elif not style_id or style_id not in STYLE_RECIPES:
                if style_mode in STYLE_RECIPES:
                    style_id = style_mode
                elif style_mode == "chapter":
                    style_id = recommend_style_for_entry(entry.get("chapter_index", 1))
                else:
                    style_id = recommend_style_for_entry(entry.get("chapter_index", 1))
            recipe = get_style_recipe(style_id)
            obj["art_style_id"] = style_id
            obj["art_style_name"] = recipe["name"]
            if not obj.get("art_style_reason"):
                if style_id == "w1_whiteboard":
                    obj["art_style_reason"] = "通过极简手绘线稿与大面积呼吸留白，将复杂枯燥的生活常识转化为一目了然的思维导图"
                else:
                    obj["art_style_reason"] = "AI 深度理解内容语义与情绪基调自主决策"

            if motion_mode == "whiteboard":
                for s in obj.get("scenes", []):
                    s.setdefault("motion_type_mode", "whiteboard")
                    if "board_spec" not in s:
                        title_text = s.get("kinetic_typography", {}).get("text") or s.get("primary_subject", "关键要点")
                        s["board_spec"] = {
                            "board_title": title_text[:10],
                            "underline_accent": "#E28743",
                            "key_subject": s.get("primary_subject", "核心概念"),
                            "board_keywords": title_text[:10],
                            "whitespace_ratio": "70%",
                            "hand_action": "画笔流畅书写"
                        }
            return obj

        # 3. Fallback
        print("⚠️ Could not parse JSON from model output, using structured fallback.")
        return self._mock_script_generation(
            entry, style_mode=style_mode, scene_count=scene_count, motion_mode=motion_mode
        )

    def _mock_script_generation(
        self,
        entry: Dict[str, Any],
        style_mode: str = "auto",
        scene_count: int = 6,
        motion_mode: str = "static"
    ) -> Dict[str, Any]:
        """Generate a realistic fallback storyboard conforming to huashu-art-motion standards."""
        chapter_index = entry.get("chapter_index", 1)
        chapter_title = entry.get("chapter_title", "生活指南")
        item_title = entry.get("title", "健康安全建议")
        entry_id = entry.get("id", "01_001")
        plain_text = entry.get("plain_text", "日常生活的重要建议")
        cost_desc = entry.get("cost_desc", "几乎不花钱")
        benefit_desc = entry.get("benefit_desc", "显著降低风险")
        evidence_grade = entry.get("evidence_grade", "A")

        if motion_mode == "whiteboard" or style_mode == "w1_whiteboard":
            style_id = "w1_whiteboard"
            style_reason = "通过极简手绘线稿与大面积呼吸留白，将复杂枯燥的生活常识转化为一目了然的思维导图"
        elif style_mode in STYLE_RECIPES:
            style_id = style_mode
            style_reason = f"用户手动指定风格【{style_id}】"
        elif style_mode == "chapter":
            style_id = recommend_style_for_entry(chapter_index)
            style_reason = "依据章节类别规则映射"
        else:
            # Autonomous AI heuristic based on chapter & topic
            if chapter_index in (5, 8, 9, 11, 12, 15):
                style_id = "y2_vox"
                style_reason = "AI 识别到条目涉及经济规则、法律红线与防骗，选用 Vox 调查剪报风强化档案警示感"
            elif chapter_index in (3, 4, 6, 23):
                style_id = "y1_kurzgesagt"
                style_reason = "AI 识别到条目涉及精力机制与科学拆解，选用 Kurzgesagt 扁平科普矢量风增强明晰度"
            elif chapter_index in (7, 10, 17, 18, 22, 29):
                style_id = "24_hopper"
                style_reason = "AI 识别到条目涉及现代都市生活与人际压力，选用霍珀现实主义风传达沉思质感"
            else:
                style_id = "25_ghibli"
                style_reason = "AI 识别到条目涉及生命健康与日常守护，选用吉卜力手绘风传递温润治愈感"

        style_info = get_style_recipe(style_id)
        video_title = f"{chapter_title}之{item_title}"

        if scene_count == 6:
            if style_id == "w1_whiteboard":
                scenes = [
                    {
                        "scene_index": 1,
                        "time_range": "0.0-4.5",
                        "duration_sec": 4.5,
                        "narration_segment": f"高性价比人生建议：关于{item_title}，关键在于极简行动。",
                        "primary_subject": f"{item_title}核心行动符号",
                        "visual_action": "现代金属触控笔在纸质白板上流畅勾勒核心图素，笔触连贯清晰",
                        "motion_type_mode": "whiteboard",
                        "board_spec": {
                            "board_title": item_title[:10],
                            "underline_accent": "#E28743",
                            "key_subject": item_title[:10],
                            "board_keywords": "核心要点",
                            "whitespace_ratio": "70%",
                            "hand_action": "画笔流畅勾勒核心图素"
                        },
                        "kinetic_typography": {
                            "text": item_title[:10],
                            "style": "handdrawn_write",
                            "position": "center_high"
                        },
                        "image_prompt": f"zen minimalist whiteboard doodle sketch of {item_title}, clean black pen line art on warm ivory paper #FAF8F5, ample negative space, elegant calm composition, vertical 9:16",
                        "video_motion_prompt": "Stylus pen smoothly sketching lines, precise pen tip reveal, calm hold"
                    },
                    {
                        "scene_index": 2,
                        "time_range": "4.5-9.5",
                        "duration_sec": 5.0,
                        "narration_segment": "日常生活中我们往往忽略了关键动作，让潜在风险悄然累加。",
                        "primary_subject": "日常认知误区与常见盲区对比",
                        "visual_action": "画笔绘制警示对比框，线条一气呵成",
                        "motion_type_mode": "whiteboard",
                        "board_spec": {
                            "board_title": "认知误区",
                            "underline_accent": "#E28743",
                            "key_subject": "盲区对比",
                            "board_keywords": "常见误区",
                            "whitespace_ratio": "68%",
                            "hand_action": "画笔绘制警示框"
                        },
                        "kinetic_typography": {
                            "text": "认知误区",
                            "style": "handdrawn_write",
                            "position": "center"
                        },
                        "image_prompt": f"zen minimalist whiteboard sketch showing cognitive pitfall, simple black line drawing on ivory background, ample negative space, clean typography, 9:16 vertical ratio",
                        "video_motion_prompt": "Stylus pen drawing box and question mark smoothly"
                    },
                    {
                        "scene_index": 3,
                        "time_range": "9.5-14.5",
                        "duration_sec": 5.0,
                        "narration_segment": f"底层逻辑非常清晰：{plain_text[:50]}",
                        "primary_subject": "机制拆解与因果箭头流程",
                        "visual_action": "画笔书写因果递进逻辑链，手绘箭头平滑舒展",
                        "motion_type_mode": "whiteboard",
                        "board_spec": {
                            "board_title": "底层逻辑",
                            "underline_accent": "#7BC8A4",
                            "key_subject": "因果箭头",
                            "board_keywords": "科学机制",
                            "whitespace_ratio": "65%",
                            "hand_action": "画笔书写递进箭头"
                        },
                        "kinetic_typography": {
                            "text": "底层逻辑",
                            "style": "handdrawn_write",
                            "position": "center"
                        },
                        "image_prompt": f"minimalist whiteboard diagram showing cause and effect arrow, black lines on warm ivory paper, clean minimalist doodle, vertical 9:16",
                        "video_motion_prompt": "Stylus pen smoothly tracing flow arrow"
                    },
                    {
                        "scene_index": 4,
                        "time_range": "14.5-20.0",
                        "duration_sec": 5.5,
                        "narration_segment": f"证据等级达到 {evidence_grade} 级硬核标准，权威数据真实可信。",
                        "primary_subject": f"证据等级 {evidence_grade} 级权威手绘徽章",
                        "visual_action": "画笔快速勾勒盾牌徽章与评级大字，金属笔尖微光闪烁",
                        "motion_type_mode": "whiteboard",
                        "board_spec": {
                            "board_title": f"证据 {evidence_grade} 级",
                            "underline_accent": "#7BC8A4",
                            "key_subject": "权威徽章",
                            "board_keywords": f"Grade {evidence_grade}",
                            "whitespace_ratio": "70%",
                            "hand_action": "画笔勾勒盾牌徽章"
                        },
                        "kinetic_typography": {
                            "text": f"证据 {evidence_grade} 级",
                            "style": "handdrawn_write",
                            "position": "center"
                        },
                        "image_prompt": f"minimalist whiteboard doodle badge with letter {evidence_grade}, hand drawn simple shield, clean line art on ivory paper #FAF8F5, vertical 9:16",
                        "video_motion_prompt": "Stylus pen sketching shield outline smoothly"
                    },
                    {
                        "scene_index": 5,
                        "time_range": "20.0-25.0",
                        "duration_sec": 5.0,
                        "narration_segment": f"执行成本：{cost_desc}；而收益却是：{benefit_desc[:40]}。",
                        "primary_subject": "投入与产出天平对比示意",
                        "visual_action": "画笔绘制简洁天平，零成本带来高确定性",
                        "motion_type_mode": "whiteboard",
                        "board_spec": {
                            "board_title": "极低成本",
                            "underline_accent": "#E28743",
                            "key_subject": "天平对比",
                            "board_keywords": "超高性价比",
                            "whitespace_ratio": "68%",
                            "hand_action": "画笔勾勒天平"
                        },
                        "kinetic_typography": {
                            "text": "极低成本",
                            "style": "handdrawn_write",
                            "position": "center"
                        },
                        "image_prompt": f"minimalist handdrawn scale showing low cost and high return, clean doodle sketch on ivory canvas, ample negative space, vertical 9:16",
                        "video_motion_prompt": "Stylus pen drawing scale beam"
                    },
                    {
                        "scene_index": 6,
                        "time_range": "25.0-30.0",
                        "duration_sec": 5.0,
                        "narration_segment": "高性价比人生：用最少的代价换回最大的确定性，行动是唯一解。",
                        "primary_subject": "核心行动金句手绘落款与对勾标记",
                        "visual_action": "画笔打下坚定醒目的对勾标记，随后平滑升空移出画布",
                        "motion_type_mode": "whiteboard",
                        "board_spec": {
                            "board_title": "行动是唯一解",
                            "underline_accent": "#7BC8A4",
                            "key_subject": "确定对勾",
                            "board_keywords": "立即行动",
                            "whitespace_ratio": "72%",
                            "hand_action": "画笔打勾后升空离场"
                        },
                        "kinetic_typography": {
                            "text": "行动是唯一解",
                            "style": "handdrawn_write",
                            "position": "center"
                        },
                        "image_prompt": f"zen minimalist whiteboard layout with big checkmark, clean line art, peaceful ivory negative space, elegant composition, vertical 9:16",
                        "video_motion_prompt": "Stylus pen drawing bold checkmark and flying off canvas"
                    }
                ]
            else:
                scenes = [
                {
                    "scene_index": 1,
                    "time_range": "0.0-4.5",
                    "duration_sec": 4.5,
                    "narration_segment": f"高性价比人生建议：关于{item_title}，很多人都做错了。",
                    "primary_subject": f"{item_title}相关的核心生活物件与手部操作特写",
                    "visual_action": "镜头快速推近，物件特写，展现清晰的物理材质纹理与微动",
                    "kinetic_typography": {
                        "text": item_title[:10],
                        "style": "slam_in",
                        "position": "center_high"
                    },
                    "image_prompt": f"Close-up shot of {item_title}, detailed physical texture and hands, warm natural cinematic lighting, {style_info['keywords']}, 9:16 vertical ratio, masterpiece",
                    "video_motion_prompt": "Camera quick punch-in zoom onto subject, dynamic lighting, organic micro motion"
                },
                {
                    "scene_index": 2,
                    "time_range": "4.5-9.5",
                    "duration_sec": 5.0,
                    "narration_segment": "日常生活中我们往往忽略了关键动作，让潜在风险悄然累加。",
                    "primary_subject": "日常现实生活场景展开与普遍习惯空镜",
                    "visual_action": "镜头横移，清晰展示生活场景全貌与普遍误区细节",
                    "kinetic_typography": {
                        "text": "认知误区",
                        "style": "highlight_box",
                        "position": "center"
                    },
                    "image_prompt": f"Wide living room scene related to {item_title}, everyday lifestyle details, natural soft light, {style_info['keywords']}, 9:16 vertical ratio, clean visual hierarchy",
                    "video_motion_prompt": "Smooth lateral camera tracking pan from left to right, subtle atmospheric drift"
                },
                {
                    "scene_index": 3,
                    "time_range": "9.5-14.5",
                    "duration_sec": 5.0,
                    "narration_segment": plain_text[:35] if plain_text else "科学研究证实，底层机制的改变能产生巨大影响。",
                    "primary_subject": "微观机制图解或生活关键指标对比",
                    "visual_action": "微幅推镜头，清晰展示前后对比或科学事实",
                    "kinetic_typography": {
                        "text": "机理真相",
                        "style": "highlight_box",
                        "position": "center"
                    },
                    "image_prompt": f"Illustrative comparison layout of {item_title}, clean informative visual, {style_info['keywords']}, 9:16 vertical ratio, high visual contrast",
                    "video_motion_prompt": "Steady slow push-in zoom with focus on key elements"
                },
                {
                    "scene_index": 4,
                    "time_range": "14.5-19.5",
                    "duration_sec": 5.0,
                    "narration_segment": f"权威数据证实：这一动作能带来 {benefit_desc[:30]}。",
                    "primary_subject": "权威背书、清晰事实标签与数据可视化",
                    "visual_action": "数据标签清晰浮现，主体稳定沉静，对比鲜明",
                    "kinetic_typography": {
                        "text": f"权威 {evidence_grade} 级证据",
                        "style": "data_badge",
                        "position": "bottom_third"
                    },
                    "image_prompt": f"Authoritative infographic layout with serene aesthetic, {item_title} elements, {style_info['keywords']}, 9:16 vertical ratio, clean planes",
                    "video_motion_prompt": "Steady focused framing with subtle floating particle dust in ambient lighting"
                },
                {
                    "scene_index": 5,
                    "time_range": "19.5-24.5",
                    "duration_sec": 5.0,
                    "narration_segment": f"成本方面：{cost_desc}；用最小的微动作锁死确定性。",
                    "primary_subject": "简易操作动作示范与零成本工具",
                    "visual_action": "手部利落执行动作，体现轻松自如与零门槛",
                    "kinetic_typography": {
                        "text": "零成本行动",
                        "style": "slam_in",
                        "position": "center_high"
                    },
                    "image_prompt": f"Demonstration of simple easy action for {item_title}, gentle sunlight, calm hands, {style_info['keywords']}, 9:16 vertical ratio",
                    "video_motion_prompt": "Gentle lateral tracking pan, soft illumination"
                },
                {
                    "scene_index": 6,
                    "time_range": "24.5-29.5",
                    "duration_sec": 5.0,
                    "narration_segment": "高性价比人生第一原则：用最小代价换取最大确定性，立即行动！",
                    "primary_subject": "明亮开阔的未来生活场景或从容的人物背影",
                    "visual_action": "定镜停留，核心金句稳定落定收尾",
                    "kinetic_typography": {
                        "text": "行动是唯一解",
                        "style": "gold_sentence_lock",
                        "position": "center"
                    },
                    "image_prompt": f"Wide scenic view with peaceful atmosphere, gentle sunlight, looking forward, {style_info['keywords']}, 9:16 vertical ratio, harmonious color balance",
                    "video_motion_prompt": "Static grounded hold with gentle atmospheric breathing"
                }
            ]
        else:
            # 4-scene fallback
            scenes = [
                {
                    "scene_index": 1,
                    "time_range": "0.0-4.0",
                    "duration_sec": 4.0,
                    "narration_segment": f"高性价比人生建议：关于{item_title}，很多人都做错了。",
                    "primary_subject": f"{item_title}相关的核心生活物件与手部操作动作",
                    "visual_action": "镜头快速推近，物件特写，展现清晰的物理材质纹理",
                    "kinetic_typography": {"text": item_title[:10], "style": "slam_in", "position": "center_high"},
                    "image_prompt": f"Close-up shot of {item_title}, detailed physical texture and hands, warm natural cinematic lighting, {style_info['keywords']}, 9:16 vertical ratio, masterpiece",
                    "video_motion_prompt": "Camera quick punch-in zoom onto subject, dynamic lighting, organic micro motion"
                },
                {
                    "scene_index": 2,
                    "time_range": "4.0-12.0",
                    "duration_sec": 8.0,
                    "narration_segment": plain_text[:60] if plain_text else f"权威数据表明，这一条能直接改变生活质量。",
                    "primary_subject": "日常现实生活场景展开与对比",
                    "visual_action": "镜头横移，清晰展示生活场景全貌与关键指标对比",
                    "kinetic_typography": {"text": "说人话·核心对比", "style": "highlight_box", "position": "center"},
                    "image_prompt": f"Everyday living scene related to {item_title}, thoughtful and serene atmosphere, {style_info['keywords']}, 9:16 vertical ratio, clean visual hierarchy",
                    "video_motion_prompt": "Smooth lateral camera tracking pan from left to right, subtle atmospheric drift"
                },
                {
                    "scene_index": 3,
                    "time_range": "12.0-22.0",
                    "duration_sec": 10.0,
                    "narration_segment": f"成本方面：{cost_desc}；而收益却是：{benefit_desc[:50]}。证据等级达到 {evidence_grade} 级硬核标准！",
                    "primary_subject": "权威背书、清晰事实标签与数据可视化",
                    "visual_action": "数据标签清晰浮现，主体稳定沉静，对比鲜明",
                    "kinetic_typography": {"text": f"证据等级 {evidence_grade} 级", "style": "data_badge", "position": "bottom_third"},
                    "image_prompt": f"Authoritative infographic layout with serene aesthetic, {item_title} elements, {style_info['keywords']}, 9:16 vertical ratio, high visual contrast",
                    "video_motion_prompt": "Steady focused framing with subtle floating particle dust in ambient lighting"
                },
                {
                    "scene_index": 4,
                    "time_range": "22.0-28.0",
                    "duration_sec": 6.0,
                    "narration_segment": f"高性价比人生：用最少的代价换回最大的确定性，行动起来！",
                    "primary_subject": "明亮开阔的未来生活场景或平静从容的人物背影",
                    "visual_action": "定镜停留，核心金句稳定落定收尾",
                    "kinetic_typography": {"text": "行动是唯一解", "style": "gold_sentence_lock", "position": "center"},
                    "image_prompt": f"Wide scenic view with peaceful atmosphere, gentle sunlight, looking forward, {style_info['keywords']}, 9:16 vertical ratio, harmonious color balance",
                    "video_motion_prompt": "Static grounded hold with gentle atmospheric breathing"
                }
            ]

        return {
            "entry_id": entry_id,
            "video_title": video_title,
            "target_duration_sec": 29,
            "art_style_id": style_id,
            "art_style_name": style_info["name"],
            "art_style_reason": style_reason,
            "color_palette": ["#1A365D", "#E2E8F0", "#319795", "#ED8936"],
            "narration_text_full": f"高性价比人生建议：{item_title}。{plain_text}。{cost_desc}，换来{benefit_desc}。证据等级 {evidence_grade} 级，转给在乎的人！",
            "scenes": scenes
        }


    def _mock_image_generation(self, prompt: str, output_path: str, style_id: str) -> str:
        """Create a clean gradient background without debug labels."""
        width, height = 1080, 1920
        # Warm aesthetic gradient
        img = Image.new("RGB", (width, height), (245, 238, 225))
        draw = ImageDraw.Draw(img)

        # Soft subtle warm sunrays / watercolor circles
        for r in range(400, 50, -50):
            alpha_color = (250, 220 - r // 5, 180 - r // 4)
            draw.ellipse([width // 2 - r, height // 3 - r, width // 2 + r, height // 3 + r], fill=alpha_color)

        img.save(output_path, quality=95)
        return output_path

    def _mock_video_generation(
        self,
        prompt: str,
        output_path: str,
        image_path: Optional[str] = None,
        duration_sec: float = 3.0
    ) -> str:
        """Synthesize a smooth micro-motion MP4 from the initial image frame."""
        import numpy as np
        from moviepy import VideoClip

        width, height = 1080, 1920
        if image_path and os.path.exists(image_path):
            try:
                base_img = Image.open(image_path).convert("RGB")
                if base_img.size != (width, height):
                    base_img = base_img.resize((width, height), Image.Resampling.BILINEAR)
            except Exception:
                base_img = Image.new("RGB", (width, height), (30, 42, 56))
        else:
            base_img = Image.new("RGB", (width, height), (30, 42, 56))

        # Margin expansion for organic physical push-in
        margin = 1.05
        bw = int(width * margin)
        bh = int(height * margin)
        expanded = base_img.resize((bw, bh), Image.Resampling.BILINEAR)

        # Micro motion frame generator (24 fps, subtle 3% zoom + gentle breathing)
        def make_frame(t):
            p = min(max(t / max(duration_sec, 0.1), 0.0), 1.0)
            smooth_p = 0.5 * (1.0 - math.cos(math.pi * p))
            scale = 1.0 + 0.03 * smooth_p
            cw = int(width * margin / scale)
            ch = int(height * margin / scale)
            left = (bw - cw) // 2
            top = (bh - ch) // 2
            cropped = expanded.crop((left, top, left + cw, top + ch))
            if cropped.size != (width, height):
                cropped = cropped.resize((width, height), Image.Resampling.BILINEAR)
            return np.array(cropped)

        clip = VideoClip(make_frame, duration=duration_sec)
        clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            preset="ultrafast",
            pixel_format="yuv420p",
            logger=None
        )
        clip.close()
        return output_path

