"""Cover card generator module for HowToLiveBetter-Motion.
Generates 1080x1920 vertical high-CTR cover images for Xiaohongshu, Douyin, and WeChat Channels.
"""

import argparse
import io
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.assembler import find_system_font
from src.config import OUTPUT_FINAL_VIDEOS_DIR, OUTPUT_RAW_ASSETS_DIR
from src.db import get_connection, get_entry
from src.prompt_builder import get_style_recipe


class CoverGenerator:
    """Generates 1080x1920 high-contrast vertical cover cards for short videos."""

    def __init__(self, font_bold_path: Optional[str] = None, font_reg_path: Optional[str] = None):
        self.font_bold_path = font_bold_path or find_system_font(bold=True)
        self.font_reg_path = font_reg_path or find_system_font(bold=False)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Load font at specific point size with fallback."""
        path = self.font_bold_path if bold else self.font_reg_path
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    def generate_cover(
        self,
        entry: Dict[str, Any],
        background_image_path: Optional[str] = None,
        output_path: Optional[str] = None,
        storyboard_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a vertical 1080x1920 cover image for an entry.

        Args:
            entry: Entry data dictionary from database.
            background_image_path: Path to scene_01.png or background image.
            output_path: Target path to save the cover image.
            storyboard_data: Optional parsed storyboard JSON dictionary.

        Returns:
            Absolute path of the saved cover image.
        """
        canvas_w, canvas_h = 1080, 1920
        entry_id = entry.get("id", "01_001")
        chapter_title = entry.get("chapter_title", "生活指南")
        chapter_index = entry.get("chapter_index", 1)
        title = entry.get("title", "高性价比人生建议")
        evidence_grade = entry.get("evidence_grade", "A") or "A"
        cost_desc = entry.get("cost_desc", "不花钱")
        plain_text = entry.get("plain_text", "")
        benefit_desc = entry.get("benefit_desc", "")

        # 1. Prepare output path
        if not output_path:
            asset_dir = os.path.join(OUTPUT_RAW_ASSETS_DIR, entry_id)
            os.makedirs(asset_dir, exist_ok=True)
            output_path = os.path.join(asset_dir, "cover.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 2. Build or load base background image (1080x1920)
        base_img = self._create_base_background(
            background_image_path,
            entry.get("chapter_index", 1),
            canvas_w,
            canvas_h
        )

        # 3. Create drawing overlay
        overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 4. Render Layout Elements
        # 4.1 Top Tag & Chapter Header (Y: 180 ~ 300)
        self._render_header(draw, chapter_index, chapter_title)

        # 4.2 Central Card & Hero Title & Hook (Y: 420 ~ 1400)
        self._render_central_hero_card(
            draw,
            title,
            plain_text,
            cost_desc,
            benefit_desc,
            evidence_grade,
            storyboard_data
        )

        # 4.3 Footer Brand Signature (Y: 1720 ~ 1820)
        self._render_footer(draw)

        # 5. Composite and save
        final_img = Image.alpha_composite(base_img.convert("RGBA"), overlay)
        final_img = final_img.convert("RGB")
        final_img.save(output_path, "PNG", quality=95)

        # Also copy to output/final_videos/{entry_id}_cover.png if final_videos dir exists
        try:
            os.makedirs(OUTPUT_FINAL_VIDEOS_DIR, exist_ok=True)
            safe_title = "".join(c for c in title if c not in '\\/:*?"<>|')
            final_dest = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, f"{entry_id}_{chapter_title}之{safe_title}_cover.png")
            final_img.save(final_dest, "PNG", quality=95)
        except Exception:
            pass

        return output_path

    def _create_base_background(
        self,
        bg_path: Optional[str],
        chapter_index: int,
        w: int,
        h: int
    ) -> Image.Image:
        """Create high-resolution base canvas with cinematic darkening gradient."""
        canvas = None

        if bg_path and os.path.exists(bg_path):
            try:
                raw_bg = Image.open(bg_path).convert("RGBA")
                # Resize and crop to fill 1080x1920
                scale = max(w / raw_bg.width, h / raw_bg.height)
                new_w, new_h = int(raw_bg.width * scale), int(raw_bg.height * scale)
                resized = raw_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
                crop_x = (new_w - w) // 2
                crop_y = (new_h - h) // 2
                canvas = resized.crop((crop_x, crop_y, crop_x + w, crop_y + h))
                # Apply subtle blur to add depth of field
                canvas = canvas.filter(ImageFilter.GaussianBlur(radius=2))
            except Exception:
                canvas = None

        if canvas is None:
            # Fallback aesthetic gradient
            canvas = Image.new("RGBA", (w, h), (15, 23, 42, 255))
            draw = ImageDraw.Draw(canvas)
            top_color = (15, 23, 42)
            bottom_color = (30, 41, 59)
            for y in range(h):
                r = int(top_color[0] + (bottom_color[0] - top_color[0]) * (y / h))
                g = int(top_color[1] + (bottom_color[1] - top_color[1]) * (y / h))
                b = int(top_color[2] + (bottom_color[2] - top_color[2]) * (y / h))
                draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

        # Apply multi-stage dark scrim overlay for high text legibility
        scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        scrim_draw = ImageDraw.Draw(scrim)
        for y in range(h):
            # Gradual darkening: lighter at top, deepest in middle and lower thirds
            if y < 400:
                alpha = int(120 + 40 * (y / 400))
            elif y < 1400:
                alpha = int(160 + 35 * ((y - 400) / 1000))
            else:
                alpha = int(195 + 40 * ((y - 1400) / 520))
            scrim_draw.line([(0, y), (w, y)], fill=(10, 15, 29, min(alpha, 235)))

        return Image.alpha_composite(canvas, scrim)

    def _render_header(self, draw: ImageDraw.ImageDraw, chapter_index: int, chapter_title: str):
        """Render top category badges and chapter label without emoji tofu glyphs."""
        font_tag = self._get_font(28, bold=True)
        font_chapter = self._get_font(34, bold=True)

        # 1. Category Tag Pill (Top Left)
        tag_text = "高性价比人生指南"
        bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        px, py = 72, 185
        pad_x, pad_y = 22, 10
        # Draw a small accent dot inside pill
        dot_radius = 5
        pill_rect = (px, py, px + tw + pad_x * 2 + 20, py + th + pad_y * 2)
        draw.rounded_rectangle(pill_rect, radius=18, fill=(217, 119, 6, 230), outline=(251, 191, 36, 255), width=2)
        # Dot
        draw.ellipse(
            (px + 16, py + pad_y + th // 2 - dot_radius, px + 16 + dot_radius * 2, py + pad_y + th // 2 + dot_radius),
            fill=(255, 255, 255, 255)
        )
        draw.text((px + 32, py + pad_y), tag_text, font=font_tag, fill=(255, 255, 255, 255))

        # 2. Chapter Subhead
        chapter_str = f"第 {chapter_index:02d} 章 · 《{chapter_title}》"
        draw.text((px, py + th + pad_y * 2 + 18), chapter_str, font=font_chapter, fill=(226, 232, 240, 245))

    def _render_central_hero_card(
        self,
        draw: ImageDraw.ImageDraw,
        title: str,
        plain_text: str,
        cost_desc: str,
        benefit_desc: str,
        evidence_grade: str,
        storyboard_data: Optional[Dict[str, Any]]
    ):
        """Render the prominent frosted glass card containing hero title, hook and badges."""
        card_x1, card_y1 = 64, 420
        card_x2, card_y2 = 1016, 1560
        card_w = card_x2 - card_x1

        # 1. Frosted card background container
        draw.rounded_rectangle(
            (card_x1, card_y1, card_x2, card_y2),
            radius=32,
            fill=(15, 23, 42, 220),
            outline=(245, 158, 11, 235),  # Amber border
            width=3
        )

        # 2. Corner decorative highlight tag
        rec_tag = "核心精选建议"
        font_rec = self._get_font(26, bold=True)
        tag_w = 180
        draw.rounded_rectangle(
            (card_x1 + 36, card_y1 + 36, card_x1 + 36 + tag_w, card_y1 + 82),
            radius=12,
            fill=(245, 158, 11, 45),
            outline=(245, 158, 11, 200),
            width=2
        )
        draw.text((card_x1 + 52, card_y1 + 44), rec_tag, font=font_rec, fill=(251, 191, 36, 255))

        # 3. Hero Title (Large, Bold, Intelligent comma splitting & auto-wrapping)
        font_title = self._get_font(76, bold=True)
        max_title_w = card_w - 72

        # Split intelligently by comma if present for punchy short-video poster feel
        title_lines = []
        if "，" in title and len(title) <= 24:
            parts = title.split("，")
            for p in parts:
                title_lines.extend(self._wrap_text(p.strip(), font_title, max_title_w))
        else:
            title_lines = self._wrap_text(title, font_title, max_title_w)

        cur_y = card_y1 + 115
        line_height = 96

        for line in title_lines:
            # Drop shadow
            draw.text((card_x1 + 38, cur_y + 4), line, font=font_title, fill=(0, 0, 0, 230))
            draw.text((card_x1 + 36, cur_y), line, font=font_title, fill=(255, 255, 255, 255))
            cur_y += line_height

        # 4. Accent divider bar
        cur_y += 12
        draw.rectangle(
            (card_x1 + 36, cur_y, card_x1 + 160, cur_y + 6),
            fill=(245, 158, 11, 255)
        )
        cur_y += 32

        # 5. Hook Subtitle (说人话 / 核心反直觉论据)
        font_hook = self._get_font(38, bold=True)
        hook_text = ""
        if storyboard_data and "scenes" in storyboard_data and len(storyboard_data["scenes"]) > 1:
            hook_text = storyboard_data["scenes"][1].get("narration_segment", "")
        if not hook_text and plain_text:
            hook_text = plain_text.split("。")[0] + "。"
        if not hook_text:
            hook_text = "用最低的执行成本，锁死最高的生活确定性。"

        hook_text = hook_text.strip()
        hook_lines = self._wrap_text(hook_text, font_hook, max_title_w)[:3]

        for h_line in hook_lines:
            draw.text((card_x1 + 36, cur_y), h_line, font=font_hook, fill=(254, 240, 138, 255))
            cur_y += 54

        # 6. Authority & Value Badges Bar (Horizontal arrangement)
        badge_y = card_y2 - 190
        self._render_badges_bar(draw, card_x1 + 36, badge_y, evidence_grade, cost_desc, benefit_desc)

    def _render_badges_bar(
        self,
        draw: ImageDraw.ImageDraw,
        start_x: int,
        start_y: int,
        evidence_grade: str,
        cost_desc: str,
        benefit_desc: str
    ):
        """Render 3 structured badges: Evidence Grade, Cost, and Return."""
        font_badge_title = self._get_font(22, bold=False)
        font_badge_val = self._get_font(30, bold=True)

        # Simplify cost label
        cost_clean = "几乎零成本"
        if "0" in cost_desc or "不花钱" in cost_desc:
            cost_clean = "成本: 0元/秒"
        elif "元" in cost_desc:
            cost_clean = "超低开销"

        # Simplify benefit label
        benefit_clean = "极高确定性"
        if "降" in benefit_desc or "少" in benefit_desc:
            benefit_clean = "风险砍半"
        elif "倍" in benefit_desc:
            benefit_clean = "收益翻倍"

        badges = [
            {
                "label": "权威背书",
                "val": f"{evidence_grade} 级硬核证据",
                "bg": (30, 58, 138, 230),      # Blue
                "border": (96, 165, 250, 255),
                "text_color": (219, 234, 254, 255)
            },
            {
                "label": "执行代价",
                "val": cost_clean,
                "bg": (6, 78, 59, 230),        # Green
                "border": (52, 211, 153, 255),
                "text_color": (209, 250, 229, 255)
            },
            {
                "label": "核心收益",
                "val": benefit_clean,
                "bg": (124, 45, 18, 230),      # Orange/Red
                "border": (251, 146, 60, 255),
                "text_color": (255, 237, 213, 255)
            }
        ]

        badge_w = 278
        badge_h = 126
        gap = 22

        for idx, b in enumerate(badges):
            bx = start_x + idx * (badge_w + gap)
            by = start_y
            # Background pill
            draw.rounded_rectangle(
                (bx, by, bx + badge_w, by + badge_h),
                radius=18,
                fill=b["bg"],
                outline=b["border"],
                width=2
            )
            # Label
            draw.text((bx + 20, by + 18), b["label"], font=font_badge_title, fill=(203, 213, 225, 220))
            # Value
            draw.text((bx + 20, by + 56), b["val"], font=font_badge_val, fill=b["text_color"])

    def _render_footer(self, draw: ImageDraw.ImageDraw):
        """Render bottom brand pill."""
        font_footer = self._get_font(28, bold=True)
        brand_text = "HowToLiveBetter-Motion · 权威大众科普"

        bbox = draw.textbbox((0, 0), brand_text, font=font_footer)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        center_x = 1080 // 2
        py = 1750
        pad_x, pad_y = 28, 12

        rx1 = center_x - (tw // 2) - pad_x
        rx2 = center_x + (tw // 2) + pad_x
        ry1 = py
        ry2 = py + th + pad_y * 2

        draw.rounded_rectangle(
            (rx1, ry1, rx2, ry2),
            radius=20,
            fill=(15, 23, 42, 200),
            outline=(100, 116, 139, 180),
            width=2
        )
        draw.text((rx1 + pad_x, ry1 + pad_y), brand_text, font=font_footer, fill=(226, 232, 240, 240))

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
        """Wrap text into multiple lines based on maximum pixel width."""
        lines = []
        cur_line = ""
        for char in text:
            test_line = cur_line + char
            bbox = font.getbbox(test_line)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                cur_line = test_line
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = char
        if cur_line:
            lines.append(cur_line)
        return lines


def main():
    parser = argparse.ArgumentParser(description="Generate 1080x1920 cover cards for short videos.")
    parser.add_argument("--entry-id", type=str, default="01_001", help="Target entry ID (e.g. 01_001)")
    parser.add_argument("--output", type=str, default=None, help="Custom output image path")
    args = parser.parse_args()

    conn = get_connection()
    entry = get_entry(conn, args.entry_id)
    if not entry:
        print(f"❌ Entry not found: {args.entry_id}")
        sys.exit(1)

    # Check for existing scene_01.png and storyboard.json
    asset_dir = os.path.join(OUTPUT_RAW_ASSETS_DIR, args.entry_id)
    scene_01_path = os.path.join(asset_dir, "scene_01.png")
    storyboard_path = os.path.join(asset_dir, "storyboard.json")

    storyboard_data = None
    if os.path.exists(storyboard_path):
        try:
            with open(storyboard_path, "r", encoding="utf-8") as f:
                storyboard_data = json.load(f)
        except Exception:
            pass

    bg_path = scene_01_path if os.path.exists(scene_01_path) else None

    generator = CoverGenerator()
    out_file = generator.generate_cover(
        entry=entry,
        background_image_path=bg_path,
        output_path=args.output,
        storyboard_data=storyboard_data
    )
    print(f"✅ 封面卡片生成成功: {out_file}")


if __name__ == "__main__":
    main()
