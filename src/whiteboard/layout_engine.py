"""Whiteboard layout engine and vector trajectory builder for Zen minimalist explainers."""

import math
import os
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.config import ASSETS_FONTS_DIR


@dataclass
class BoardItem:
    """A conceptual item on the whiteboard."""
    item_id: str
    title: str = ""
    subtitle: str = ""
    color_accent: str = "#7BC8A4"  # Pastel color (e.g., mint green, sky blue, wood brown)
    box_type: str = "rounded_box"  # rounded_box, server_box, paper_plane, network_graph, custom
    slot_index: int = 0
    center_pos: Tuple[int, int] = (0, 0)
    width: int = 240
    height: int = 140
    strokes: List[List[Tuple[float, float]]] = field(default_factory=list)


@dataclass
class BoardLayout:
    """Full whiteboard scene specifications."""
    scene_title: str = "几个设计取舍"
    title_underline_color: str = "#E28743"
    canvas_bg_color: str = "#FAF8F5"  # Warm ivory paper
    items: List[BoardItem] = field(default_factory=list)
    whitespace_ratio: float = 0.70  # Target >= 65% negative space


class WhiteboardLayoutEngine:
    """Engine for procedural whiteboard paper rendering, element placement, and stroke path extraction."""

    def __init__(self, width: int = 1080, height: int = 1920):
        self.width = width
        self.height = height
        self.font_cache: Dict[Tuple[int, bool], ImageFont.FreeTypeFont] = {}

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Discover and load high-quality Chinese fonts with graceful fallback."""
        cache_key = (size, bold)
        if cache_key in self.font_cache:
            return self.font_cache[cache_key]

        candidates = [
            os.path.join(ASSETS_FONTS_DIR, "SourceHanSansCN-Bold.otf" if bold else "SourceHanSansCN-Regular.otf"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "msyhbd.ttc" if bold else "msyh.ttc"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simhei.ttf"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
        ]

        for font_path in candidates:
            if os.path.exists(font_path):
                try:
                    loaded = ImageFont.truetype(font_path, size)
                    self.font_cache[cache_key] = loaded
                    return loaded
                except Exception:
                    continue

        fallback = ImageFont.load_default()
        self.font_cache[cache_key] = fallback
        return fallback

    def create_paper_canvas(self) -> Image.Image:
        """Create a 1080x1920 warm ivory background with subtle natural paper noise grain."""
        # Base ivory paper: #FAF8F5 (R: 250, G: 248, B: 245)
        base = np.full((self.height, self.width, 3), (250, 248, 245), dtype=np.uint8)

        # Micro-texture noise (amplitude ~3) for tactile paper feel
        rng = np.random.default_rng(seed=42)
        grain = rng.integers(-2, 3, size=(self.height, self.width, 3), dtype=np.int16)
        textured = np.clip(base.astype(np.int16) + grain, 0, 255).astype(np.uint8)

        return Image.fromarray(textured)

    def build_sample_layout(self) -> BoardLayout:
        """Build a reference 4-item horizontal layout matching the prototype attachment."""
        layout = BoardLayout(
            scene_title="几个设计取舍",
            title_underline_color="#E28743",
            canvas_bg_color="#FAF8F5",
            whitespace_ratio=0.72,
        )

        # 4 items arranged along mid-horizontal line (Y ~ 880 in vertical 1080x1920)
        # 1. 保存 button with cursor
        # 2. 家 / 小电脑 server box
        # 3. Telegram 输入 paper airplane
        # 4. Triangle network node graph
        center_y = 860

        # Slot 1: Button
        item1 = BoardItem(
            item_id="save_btn",
            title="保存",
            subtitle="唯一会写文件",
            color_accent="#D5E8D4",  # Light pastel green
            box_type="rounded_box",
            slot_index=0,
            center_pos=(180, center_y),
            width=180,
            height=90,
        )
        item1.strokes = self.generate_rounded_box_strokes(180, center_y, 180, 90, radius=36)
        # Add cursor stroke
        item1.strokes.extend(self.generate_cursor_strokes(245, center_y + 35, size=55))

        # Slot 2: Server box
        item2 = BoardItem(
            item_id="home_server",
            title="家",
            subtitle="家里小电脑",
            color_accent="#D08770",  # Light warm brown / orange
            box_type="server_box",
            slot_index=1,
            center_pos=(440, center_y),
            width=170,
            height=90,
        )
        item2.strokes = self.generate_server_box_strokes(440, center_y, 170, 90)

        # Slot 3: Paper plane
        item3 = BoardItem(
            item_id="telegram_plane",
            title="",
            subtitle="Telegram 输入",
            color_accent="#A8D0E6",  # Light sky blue
            box_type="paper_plane",
            slot_index=2,
            center_pos=(680, center_y),
            width=180,
            height=130,
        )
        item3.strokes = self.generate_paper_plane_strokes(680, center_y, size=110)

        # Slot 4: Triangle network
        item4 = BoardItem(
            item_id="network_graph",
            title="",
            subtitle="",
            color_accent="#008080",  # Teal connector
            box_type="network_graph",
            slot_index=3,
            center_pos=(910, center_y),
            width=170,
            height=140,
        )
        item4.strokes = self.generate_network_graph_strokes(910, center_y, radius=70)

        layout.items = [item1, item2, item3, item4]
        return layout

    # --- [Procedural Hand-Drawn Stroke Generators] ---

    def generate_title_underline_strokes(
        self, start_x: float, start_y: float, end_x: float, end_y: float
    ) -> List[List[Tuple[float, float]]]:
        """Generate a slightly curved, hand-drawn brush stroke line."""
        steps = 40
        points = []
        for i in range(steps + 1):
            t = i / steps
            x = start_x + (end_x - start_x) * t
            # Subtle natural downward hand arc
            arc = math.sin(t * math.pi) * 3.5
            wobble = (math.sin(t * 18.0) * 0.8)
            y = start_y + (end_y - start_y) * t + arc + wobble
            points.append((round(x, 2), round(y, 2)))
        return [points]

    def generate_rounded_box_strokes(
        self, cx: float, cy: float, w: float, h: float, radius: float = 30.0
    ) -> List[List[Tuple[float, float]]]:
        """Generate closed rounded box stroke path with slight hand-drawn imperfection."""
        half_w = w / 2.0
        half_h = h / 2.0
        r = min(radius, half_w, half_h)

        points: List[Tuple[float, float]] = []
        # Top-left start
        steps_corner = 10
        # 1. Top horizontal: from (cx - half_w + r, cy - half_h) to (cx + half_w - r, cy - half_h)
        for i in range(15):
            t = i / 14.0
            px = (cx - half_w + r) + (w - 2 * r) * t
            py = cy - half_h + (math.sin(t * 7) * 0.6)
            points.append((round(px, 2), round(py, 2)))

        # 2. Top-right corner
        for i in range(steps_corner):
            ang = -math.pi / 2.0 + (math.pi / 2.0) * (i / (steps_corner - 1))
            px = (cx + half_w - r) + r * math.cos(ang)
            py = (cy - half_h + r) + r * math.sin(ang)
            points.append((round(px, 2), round(py, 2)))

        # 3. Right vertical
        for i in range(12):
            t = i / 11.0
            px = cx + half_w + (math.sin(t * 6) * 0.5)
            py = (cy - half_h + r) + (h - 2 * r) * t
            points.append((round(px, 2), round(py, 2)))

        # 4. Bottom-right corner
        for i in range(steps_corner):
            ang = 0.0 + (math.pi / 2.0) * (i / (steps_corner - 1))
            px = (cx + half_w - r) + r * math.cos(ang)
            py = (cy + half_h - r) + r * math.sin(ang)
            points.append((round(px, 2), round(py, 2)))

        # 5. Bottom horizontal
        for i in range(15):
            t = i / 14.0
            px = (cx + half_w - r) - (w - 2 * r) * t
            py = cy + half_h + (math.sin(t * 7) * 0.6)
            points.append((round(px, 2), round(py, 2)))

        # 6. Bottom-left corner
        for i in range(steps_corner):
            ang = math.pi / 2.0 + (math.pi / 2.0) * (i / (steps_corner - 1))
            px = (cx - half_w + r) + r * math.cos(ang)
            py = (cy + half_h - r) + r * math.sin(ang)
            points.append((round(px, 2), round(py, 2)))

        # 7. Left vertical
        for i in range(12):
            t = i / 11.0
            px = cx - half_w + (math.sin(t * 6) * 0.5)
            py = (cy + half_h - r) - (h - 2 * r) * t
            points.append((round(px, 2), round(py, 2)))

        # 8. Top-left corner to close
        for i in range(steps_corner):
            ang = math.pi + (math.pi / 2.0) * (i / (steps_corner - 1))
            px = (cx - half_w + r) + r * math.cos(ang)
            py = (cy - half_h + r) + r * math.sin(ang)
            points.append((round(px, 2), round(py, 2)))

        return [points]

    def generate_cursor_strokes(self, tip_x: float, tip_y: float, size: float = 50.0) -> List[List[Tuple[float, float]]]:
        """Generate mouse arrow pointer stroke."""
        # Standard cursor shape
        rel_coords = [
            (0, 0),
            (0, 1.0),
            (0.28, 0.75),
            (0.55, 1.15),
            (0.72, 1.05),
            (0.45, 0.65),
            (0.85, 0.65),
            (0, 0),
        ]
        points = [(tip_x + rx * size, tip_y + ry * size) for rx, ry in rel_coords]
        return [points]

    def generate_server_box_strokes(self, cx: float, cy: float, w: float, h: float) -> List[List[Tuple[float, float]]]:
        """Generate minimalist server/NAS box strokes: outer box, power LED circle, and slot line."""
        strokes = []
        # 1. Outer rounded box
        outer = self.generate_rounded_box_strokes(cx, cy, w, h, radius=18)
        strokes.extend(outer)

        # 2. Power LED circle at left
        led_cx = cx - w / 2.0 + 32
        led_cy = cy
        led_r = 10
        circle_pts = []
        for i in range(25):
            ang = (i / 24.0) * 2 * math.pi
            circle_pts.append((led_cx + led_r * math.cos(ang), led_cy + led_r * math.sin(ang)))
        strokes.append(circle_pts)

        # 3. Horizontal slot line
        slot_x1 = cx - 18
        slot_x2 = cx + w / 2.0 - 24
        slot_y = cy
        slot_pts = [(slot_x1 + (slot_x2 - slot_x1) * (i / 15.0), slot_y) for i in range(16)]
        strokes.append(slot_pts)

        return strokes

    def generate_paper_plane_strokes(self, cx: float, cy: float, size: float = 100.0) -> List[List[Tuple[float, float]]]:
        """Generate paper airplane strokes (Telegram style)."""
        # Tip points right-up
        tip = (cx + size * 0.7, cy - size * 0.3)
        bottom_left = (cx - size * 0.6, cy + size * 0.1)
        crease = (cx - size * 0.1, cy + size * 0.45)
        top_fold = (cx - size * 0.6, cy + size * 0.1)

        # Main contour: tip -> bottom_left -> crease -> tip
        path1 = [tip, bottom_left, crease, tip]
        # Inner fold line: crease to tip
        path2 = [crease, (cx + size * 0.1, cy)]
        return [path1, path2]

    def generate_network_graph_strokes(
        self, cx: float, cy: float, radius: float = 65.0
    ) -> List[List[Tuple[float, float]]]:
        """Generate 3-node triangular network strokes (3 circles + connecting triangle)."""
        strokes = []
        # Node positions
        r = radius
        node_radius = 22.0
        n1 = (cx - r * 0.85, cy - r * 0.5)
        n2 = (cx + r * 0.85, cy - r * 0.5)
        n3 = (cx, cy + r * 0.8)

        # Triangle connector lines (teal)
        strokes.append([n1, n2])
        strokes.append([n2, n3])
        strokes.append([n3, n1])

        # 3 Circles
        for nx, ny in [n1, n2, n3]:
            c_pts = []
            for i in range(25):
                ang = (i / 24.0) * 2 * math.pi
                c_pts.append((nx + node_radius * math.cos(ang), ny + node_radius * math.sin(ang)))
            strokes.append(c_pts)

        return strokes

    # --- [Static Completed Board Rendering] ---

    def render_static_board(self, layout: BoardLayout) -> Image.Image:
        """Render the fully drawn, finalized whiteboard graphic with crisp typography."""
        canvas = self.create_paper_canvas()
        draw = ImageDraw.Draw(canvas)

    def create_base_canvas(self, layout: BoardLayout) -> Image.Image:
        """Create the textured paper canvas with the scene title pre-rendered."""
        canvas = self.create_paper_canvas()
        draw = ImageDraw.Draw(canvas)
        title_font = self._get_font(56, bold=True)
        title_x = 90
        title_y = 130
        draw.text((title_x, title_y), layout.scene_title, fill=(35, 35, 35), font=title_font)
        return canvas

    def render_item_fill_and_labels(self, draw: ImageDraw.ImageDraw, item: BoardItem):
        """Render pastel color fill, button/server text, and subtitle below the icon."""
        cx, cy = item.center_pos

        if item.item_id == "save_btn":
            bx1 = cx - item.width // 2
            by1 = cy - item.height // 2
            bx2 = cx + item.width // 2
            by2 = cy + item.height // 2
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=36, fill=(215, 238, 220), outline=None)
            btn_font = self._get_font(36, bold=True)
            draw.text((cx - 15, cy), "保存", fill=(46, 117, 89), font=btn_font, anchor="mm")

        elif item.item_id == "home_server":
            bx1 = cx - item.width // 2
            by1 = cy - item.height // 2
            bx2 = cx + item.width // 2
            by2 = cy + item.height // 2
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=18, fill=(245, 245, 245), outline=None)
            led_cx = cx - item.width // 2 + 32
            draw.ellipse([led_cx - 9, cy - 9, led_cx + 9, cy + 9], fill=(46, 117, 89))
            home_font = self._get_font(32, bold=True)
            draw.text((cx, by1 - 32), "家", fill=(160, 95, 50), font=home_font, anchor="mm")

        elif item.item_id == "telegram_plane":
            tip = (cx + 77, cy - 33)
            bl = (cx - 66, cy + 11)
            cr = (cx - 11, cy + 49)
            draw.polygon([tip, bl, cr], fill=(210, 230, 248))

        if item.subtitle:
            sub_font = self._get_font(26, bold=True)
            text_y = cy + item.height // 2 + 45
            text_color = (46, 117, 89) if ("保存" in item.subtitle or "唯一" in item.subtitle) else (
                (160, 95, 50) if "电脑" in item.subtitle else (
                    (30, 110, 200) if "Telegram" in item.subtitle else (60, 60, 60)
                )
            )
            draw.text((cx, text_y), item.subtitle, fill=text_color, font=sub_font, anchor="mm")

    def render_static_board(self, layout: BoardLayout) -> Image.Image:
        """Render the fully drawn, finalized whiteboard graphic with crisp typography."""
        canvas = self.create_base_canvas(layout)
        draw = ImageDraw.Draw(canvas)

        # Underline accent
        title_x = 90
        ul_y = 130 + 80
        draw.line([(title_x, ul_y), (title_x + 230, ul_y)], fill=(226, 135, 67), width=6)

        # Render items
        for item in layout.items:
            self.render_item_fill_and_labels(draw, item)
            # Black hand-drawn outlines
            for stroke in item.strokes:
                if len(stroke) >= 2:
                    draw.line(stroke, fill=(30, 30, 30), width=3, joint="curve")

        return canvas

