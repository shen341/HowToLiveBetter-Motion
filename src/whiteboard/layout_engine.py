"""Whiteboard layout engine and vector trajectory builder for Zen minimalist explainers."""

import math
import os
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.config import ASSETS_FONTS_DIR
from src.whiteboard.svg_library import SVGIconLibrary


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
        self.svg_library = SVGIconLibrary()

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

    # --- [Additional Minimalist Icons for Scene Storyboard] ---

    def generate_shield_strokes(self, cx: float, cy: float, w: float = 240.0, h: float = 300.0) -> List[List[Tuple[float, float]]]:
        """Generate hand-drawn shield badge outline for evidence/grade validation."""
        half_w = w / 2.0
        points: List[Tuple[float, float]] = []
        top_y = cy - h / 2.0
        mid_y = cy + h * 0.1
        bottom_y = cy + h / 2.0

        # 1. Top curved edge: from (cx - half_w, top_y) to (cx + half_w, top_y)
        for i in range(16):
            t = i / 15.0
            px = (cx - half_w) + w * t
            py = top_y + math.sin(t * math.pi) * 12.0
            points.append((round(px, 2), round(py, 2)))

        # 2. Right vertical-to-bottom edge: from (cx + half_w, top_y) to (cx, bottom_y)
        for i in range(20):
            t = i / 19.0
            px = (cx + half_w) * (1 - t) + cx * t - math.sin(t * math.pi) * 15.0
            py = top_y * (1 - t) + bottom_y * t
            points.append((round(px, 2), round(py, 2)))

        # 3. Bottom to left edge: from (cx, bottom_y) to (cx - half_w, top_y)
        for i in range(20):
            t = i / 19.0
            px = cx * (1 - t) + (cx - half_w) * t - math.sin(t * math.pi) * 15.0
            py = bottom_y * (1 - t) + top_y * t
            points.append((round(px, 2), round(py, 2)))

        # Close
        points.append(points[0])

        # Internal letter 'A' or grade star
        letter_strokes: List[Tuple[float, float]] = []
        # Left leg of A
        for i in range(12):
            t = i / 11.0
            letter_strokes.append((round((cx - 35) + 35 * t, 2), round((cy + 40) - 80 * t, 2)))
        # Right leg of A
        right_leg: List[Tuple[float, float]] = []
        for i in range(12):
            t = i / 11.0
            right_leg.append((round(cx + 35 * t, 2), round((cy - 40) + 80 * t, 2)))
        # Crossbar of A
        bar: List[Tuple[float, float]] = []
        for i in range(8):
            t = i / 7.0
            bar.append((round((cx - 20) + 40 * t, 2), round(cy + 10, 2)))

        return [points, letter_strokes, right_leg, bar]

    def generate_flow_arrow_strokes(
        self, start_x: float, start_y: float, end_x: float, end_y: float
    ) -> List[List[Tuple[float, float]]]:
        """Generate smooth curved arrow with arrowhead."""
        stem: List[Tuple[float, float]] = []
        dx = end_x - start_x
        dy = end_y - start_y
        dist = math.hypot(dx, dy)
        steps = max(15, int(dist / 15))
        for i in range(steps):
            t = i / float(steps - 1)
            # Gentle natural curve
            px = start_x + dx * t
            py = start_y + dy * t + math.sin(t * math.pi) * 20.0
            stem.append((round(px, 2), round(py, 2)))

        # Arrow wings
        angle = math.atan2(dy, dx)
        wing_len = 35.0
        wing1: List[Tuple[float, float]] = []
        wing2: List[Tuple[float, float]] = []
        for i in range(8):
            t = i / 7.0
            w1x = end_x - math.cos(angle - math.pi / 6) * wing_len * t
            w1y = end_y - math.sin(angle - math.pi / 6) * wing_len * t
            wing1.append((round(w1x, 2), round(w1y, 2)))

            w2x = end_x - math.cos(angle + math.pi / 6) * wing_len * t
            w2y = end_y - math.sin(angle + math.pi / 6) * wing_len * t
            wing2.append((round(w2x, 2), round(w2y, 2)))

        return [stem, wing1, wing2]

    def generate_checkmark_strokes(self, cx: float, cy: float, size: float = 180.0) -> List[List[Tuple[float, float]]]:
        """Generate bold circular ring and decisive checkmark."""
        # Outer circle
        circle: List[Tuple[float, float]] = []
        r = size * 0.85
        for i in range(36):
            ang = (i / 35.0) * 2 * math.pi
            px = cx + r * math.cos(ang)
            py = cy + r * math.sin(ang)
            circle.append((round(px, 2), round(py, 2)))

        # Checkmark: down-left to dip, then sharp up-right
        check: List[Tuple[float, float]] = []
        # First leg
        p_start = (cx - size * 0.45, cy)
        p_dip = (cx - size * 0.1, cy + size * 0.35)
        p_end = (cx + size * 0.5, cy - size * 0.4)

        for i in range(12):
            t = i / 11.0
            px = p_start[0] + (p_dip[0] - p_start[0]) * t
            py = p_start[1] + (p_dip[1] - p_start[1]) * t
            check.append((round(px, 2), round(py, 2)))

        for i in range(16):
            t = i / 15.0
            px = p_dip[0] + (p_end[0] - p_dip[0]) * t
            py = p_dip[1] + (p_end[1] - p_dip[1]) * t
            check.append((round(px, 2), round(py, 2)))

        return [circle, check]

    def generate_balance_scale_strokes(self, cx: float, cy: float, w: float = 340.0, h: float = 240.0) -> List[List[Tuple[float, float]]]:
        """Generate minimalist balance scale indicating cost vs benefit."""
        strokes: List[List[Tuple[float, float]]] = []

        # 1. Base triangular stand
        stand: List[Tuple[float, float]] = []
        half_base = 60.0
        bottom_y = cy + h * 0.4
        apex = (cx, cy - h * 0.1)
        stand.append((cx - half_base, bottom_y))
        stand.append(apex)
        stand.append((cx + half_base, bottom_y))
        stand.append((cx - half_base, bottom_y))
        strokes.append(stand)

        # 2. Main horizontal beam (slightly tilted towards right for high return)
        beam: List[Tuple[float, float]] = []
        half_w = w / 2.0
        tilt_dy = -15.0
        for i in range(18):
            t = i / 17.0
            px = (cx - half_w) + w * t
            py = (cy - h * 0.1 - tilt_dy) + (tilt_dy * 2) * t
            beam.append((round(px, 2), round(py, 2)))
        strokes.append(beam)

        # 3. Left pan (Cost: small pan)
        left_hook = beam[0]
        left_pan_w = 60.0
        left_pan_y = left_hook[1] + 80.0
        left_strings: List[Tuple[float, float]] = [
            (left_hook[0] - left_pan_w / 2, left_pan_y),
            left_hook,
            (left_hook[0] + left_pan_w / 2, left_pan_y),
        ]
        strokes.append(left_strings)
        # Left plate arc
        left_plate = []
        for i in range(10):
            t = i / 9.0
            px = (left_hook[0] - left_pan_w / 2) + left_pan_w * t
            py = left_pan_y + math.sin(t * math.pi) * 8.0
            left_plate.append((round(px, 2), round(py, 2)))
        strokes.append(left_plate)

        # 4. Right pan (Benefit: bigger pan)
        right_hook = beam[-1]
        right_pan_w = 80.0
        right_pan_y = right_hook[1] + 65.0
        right_strings: List[Tuple[float, float]] = [
            (right_hook[0] - right_pan_w / 2, right_pan_y),
            right_hook,
            (right_hook[0] + right_pan_w / 2, right_pan_y),
        ]
        strokes.append(right_strings)
        right_plate = []
        for i in range(12):
            t = i / 11.0
            px = (right_hook[0] - right_pan_w / 2) + right_pan_w * t
            py = right_pan_y + math.sin(t * math.pi) * 12.0
            right_plate.append((round(px, 2), round(py, 2)))
        strokes.append(right_plate)

        return strokes

    def generate_scene_layout(
        self, scene: Dict[str, Any], scene_index: int = 1
    ) -> Tuple[BoardLayout, Image.Image, List[List[Tuple[float, float]]]]:
        """
        Dynamically synthesize a Zen minimalist whiteboard layout and stroke trajectories
        from structured scene metadata.
        """
        board_spec = scene.get("board_spec", {})
        title_text = (
            board_spec.get("board_title")
            or scene.get("kinetic_typography", {}).get("text")
            or scene.get("primary_subject", f"核心要点 {scene_index}")
        )
        accent_color = board_spec.get("underline_accent", "#E28743")

        layout = BoardLayout(
            scene_title=title_text[:14],
            title_underline_color=accent_color,
            canvas_bg_color="#FAF8F5",
            whitespace_ratio=0.70,
        )

        base_canvas = self.create_base_canvas(layout)
        draw = ImageDraw.Draw(base_canvas)

        # Draw stylish hand-drawn underline
        ul_x1 = 90
        ul_y = 130 + 80
        ul_x2 = min(90 + len(layout.scene_title) * 48 + 30, self.width - 90)
        draw.line([(ul_x1, ul_y), (ul_x2, ul_y)], fill=(226, 135, 67), width=6)

        cx = self.width // 2
        cy = 850
        all_strokes: List[List[Tuple[float, float]]] = []

        # Determine diagram mode based on scene metadata, keywords, and semantic vector icons
        board_keywords = board_spec.get("board_keywords", "")
        key_subject = board_spec.get("key_subject", "")
        primary_subject = scene.get("primary_subject", "")
        narration = scene.get("narration_segment", "")
        context_text = f"{title_text} {key_subject} {board_keywords} {primary_subject} {narration}".strip()

        # Prioritize matching based on scene role or keyword semantics
        preferred_priority = None
        if scene_index == 3:
            # Underpinning logic / mechanism: prioritize domain objects like automobile, seatbelt
            preferred_priority = ["automobile", "seatbelt", "heart_pulse"]
        elif scene_index == 4:
            preferred_priority = ["shield_badge"]
        elif scene_index == 5:
            preferred_priority = ["balance_scale", "clock_time"]
        elif scene_index == 6:
            preferred_priority = ["checkmark_circle"]
        elif scene_index == 2:
            preferred_priority = ["crash_warning"]
        elif scene_index == 1:
            preferred_priority = ["seatbelt", "automobile", "heart_pulse"]

        matched_icon = self.svg_library.match_icon(context_text, preferred_priority=preferred_priority)
        svg_strokes = None
        if matched_icon:
            target_w = 420.0 if matched_icon in ("automobile", "balance_scale") else 340.0
            svg_strokes = self.svg_library.get_icon_strokes(
                icon_name_or_keyword=matched_icon,
                center_x=cx,
                center_y=cy - 30,
                target_width=target_w,
            )

        if svg_strokes:
            all_strokes.extend(svg_strokes)
            # Add semantic labels based on matched icon and context
            if matched_icon == "automobile":
                label = "车祸生存概率 +50%" if any(k in context_text for k in ("50%", "一半", "车祸", "撞死")) else "乘员安全防护"
                draw.text((cx, cy + 180), label, fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "碰撞缓冲与生命守护", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "seatbelt":
                draw.text((cx, cy + 180), "上车即系 · 前后排皆系", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "极简动作 守护一生", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "shield_badge":
                draw.text((cx, cy + 190), "权威证据标准", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 240), "循证医学 A 级认证", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "balance_scale":
                draw.text((cx - 150, cy + 140), "成本 ≈ 0", fill=(160, 95, 50), font=self._get_font(28, bold=True), anchor="mm")
                draw.text((cx + 150, cy + 140), "确定收益", fill=(46, 117, 89), font=self._get_font(28, bold=True), anchor="mm")
                draw.text((cx, cy + 220), "极低成本 vs 极高回报", fill=(46, 117, 89), font=self._get_font(32, bold=True), anchor="mm")
            elif matched_icon == "checkmark_circle":
                draw.text((cx, cy + 180), "行动是唯一解", fill=(46, 117, 89), font=self._get_font(36, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "立即执行 · 形成本能习惯", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "crash_warning":
                draw.text((cx, cy + 170), "认知盲区与陷阱", fill=(160, 95, 50), font=self._get_font(32, bold=True), anchor="mm")
                draw.text((cx, cy + 220), "忽视潜在风险代价值千金", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "clock_time":
                draw.text((cx, cy + 180), "仅需 2 秒", fill=(160, 95, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "微小习惯撬动巨大确定性", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "heart_pulse":
                draw.text((cx, cy + 180), "守护生命健康", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "将非受控风险降至最低", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "abdominal_feeling":
                draw.text((cx, cy + 180), "身体预警信号", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "关注内脏微小不适", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon in ("bank-card", "bank_card"):
                draw.text((cx, cy + 180), "资金与财务底线", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "理性消费 严守本金", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "crying_feeling":
                draw.text((cx, cy + 180), "情绪觉察与释放", fill=(160, 95, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "正视悲伤 及时疏导", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "gambling":
                draw.text((cx, cy + 180), "拒绝负期望博弈", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "概率陷阱是确定性亏损", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "happy_feeling":
                draw.text((cx, cy + 180), "正向反馈与喜悦", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "微小胜利铸就长久习惯", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "hospital":
                draw.text((cx, cy + 180), "专业医疗机构介入", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "早筛早查 遵从医嘱", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "aids":
                draw.text((cx, cy + 180), "疾病防控与阻断", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "科学预防 杜绝感染", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "drug":
                draw.text((cx, cy + 180), "药物与疫苗防护", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "遵医嘱规范用药", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "help":
                draw.text((cx, cy + 180), "积极互助与求助", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "及时求援 走出困境", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon in ("medical-examination", "medical_examination"):
                draw.text((cx, cy + 180), "医疗体检与筛查", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "早发现早干预是金标准", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "motor":
                draw.text((cx, cy + 180), "两轮骑行安全第一", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "佩戴头盔 减速慢行", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon in ("metal-bar", "metal_bar"):
                draw.text((cx, cy + 180), "金属与物理防护", fill=(100, 100, 100), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "注意重金属与外力风险", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon in ("radiation-alt", "radiation_alt"):
                draw.text((cx, cy + 180), "远离有害辐射源", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "防护照射 保护机体", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "female":
                draw.text((cx, cy + 180), "女性健康专项守护", fill=(160, 95, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "关爱女性 科学呵护", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "male":
                draw.text((cx, cy + 180), "男性健康特征关注", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "定期筛查 警惕高危习惯", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "children":
                draw.text((cx, cy + 180), "少儿与儿童健康成长", fill=(46, 117, 89), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "筑牢童年安全屏障", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon == "dead":
                draw.text((cx, cy + 180), "致命风险严防死守", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "最大程度降低非受控死因", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            elif matched_icon in ("fall-down", "fall_down"):
                draw.text((cx, cy + 180), "防跌倒与骨骼防护", fill=(180, 50, 50), font=self._get_font(34, bold=True), anchor="mm")
                draw.text((cx, cy + 230), "避免外伤 骨质健康守护", fill=(100, 100, 100), font=self._get_font(26), anchor="mm")
            else:
                lbl = key_subject or title_text[:8]
                draw.text((cx, cy + 180), lbl, fill=(46, 117, 89), font=self._get_font(32, bold=True), anchor="mm")

        elif scene_index == 4 or "证据" in context_text or "徽章" in context_text or "grade" in context_text:
            strokes = self.generate_shield_strokes(cx=cx, cy=cy, w=260, h=320)
            all_strokes.extend(strokes)
            draw.text((cx, cy + 220), "权威证据标准", fill=(46, 117, 89), font=self._get_font(32, bold=True), anchor="mm")

        elif scene_index == 3 or "逻辑" in context_text or "机理" in context_text or "箭头" in context_text:
            left_x = cx - 220
            right_x = cx + 220
            c1 = []
            for i in range(25):
                ang = (i / 24.0) * 2 * math.pi
                c1.append((round(left_x + 55 * math.cos(ang), 2), round(cy + 55 * math.sin(ang), 2)))
            all_strokes.append(c1)
            c2 = []
            for i in range(25):
                ang = (i / 24.0) * 2 * math.pi
                c2.append((round(right_x + 55 * math.cos(ang), 2), round(cy + 55 * math.sin(ang), 2)))
            all_strokes.append(c2)
            arrow = self.generate_flow_arrow_strokes(left_x + 65, cy, right_x - 65, cy)
            all_strokes.extend(arrow)
            draw.text((left_x, cy), "原因", fill=(160, 95, 50), font=self._get_font(28, bold=True), anchor="mm")
            draw.text((right_x, cy), "结果", fill=(46, 117, 89), font=self._get_font(28, bold=True), anchor="mm")
            draw.text((cx, cy + 130), "底层因果逻辑", fill=(60, 60, 60), font=self._get_font(30, bold=True), anchor="mm")

        elif scene_index == 5 or "成本" in context_text or "天平" in context_text or "收益" in context_text:
            scale_strokes = self.generate_balance_scale_strokes(cx=cx, cy=cy - 20, w=380, h=260)
            all_strokes.extend(scale_strokes)
            draw.text((cx - 150, cy + 130), "成本 ≈ 0", fill=(160, 95, 50), font=self._get_font(28, bold=True), anchor="mm")
            draw.text((cx + 150, cy + 130), "确定收益", fill=(46, 117, 89), font=self._get_font(28, bold=True), anchor="mm")

        elif scene_index == 6 or "行动" in context_text or "对勾" in context_text or "解" in context_text:
            check_strokes = self.generate_checkmark_strokes(cx=cx, cy=cy, size=150)
            all_strokes.extend(check_strokes)
            draw.text((cx, cy + 200), "立即行动", fill=(46, 117, 89), font=self._get_font(36, bold=True), anchor="mm")

        elif scene_index == 2 or "误区" in context_text or "盲区" in context_text or "警示" in context_text:
            box = self.generate_rounded_box_strokes(cx, cy, w=320, h=200, radius=24)
            all_strokes.extend(box)
            q_stem = []
            for i in range(15):
                t = i / 14.0
                ang = -math.pi / 2.0 + t * 1.3 * math.pi
                q_stem.append((round(cx + 25 * math.cos(ang), 2), round(cy - 40 + 25 * math.sin(ang), 2)))
            all_strokes.append(q_stem)
            all_strokes.append([(round(cx, 2), round(cy + 15, 2)), (round(cx, 2), round(cy + 35, 2))])
            draw.text((cx, cy + 150), "认知盲区与陷阱", fill=(160, 95, 50), font=self._get_font(30, bold=True), anchor="mm")

        else:
            box = self.generate_rounded_box_strokes(cx, cy, w=300, h=160, radius=28)
            cursor = self.generate_cursor_strokes(tip_x=cx + 70, tip_y=cy + 40, size=50)
            all_strokes.extend(box)
            all_strokes.extend(cursor)
            kw_label = board_spec.get("key_subject") or title_text[:6]
            draw.text((cx - 20, cy), kw_label, fill=(46, 117, 89), font=self._get_font(32, bold=True), anchor="mm")

        return layout, base_canvas, all_strokes

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

