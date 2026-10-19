"""Local image generation client integrating ComfyUI API with style LoRAs for HowToLiveBetter-Motion (Phase 3 / ADR-015)."""

import json
import os
import random
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import requests

from src.config import (
    LOCAL_COMFYUI_URL,
    LOCAL_COMFYUI_WORKFLOW,
    LOCAL_IMAGE_CFG,
    LOCAL_IMAGE_CHECKPOINT,
    LOCAL_IMAGE_SAMPLER,
    LOCAL_IMAGE_SCHEDULER,
    LOCAL_IMAGE_STEPS,
    LOCAL_IMAGE_TIMEOUT_SECONDS,
)
from src.prompt_builder import get_style_recipe

# LoRA and prompt trigger configurations for the 7 hallmark art style cards
STYLE_LORA_PRESETS: Dict[str, Dict[str, Any]] = {
    "25_ghibli": {
        "lora_name": "ghibli_style_offset.safetensors",
        "strength": 0.85,
        "trigger": "Studio Ghibli aesthetic, Hayao Miyazaki anime style, warm gouache texture",
        "default_negative": "blurry, low quality, 3d cgi render, photorealistic, watermark, text"
    },
    "y1_kurzgesagt": {
        "lora_name": "kurzgesagt_vector.safetensors",
        "strength": 0.85,
        "trigger": "Kurzgesagt flat vector art, clean sharp geometric silhouettes, immaculate lighting",
        "default_negative": "photorealistic, noisy gradients, 3d render, blurry, watermark"
    },
    "13_pop": {
        "lora_name": "roy_lichtenstein_pop.safetensors",
        "strength": 0.85,
        "trigger": "Roy Lichtenstein pop art, Ben-Day dots matrix, bold black outlines, vintage comic book",
        "default_negative": "soft watercolor, photorealistic, gloomy dark, 3d cgi, blurry, watermark"
    },
    "24_hopper": {
        "lora_name": "edward_hopper_realism.safetensors",
        "strength": 0.80,
        "trigger": "Edward Hopper American realism, dramatic geometric sunlight shadows, cinematic framing",
        "default_negative": "anime, cute cartoon, cyberpunk neon, hyper-saturated fantasy, watermark"
    },
    "17_ink": {
        "lora_name": "traditional_chinese_ink.safetensors",
        "strength": 0.85,
        "trigger": "modern Chinese ink wash painting, delicate sumi-e brush strokes, mineral color accents, poetic mist",
        "default_negative": "loud neon, western comic, sharp geometric, cluttered, noisy 3d, watermark"
    },
    "14_pixel": {
        "lora_name": "16bit_pixel_art.safetensors",
        "strength": 0.90,
        "trigger": "detailed 16-bit pixel art style, nostalgic retro game aesthetic, clean isometric composition",
        "default_negative": "blurry, smooth photorealistic, soft watercolor, dark gloomy, watermark"
    },
    "w1_whiteboard": {
        "lora_name": "whiteboard_minimalist_doodle.safetensors",
        "strength": 0.85,
        "trigger": "zen minimalist whiteboard doodle art, clean ivory paper texture, ample negative space, isolated single iconic subject, crisp black outline sketch, subtle pastel color accents",
        "default_negative": "crowded, cluttered composition, photorealistic, complex shading, dark gloomy background, neon glow, 3d glossy, watermark, text"
    }
}



class LocalImageClient:
    """Client for generating vertical 1024x1792 scene images via local ComfyUI API with LoRA style control."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        checkpoint: Optional[str] = None,
        steps: Optional[int] = None,
        cfg: Optional[float] = None,
        sampler_name: Optional[str] = None,
        scheduler: Optional[str] = None,
        timeout: Optional[float] = None,
        workflow_path: Optional[str] = None,
        mock: bool = False,
    ):
        self.base_url = (base_url or LOCAL_COMFYUI_URL or "http://127.0.0.1:8188").rstrip("/")
        self.checkpoint = checkpoint or LOCAL_IMAGE_CHECKPOINT or "sd_xl_base_1.0.safetensors"
        self.steps = steps if steps is not None else LOCAL_IMAGE_STEPS
        self.cfg = cfg if cfg is not None else LOCAL_IMAGE_CFG
        self.sampler_name = sampler_name or LOCAL_IMAGE_SAMPLER or "euler_ancestral"
        self.scheduler = scheduler or LOCAL_IMAGE_SCHEDULER or "karras"
        self.timeout = timeout if timeout is not None else LOCAL_IMAGE_TIMEOUT_SECONDS
        self.workflow_path = workflow_path or LOCAL_COMFYUI_WORKFLOW
        self.mock = mock

    def is_available(self) -> bool:
        """Check if local ComfyUI server is online and responding."""
        if self.mock:
            return True
        try:
            resp = requests.get(f"{self.base_url}/system_stats", timeout=2.5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_style_lora_preset(self, style_id: str) -> Dict[str, Any]:
        """Retrieve LoRA and trigger settings for a given style ID."""
        return STYLE_LORA_PRESETS.get(style_id, STYLE_LORA_PRESETS["25_ghibli"])

    def get_installed_checkpoints(self) -> list:
        """Query ComfyUI for currently installed checkpoint models."""
        if self.mock:
            return [self.checkpoint]
        try:
            r = requests.get(f"{self.base_url}/object_info/CheckpointLoaderSimple", timeout=2.0)
            if r.status_code == 200:
                return r.json().get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        except Exception:
            pass
        return []

    def get_installed_loras(self) -> list:
        """Query ComfyUI for currently installed LoRA files."""
        if self.mock:
            return [cfg.get("lora_name") for cfg in STYLE_LORA_PRESETS.values() if cfg.get("lora_name")]
        try:
            r = requests.get(f"{self.base_url}/object_info/LoraLoader", timeout=2.0)
            if r.status_code == 200:
                return r.json().get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])[0]
        except Exception:
            pass
        return []

    def build_prompt_workflow(
        self,
        prompt: str,
        style_id: str = "25_ghibli",
        width: int = 1024,
        height: int = 1792,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Construct a ComfyUI prompt workflow DAG with Checkpoint, optional LoRA, KSampler, and SaveImage."""
        recipe = get_style_recipe(style_id)
        lora_cfg = self.get_style_lora_preset(style_id)

        # Merge recipe keywords and LoRA triggers into positive and negative prompts
        style_trigger = lora_cfg.get("trigger", "")
        recipe_keywords = recipe.get("keywords", "")
        full_positive = f"{prompt}, {style_trigger}, {recipe_keywords}"

        recipe_negative = recipe.get("negative", "")
        default_negative = lora_cfg.get("default_negative", "")
        full_negative = f"{recipe_negative}, {default_negative}".strip(", ")

        chosen_seed = seed if seed is not None else random.randint(1000000000, 9999999999)

        # Determine active checkpoint model
        installed_ckpts = self.get_installed_checkpoints()
        if self.checkpoint in installed_ckpts:
            active_ckpt = self.checkpoint
        elif installed_ckpts:
            active_ckpt = installed_ckpts[0]
        else:
            active_ckpt = self.checkpoint

        # Standard SDXL / SD 1.5 ComfyUI API prompt structure
        workflow: Dict[str, Any] = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": self.cfg,
                    "denoise": 1.0,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": self.sampler_name,
                    "scheduler": self.scheduler,
                    "seed": chosen_seed,
                    "steps": self.steps
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": active_ckpt
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": full_positive
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": full_negative
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": f"HowToLiveBetter_{style_id}",
                    "images": ["8", 0]
                }
            }
        }

        # Check if the requested style LoRA is installed; attach LoraLoader only if present
        lora_name = lora_cfg.get("lora_name")
        lora_strength = float(lora_cfg.get("strength", 0.8))
        installed_loras = self.get_installed_loras()

        if lora_name and (self.mock or lora_name in installed_loras):
            workflow["10"] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": lora_name,
                    "model": ["4", 0],
                    "clip": ["4", 1],
                    "strength_model": lora_strength,
                    "strength_clip": lora_strength
                }
            }
            # Rewire sampler and CLIP encoders through the LoRA node
            workflow["3"]["inputs"]["model"] = ["10", 0]
            workflow["6"]["inputs"]["clip"] = ["10", 1]
            workflow["7"]["inputs"]["clip"] = ["10", 1]

        return workflow


    def generate_image(
        self,
        prompt: str,
        output_path: str,
        style_id: str = "25_ghibli",
        width: int = 1024,
        height: int = 1792,
        seed: Optional[int] = None,
    ) -> str:
        """Generate vertical art image via local ComfyUI API with polling and save to output_path."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.mock:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (width, height), color=(30, 45, 60))
            draw = ImageDraw.Draw(img)
            draw.text((width // 4, height // 2), f"Mock Local Image: {style_id}", fill=(240, 240, 240))
            img.save(output_path)
            return output_path

        # 校验 ComfyUI 是否已下载底模
        ckpts = self.get_installed_checkpoints()
        if not ckpts:
            raise FileNotFoundError(
                "ComfyUI 中尚未检测到任何可用大模型底模 (.safetensors)！\n"
                "请先下载 SDXL 底模 (例如 sd_xl_base_1.0.safetensors) 放置于:\n"
                "  -> C:\\stabilityMatrix\\Models\\StableDiffusion\\"
            )


        client_id = str(uuid.uuid4())
        workflow = self.build_prompt_workflow(
            prompt=prompt,
            style_id=style_id,
            width=width,
            height=height,
            seed=seed
        )

        # 1. Queue Prompt in ComfyUI
        post_url = f"{self.base_url}/prompt"
        payload = {"prompt": workflow, "client_id": client_id}
        resp = requests.post(post_url, json=payload, timeout=30.0)
        if resp.status_code != 200:
            raise RuntimeError(f"ComfyUI prompt submission failed (HTTP {resp.status_code}): {resp.text[:200]}")

        prompt_data = resp.json()
        prompt_id = prompt_data.get("prompt_id")
        if not prompt_id:
            raise ValueError(f"No prompt_id returned by ComfyUI: {prompt_data}")

        # 2. Poll /history/{prompt_id} until completion
        start_time = time.time()
        poll_interval = 1.5
        image_meta = None

        while time.time() - start_time < self.timeout:
            history_url = f"{self.base_url}/history/{prompt_id}"
            hist_resp = requests.get(history_url, timeout=10.0)
            if hist_resp.status_code == 200:
                history_json = hist_resp.json()
                if prompt_id in history_json:
                    task_data = history_json[prompt_id]
                    outputs = task_data.get("outputs", {})
                    # Find SaveImage output
                    for node_id, node_out in outputs.items():
                        images = node_out.get("images", [])
                        if images:
                            image_meta = images[0]
                            break
                    if image_meta:
                        break
            time.sleep(poll_interval)

        if not image_meta:
            raise TimeoutError(f"ComfyUI image generation timed out after {self.timeout}s (Prompt ID: {prompt_id})")

        # 3. Download the generated image from /view
        filename = image_meta.get("filename")
        subfolder = image_meta.get("subfolder", "")
        img_type = image_meta.get("type", "output")

        view_url = f"{self.base_url}/view"
        params = {"filename": filename, "subfolder": subfolder, "type": img_type}
        view_resp = requests.get(view_url, params=params, timeout=45.0)
        view_resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(view_resp.content)

        return output_path
