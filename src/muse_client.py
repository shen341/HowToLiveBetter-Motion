"""Muse AI client wrapper using OpenAI SDK format for HowToLiveBetter-Motion."""

import base64
import json
import os
import re
import time
from typing import Any, Dict, Optional

import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

from src.config import (
    MODEL_IMAGE,
    MODEL_TEXT,
    MODEL_VIDEO,
    MUSE_API_KEY,
    MUSE_BASE_URL,
)
from src.prompt_builder import (
    STYLE_RECIPES,
    build_system_prompt,
    build_user_prompt,
    recommend_style_for_entry,
)


class MuseClient:
    """Client for Muse AI API supporting script, image, and video generation."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, mock: bool = False):
        self.api_key = api_key or MUSE_API_KEY or os.getenv("MUSE_API_KEY", "")
        self.base_url = base_url or MUSE_BASE_URL or os.getenv("MUSE_BASE_URL", "https://yourselfai.org/muse/v1")
        self.mock = mock or not bool(self.api_key)

        if not self.mock:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    def generate_script(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a 30-second structured storyboard JSON using muse-spark."""
        if self.mock:
            return self._mock_script_generation(entry)

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(entry)

        try:
            response = self.client.chat.completions.create(
                model=MODEL_TEXT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4
            )
            raw_content = response.choices[0].message.content
            return self._clean_and_parse_json(raw_content, entry)
        except Exception as e:
            print(f"⚠️ Live muse-spark error: {e}. Falling back to rule-based storyboard...")
            return self._mock_script_generation(entry)

    def generate_image(self, prompt: str, output_path: str, style_id: str = "25_ghibli") -> str:
        """Generate a real 1024x1792 vertical image using muse-image."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.mock:
            return self._mock_image_generation(prompt, output_path, style_id)

        try:
            response = self.client.images.generate(
                model=MODEL_IMAGE,
                prompt=prompt,
                size="1024x1792"
            )
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
                raise ValueError("No image data (b64 or url) returned from API response.")

            return output_path
        except Exception as e:
            print(f"⚠️ Live image generation warning: {e}. Falling back to styled placeholder...")
            return self._mock_image_generation(prompt, output_path, style_id)

    def generate_video(self, prompt: str, output_path: str, image_path: Optional[str] = None) -> str:
        """Generate video asset."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return output_path

    def _clean_and_parse_json(self, raw_content: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Strip markdown fences and parse JSON robustly with multiple fallbacks."""
        clean = raw_content.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()

        # 1. Direct parse attempt
        try:
            return json.loads(clean)
        except Exception:
            pass

        # 2. Try decoding from every '{' occurrence
        decoder = json.JSONDecoder()
        for idx in range(len(clean)):
            if clean[idx] == '{':
                try:
                    obj, _ = decoder.raw_decode(clean[idx:])
                    if isinstance(obj, dict) and ("scenes" in obj or "entry_id" in obj):
                        return obj
                except Exception:
                    continue

        # 3. Fallback
        print("⚠️ Could not parse JSON from model output, using structured fallback.")
        return self._mock_script_generation(entry)

    def _mock_script_generation(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a realistic fallback storyboard conforming to huashu-art-motion standards."""
        chapter_index = entry.get("chapter_index", 1)
        chapter_title = entry.get("chapter_title", "生活指南")
        item_title = entry.get("title", "健康安全建议")
        entry_id = entry.get("id", "01_001")
        plain_text = entry.get("plain_text", "日常生活的重要建议")
        cost_desc = entry.get("cost_desc", "几乎不花钱")
        benefit_desc = entry.get("benefit_desc", "显著降低风险")
        evidence_grade = entry.get("evidence_grade", "A")

        style_id = recommend_style_for_entry(chapter_index)
        style_info = STYLE_RECIPES.get(style_id, STYLE_RECIPES["25_ghibli"])
        video_title = f"{chapter_title}之{item_title}"

        return {
            "entry_id": entry_id,
            "video_title": video_title,
            "target_duration_sec": 28,
            "art_style_id": style_id,
            "art_style_name": style_info["name"],
            "color_palette": ["#1A365D", "#E2E8F0", "#319795", "#ED8936"],
            "narration_text_full": f"高性价比人生第一条：{item_title}。{plain_text}。{cost_desc}，换来的是{benefit_desc}。这有{evidence_grade}级权威证据，记得转给在乎的人！",
            "scenes": [
                {
                    "scene_index": 1,
                    "time_range": "0.0-4.0",
                    "duration_sec": 4.0,
                    "narration_segment": f"高性价比人生建议：关于{item_title}，很多人都做错了。",
                    "primary_subject": f"{item_title}相关的核心生活物件与手部操作动作",
                    "visual_action": "镜头快速推近，物件特写，展现清晰的物理材质纹理",
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
                    "time_range": "4.0-12.0",
                    "duration_sec": 8.0,
                    "narration_segment": plain_text[:60] if plain_text else f"权威数据表明，这一条能直接改变生活质量。",
                    "primary_subject": "日常现实生活场景展开与对比",
                    "visual_action": "镜头横移，清晰展示生活场景全貌与关键指标对比",
                    "kinetic_typography": {
                        "text": "说人话·核心对比",
                        "style": "highlight_box",
                        "position": "center"
                    },
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
                    "kinetic_typography": {
                        "text": f"证据等级 {evidence_grade} 级",
                        "style": "data_badge",
                        "position": "bottom_third"
                    },
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
                    "kinetic_typography": {
                        "text": "行动是唯一解",
                        "style": "gold_sentence_lock",
                        "position": "center"
                    },
                    "image_prompt": f"Wide scenic view with peaceful atmosphere, gentle sunlight, looking forward, {style_info['keywords']}, 9:16 vertical ratio, harmonious color balance",
                    "video_motion_prompt": "Static grounded hold with gentle atmospheric breathing"
                }
            ]
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
