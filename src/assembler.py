"""Video assembly and subtitle overlay engine for HowToLiveBetter-Motion.
Features:
- Ken Burns dynamic camera motions (smooth zoom-in, zoom-out, lateral panning)
- Seamless 0.5s cross-dissolve transitions between scenes
- Golden ratio aesthetic layout:
    * Upper golden ratio (Y ~ 733px): Kinetic typography highlight badge
    * Lower golden ratio (Y ~ 1186px): Frosted glass narration subtitle capsule (avoids mobile UI clutter)
- TTS Voiceover integration (zh-CN-YunzeNeural) with precise audio-visual synchronization
- Background music mixing from backgroup_music/ folder with soft volume (-20dB) and smooth fades
- Pillow anti-aliased high-DPI text rendering (zero ImageMagick dependencies)
"""

import math
import os
import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
)
import moviepy.audio.fx as afx
import moviepy.video.fx as vfx

from src.config import (
    ASSETS_BGM_DIR,
    ASSETS_FONTS_DIR,
    BACKGROUP_MUSIC_DIR,
    DEFAULT_PLATFORM_PRESET,
    OUTPUT_FINAL_VIDEOS_DIR,
)


PLATFORM_PRESETS: Dict[str, Dict[str, Any]] = {
    "default": {
        "name": "通用平衡推荐 (Default)",
        "crf": 21,
        "preset": "medium",
        "audio_bitrate": "128k",
        "maxrate": "5000k",
        "bufsize": "10000k",
        "description": "画质与体积兼顾，适配绝大多数移动端播放器与社交平台 (约 12~16MB/30s)",
    },
    "xhs": {
        "name": "小红书专属抗二压预设 (Xiaohongshu)",
        "crf": 21,
        "preset": "medium",
        "audio_bitrate": "128k",
        "maxrate": "4500k",
        "bufsize": "9000k",
        "description": "严格控制在 15MB 黄金安全线内，避免触发小红书服务端劣化二次转码",
    },
    "douyin": {
        "name": "抖音/TikTok高画质预设 (Douyin/TikTok)",
        "crf": 20,
        "preset": "medium",
        "audio_bitrate": "192k",
        "maxrate": "6000k",
        "bufsize": "12000k",
        "description": "更高码率上限与音频保真度，适配抖音大屏推荐流与高对比度动态帧 (约 16~22MB/30s)",
    },
    "wechat": {
        "name": "微信视频号秒开预设 (WeChat Channels)",
        "crf": 22,
        "preset": "medium",
        "audio_bitrate": "128k",
        "maxrate": "4000k",
        "bufsize": "8000k",
        "description": "高压缩比与低缓冲延迟，适配微信会话与朋友圈内毫秒级流式秒开 (约 10~14MB/30s)",
    },
    "bilibili": {
        "name": "B站竖屏高清归档预设 (Bilibili/Archival)",
        "crf": 19,
        "preset": "slow",
        "audio_bitrate": "192k",
        "maxrate": "8000k",
        "bufsize": "16000k",
        "description": "母带级高保真度，适合长期高清归档与高配额视频平台 (约 20~28MB/30s)",
    },
}


def get_platform_preset(name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve platform encoding preset configuration, fallback to 'default'."""
    key = (name or DEFAULT_PLATFORM_PRESET).lower().strip()
    return PLATFORM_PRESETS.get(key, PLATFORM_PRESETS["default"])


def list_platform_presets() -> Dict[str, Dict[str, Any]]:
    """Return all available platform presets."""
    return PLATFORM_PRESETS


def find_system_font(bold: bool = False) -> str:
    """Find a readable Chinese font on Windows or local assets directory."""
    if os.path.exists(ASSETS_FONTS_DIR):
        for f in os.listdir(ASSETS_FONTS_DIR):
            if f.endswith((".ttf", ".otf", ".ttc")):
                return os.path.join(ASSETS_FONTS_DIR, f)

    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "arial.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "arial.ttf"


class VideoAssembler:
    """Engine for assembling images, dynamic motions, transitions, subtitles, and BGM into MP4."""

    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        font_path: Optional[str] = None,
        default_preset: str = DEFAULT_PLATFORM_PRESET,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.font_path = font_path or find_system_font(bold=False)
        self.font_bold_path = find_system_font(bold=True)
        self.default_preset = default_preset

        # Golden ratio Y coordinates on a 1920px canvas
        self.Y_UPPER_GOLDEN = int(self.height * 0.382)  # ~733px (Upper focal area)
        self.Y_LOWER_GOLDEN = int(self.height * 0.618)  # ~1186px (Lower reading area)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        fp = self.font_bold_path if bold else self.font_path
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            return ImageFont.load_default()

    def create_header_badge(self, chapter_title: str, evidence_grade: str) -> np.ndarray:
        """Create a stylish top header capsule badge."""
        img = Image.new("RGBA", (self.width, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        text = f"高性价比人生指南 · 《{chapter_title}》"
        grade_text = f"证据 {evidence_grade} 级" if evidence_grade else "循证精选"

        font = self._get_font(28, bold=True)
        grade_font = self._get_font(24, bold=True)

        pill_w, pill_h = 760, 68
        pill_x = (self.width - pill_w) // 2
        pill_y = 50

        # Subtle dark capsule with amber accent
        draw.rounded_rectangle(
            [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
            radius=34,
            fill=(18, 24, 38, 220),
            outline=(245, 166, 35, 220),
            width=2
        )

        draw.text((pill_x + 36, pill_y + 17), text, fill=(255, 255, 255, 255), font=font)

        # Evidence grade pill tag
        grade_w, grade_h = 160, 46
        gx = pill_x + pill_w - grade_w - 12
        gy = pill_y + 11
        draw.rounded_rectangle(
            [gx, gy, gx + grade_w, gy + grade_h],
            radius=23,
            fill=(245, 166, 35, 245)
        )
        draw.text((gx + 20, gy + 8), grade_text, fill=(20, 25, 35, 255), font=grade_font)

        return np.array(img)

    def create_kinetic_card(self, text: str) -> np.ndarray:
        """
        Create dynamic typography card at upper golden ratio point (Y ~ 733px).
        Reflects '字就是演员' (words as actors) design principle from huashu-art-motion.
        """
        card_h = 220
        img = Image.new("RGBA", (self.width, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if not text:
            return np.array(img)

        font = self._get_font(52, bold=True)

        try:
            bbox = font.getbbox(text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            text_w = len(text) * 52
            text_h = 52

        pad_x, pad_y = 50, 20
        box_w = min(self.width - 120, text_w + pad_x * 2)
        box_h = text_h + pad_y * 2
        bx = (self.width - box_w) // 2
        by = (card_h - box_h) // 2

        # Soft drop shadow
        draw.rounded_rectangle(
            [bx + 4, by + 8, bx + box_w + 4, by + box_h + 8],
            radius=26,
            fill=(0, 0, 0, 160)
        )
        # Amber/Golden badge with white stroke
        draw.rounded_rectangle(
            [bx, by, bx + box_w, by + box_h],
            radius=26,
            fill=(245, 166, 35, 245),
            outline=(255, 255, 255, 240),
            width=3
        )
        # Inner punchy text
        draw.text(
            (self.width // 2, by + pad_y + text_h // 2),
            text,
            fill=(20, 24, 34, 255),
            font=font,
            anchor="mm"
        )

        return np.array(img)

    def create_subtitle_strip(self, text: str) -> np.ndarray:
        """
        Create frosted glass narration subtitle capsule at lower golden ratio point (Y ~ 1186px).
        Avoids bottom app navigation bars (comments, likes, progress bar).
        """
        strip_h = 240
        img = Image.new("RGBA", (self.width, strip_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if not text:
            return np.array(img)

        font = self._get_font(38, bold=True)
        max_chars_per_line = 20
        lines = []

        for i in range(0, len(text), max_chars_per_line):
            lines.append(text[i:i + max_chars_per_line])

        line_h = 52
        total_h = len(lines) * line_h + 34
        box_w = self.width - 120
        bx = 60
        by = (strip_h - total_h) // 2

        # Soft outer shadow
        draw.rounded_rectangle(
            [bx + 4, by + 6, bx + box_w + 4, by + total_h + 6],
            radius=26,
            fill=(0, 0, 0, 140)
        )

        # Elegant Frosted Dark Glass capsule (Semi-transparent navy blue with subtle golden/white border)
        draw.rounded_rectangle(
            [bx, by, bx + box_w, by + total_h],
            radius=26,
            fill=(16, 22, 34, 205),
            outline=(245, 166, 35, 180),
            width=2
        )

        start_y = by + 18
        for idx, line in enumerate(lines):
            # Text shadow for maximum clarity
            draw.text(
                (self.width // 2 + 1, start_y + idx * line_h + line_h // 2 + 1),
                line,
                fill=(0, 0, 0, 180),
                font=font,
                anchor="mm"
            )
            # Pure white foreground text
            draw.text(
                (self.width // 2, start_y + idx * line_h + line_h // 2),
                line,
                fill=(255, 255, 255, 255),
                font=font,
                anchor="mm"
            )

        return np.array(img)

    def create_animated_scene_clip(
        self,
        image_path: str,
        duration: float,
        motion_type: str = "zoom_in"
    ) -> VideoClip:
        """
        Generate a dynamic Ken Burns camera motion clip from a static keyframe.
        Motions:
        - zoom_in: Smooth cinematic punch-in (1.0 -> 1.08)
        - zoom_out: Smooth cinematic reveal (1.08 -> 1.0)
        - pan_right: Smooth lateral tracking pan to the right
        - pan_left: Smooth lateral tracking pan to the left
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Scene image missing: {image_path}")

        raw_img = Image.open(image_path).convert("RGB")
        margin = 1.12
        target_w = int(self.width * margin)
        target_h = int(self.height * margin)

        # Cover resize
        img_w, img_h = raw_img.size
        aspect_raw = img_w / img_h
        aspect_target = target_w / target_h

        if aspect_raw > aspect_target:
            new_h = target_h
            new_w = int(target_h * aspect_raw)
        else:
            new_w = target_w
            new_h = int(target_w / aspect_raw)

        resized_raw = raw_img.resize((new_w, new_h), Image.Resampling.BICUBIC)
        crop_x = (new_w - target_w) // 2
        crop_y = (new_h - target_h) // 2
        base_canvas = resized_raw.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))

        bw, bh = base_canvas.size
        w, h = self.width, self.height

        def make_frame(t):
            progress = min(max(t / duration, 0.0), 1.0)
            smooth_p = 0.5 - 0.5 * math.cos(progress * math.pi)

            if motion_type == "zoom_in":
                scale = 1.0 + 0.08 * smooth_p
                cw = int(w * margin / scale)
                ch = int(h * margin / scale)
                left = (bw - cw) // 2
                top = (bh - ch) // 2
            elif motion_type == "zoom_out":
                scale = 1.08 - 0.08 * smooth_p
                cw = int(w * margin / scale)
                ch = int(h * margin / scale)
                left = (bw - cw) // 2
                top = (bh - ch) // 2
            elif motion_type == "pan_left":
                cw = w
                ch = h
                max_shift_x = bw - w
                left = int(max_shift_x * (1.0 - smooth_p))
                top = (bh - ch) // 2
            else:  # pan_right
                cw = w
                ch = h
                max_shift_x = bw - w
                left = int(max_shift_x * smooth_p)
                top = (bh - ch) // 2

            cropped = base_canvas.crop((left, top, left + cw, top + ch))
            if cropped.size != (w, h):
                cropped = cropped.resize((w, h), Image.Resampling.BILINEAR)
            return np.array(cropped)

        return VideoClip(make_frame, duration=duration)

    def assemble_scene_clip(
        self,
        scene: Dict[str, Any],
        duration: float,
        motion_type: str = "zoom_in"
    ) -> CompositeVideoClip:
        """
        Assemble dynamic camera background, upper golden ratio kinetic badge,
        and lower golden ratio narration capsule.
        """
        img_path = scene.get("local_image_path", "")
        bg_clip = self.create_animated_scene_clip(img_path, duration=duration, motion_type=motion_type)
        layers = [bg_clip]

        # 1. Kinetic typography card at Upper Golden Ratio Point (Y ~ 733px)
        kinetic_text = scene.get("kinetic_typography", {}).get("text", "")
        if kinetic_text:
            kinetic_img = self.create_kinetic_card(kinetic_text)
            card_dur = min(duration - 0.4, 3.2)
            card_y = self.Y_UPPER_GOLDEN - 110
            card_clip = (
                ImageClip(kinetic_img)
                .with_duration(card_dur)
                .with_start(0.2)
                .with_position(("center", card_y))
                .with_effects([vfx.CrossFadeIn(0.25), vfx.CrossFadeOut(0.25)])
            )
            layers.append(card_clip)

        # 2. Narration Subtitle Strip at Lower Golden Ratio Point (Y ~ 1186px)
        narration = scene.get("narration_segment", "")
        if narration:
            sub_img = self.create_subtitle_strip(narration)
            sub_y = self.Y_LOWER_GOLDEN - 30
            sub_clip = (
                ImageClip(sub_img)
                .with_duration(duration)
                .with_position(("center", sub_y))
            )
            layers.append(sub_clip)

        return CompositeVideoClip(layers, size=(self.width, self.height)).with_duration(duration)

    def assemble_entry(
        self,
        entry_data: Dict[str, Any],
        storyboard: Dict[str, Any],
        output_path: str,
        bgm_path: Optional[str] = None,
        platform_preset: Optional[str] = None,
    ) -> str:
        """
        Assemble the full video with dynamic camera motions, 0.5s transitions,
        synchronized TTS voiceover, and gentle backgroup_music BGM.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        scenes = storyboard.get("scenes", [])
        if not scenes:
            raise ValueError("Storyboard contains no scenes!")

        chapter_title = entry_data.get("chapter_title", "")
        evidence_grade = entry_data.get("evidence_grade", "A")

        motion_sequence = ["zoom_in", "pan_right", "zoom_out", "pan_left"]

        # 1. Build animated scene clips
        scene_clips: List[CompositeVideoClip] = []
        for idx, s in enumerate(scenes):
            dur = float(s.get("duration_sec", 6.0))
            motion = motion_sequence[idx % len(motion_sequence)]
            clip = self.assemble_scene_clip(s, duration=dur, motion_type=motion)
            scene_clips.append(clip)

        # 2. Compose video timeline with 0.5s cross-dissolve transitions
        transition_dur = 0.5
        timeline_clips: List[CompositeVideoClip] = []
        scene_start_times: List[float] = []
        current_start = 0.0

        for i, clip in enumerate(scene_clips):
            if i == 0:
                timeline_clips.append(clip.with_start(0.0))
                scene_start_times.append(0.0)
                current_start += clip.duration
            else:
                overlap_start = current_start - transition_dur
                clip_with_fade = clip.with_start(overlap_start).with_effects([vfx.CrossFadeIn(transition_dur)])
                timeline_clips.append(clip_with_fade)
                scene_start_times.append(overlap_start)
                current_start = overlap_start + clip.duration

        total_duration = current_start
        main_video = CompositeVideoClip(timeline_clips, size=(self.width, self.height)).with_duration(total_duration)

        # 3. Add top persistent header badge
        header_arr = self.create_header_badge(chapter_title, evidence_grade)
        header_clip = (
            ImageClip(header_arr)
            .with_duration(total_duration)
            .with_position(("center", 30))
        )

        final_composite = CompositeVideoClip([main_video, header_clip], size=(self.width, self.height)).with_duration(total_duration)

        # 4. Prepare Voiceover Audio Tracks (TTS)
        voice_clips: List[AudioFileClip] = []
        for idx, s in enumerate(scenes):
            voice_path = s.get("local_audio_path")
            if voice_path and os.path.exists(voice_path):
                v_clip = AudioFileClip(voice_path)
                # Align audio start time with scene transition
                start_t = scene_start_times[idx]
                # Tiny 0.15s breathing delay for subsequent scenes after transition begins
                if idx > 0:
                    start_t += 0.15
                else:
                    start_t += 0.10

                v_clip_positioned = v_clip.with_start(start_t).with_volume_scaled(1.0)
                voice_clips.append(v_clip_positioned)

        # 5. Select and Mix BGM from backgroup_music/
        selected_bgm = bgm_path
        if not selected_bgm:
            bgm_dir = BACKGROUP_MUSIC_DIR if os.path.exists(BACKGROUP_MUSIC_DIR) else ASSETS_BGM_DIR
            if os.path.exists(bgm_dir):
                candidate_files = [
                    os.path.join(bgm_dir, f)
                    for f in os.listdir(bgm_dir)
                    if f.endswith((".mp3", ".wav", ".m4a"))
                ]
                if candidate_files:
                    selected_bgm = random.choice(candidate_files)

        all_audio_tracks = list(voice_clips)

        if selected_bgm and os.path.exists(selected_bgm):
            try:
                bgm_audio = AudioFileClip(selected_bgm)
                if bgm_audio.duration < total_duration:
                    bgm_audio = bgm_audio.with_effects([afx.AudioLoop(duration=total_duration)])
                else:
                    bgm_audio = bgm_audio.subclipped(0, total_duration)

                # Lower BGM volume significantly (0.09) so it never overpowers the speech
                bgm_audio = bgm_audio.with_volume_scaled(0.09)
                bgm_audio = bgm_audio.with_effects([
                    afx.AudioFadeIn(1.0),
                    afx.AudioFadeOut(2.0)
                ])
                all_audio_tracks.append(bgm_audio)
                print(f"🎵 成功加载背景音乐: {os.path.basename(selected_bgm)} (微音量: 0.09)")
            except Exception as e:
                print(f"⚠️ BGM loading warning: {e}. Outputting voice-only audio.")

        if all_audio_tracks:
            final_audio = CompositeAudioClip(all_audio_tracks).with_duration(total_duration)
            final_composite = final_composite.with_audio(final_audio)

        # 6. Export MP4 with platform preset and optimal H.264 encoding
        preset_key = platform_preset or self.default_preset
        preset_cfg = get_platform_preset(preset_key)
        crf = preset_cfg["crf"]
        enc_preset = preset_cfg.get("preset", "medium")
        audio_bitrate = preset_cfg.get("audio_bitrate", "128k")
        maxrate = preset_cfg.get("maxrate", "5000k")
        bufsize = preset_cfg.get("bufsize", "10000k")

        ffmpeg_params = [
            "-crf", str(crf),
            "-maxrate", maxrate,
            "-bufsize", bufsize,
            "-movflags", "+faststart",
        ]

        print(
            f"⚙️ 正在应用发布码率预设: [{preset_cfg['name']}] "
            f"(CRF={crf}, MaxRate={maxrate}, Audio={audio_bitrate}, movflags=+faststart)"
        )

        final_composite.write_videofile(
            output_path,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate=audio_bitrate,
            pixel_format="yuv420p",
            preset=enc_preset,
            threads=4,
            ffmpeg_params=ffmpeg_params,
            logger=None
        )

        final_composite.close()
        for c in scene_clips:
            c.close()
        for vc in voice_clips:
            vc.close()

        return output_path
