"""Stream Whiteboard Animation Renderer for HowToLiveBetter-Motion.
Integrates semantic mask partitioning with continuous ink-and-color stream drawing.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image


def _imread_any(path: str | Path, flags: int = cv2.IMREAD_COLOR) -> Optional[np.ndarray]:
    """Read an image supporting non-ASCII Windows paths safely."""
    path_str = str(path)
    if not os.path.exists(path_str):
        return None
    try:
        raw = np.fromfile(path_str, dtype=np.uint8)
        if raw.size == 0:
            return None
        return cv2.imdecode(raw, flags)
    except Exception:
        return None


def _hex_to_bgr(hex_color: str) -> np.ndarray:
    """Convert hex string (e.g. #F5EBD7 or #FAF8F5) to BGR uint8 array."""
    digits = hex_color.lstrip("#")
    if len(digits) != 6:
        return np.array([245, 248, 250], dtype=np.uint8)
    r = int(digits[0:2], 16)
    g = int(digits[2:4], 16)
    b = int(digits[4:6], 16)
    return np.array([b, g, r], dtype=np.uint8)


@dataclass(frozen=True)
class StreamWhiteboardConfig:
    """Configuration parameters for stream whiteboard animation."""
    fps: int = 30
    grid_edge: int = 10
    cap_long_edge: int = 1920
    ink_weight: int = 2
    color_weight: int = 1
    gaze_seconds: float = 0.5
    ink_threshold: int = 140
    ink_reveal_radius: int = 12
    target_hand_height: int = 480
    tip_anchor_x: float = 0.0
    tip_anchor_y: float = 0.0
    canvas_hex: str = "#FAF8F5"
    match_bg: bool = True
    match_bg_threshold: int = 28
    color_fill: str = "contour-wipe"


def apply_pen_brand_text(hand_rgba: np.ndarray, brand_text: Optional[str] = None) -> np.ndarray:
    """
    Dynamically customize the brand text on the white pen shaft.
    Rotates barrel to horizontal, cleanly in-paints the cylindrical gradient,
    renders brand_text using Microsoft YaHei / SimHei, and rotates back.
    """
    if brand_text is None:
        try:
            from src.config import WHITEBOARD_PEN_BRAND_TEXT
            brand_text = WHITEBOARD_PEN_BRAND_TEXT
        except Exception:
            brand_text = os.getenv("WHITEBOARD_PEN_BRAND_TEXT", "小生杂货铺")

    orig = hand_rgba.copy()
    h_orig, w_orig = orig.shape[:2]
    # Check if image matches standard drawing-hand.png geometry
    if h_orig < 1000 or w_orig < 800:
        return orig

    angle = 40.70607
    center = (596.8, 474.1)

    # 1. Forward rotation
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(orig, M, (w_orig, h_orig), flags=cv2.INTER_LANCZOS4)

    crop_y0 = int(center[1] - 100)
    crop_y1 = int(center[1] + 100)
    crop_x0 = int(center[0] - 350)
    crop_x1 = int(center[0] + 350)

    crop = rotated[crop_y0:crop_y1, crop_x0:crop_x1, :3].copy()

    # 2. Seamlessly clean pen barrel cylinder
    c_left = crop[50:148, 105].astype(np.float32)
    c_right = crop[50:148, 558].astype(np.float32)
    x_start = 106
    x_end = 556
    w_span = float(x_end - x_start)

    for x in range(x_start, x_end):
        alpha = (x - x_start) / w_span
        col_x = c_left * (1.0 - alpha) + c_right * alpha
        crop[50:148, x] = col_x.astype(np.uint8)

    # 3. If brand text provided, render text onto the barrel
    if brand_text and brand_text.strip():
        pil_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        font = None
        for font_candidate in ['C:/Windows/Fonts/msyhbd.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/msyh.ttc']:
            if os.path.exists(font_candidate):
                try:
                    font = ImageFont.truetype(font_candidate, 58)
                    break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()

        chars = list(brand_text.strip())
        char_widths = [font.getbbox(c)[2] - font.getbbox(c)[0] for c in chars]
        spacing = max(8, min(24, int((400 - sum(char_widths)) / max(1, len(chars) - 1))))
        total_w = sum(char_widths) + spacing * (len(chars) - 1)

        start_x = int(330 - total_w / 2)
        cur_x = start_x
        base_y = int(98 - 58 / 2)

        for c, cw in zip(chars, char_widths):
            draw.text((cur_x, base_y), c, font=font, fill=(26, 26, 30))
            cur_x += cw + spacing

        crop = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    rotated[crop_y0:crop_y1, crop_x0:crop_x1, :3] = crop

    # 4. Inverse rotation and composite with soft mask
    M_inv = cv2.getRotationMatrix2D(center, -angle, 1.0)
    new_full = cv2.warpAffine(rotated, M_inv, (w_orig, h_orig), flags=cv2.INTER_LANCZOS4)

    mask_rot = np.zeros(orig.shape[:2], dtype=np.uint8)
    mask_rot[crop_y0+50:crop_y0+148, crop_x0+106:crop_x0+556] = 255
    mask_orig = cv2.warpAffine(mask_rot, M_inv, (w_orig, h_orig), flags=cv2.INTER_LINEAR)
    mask_alpha = (cv2.GaussianBlur(mask_orig, (5, 5), 0).astype(np.float32) / 255.0)[:, :, None]

    final_hand = (new_full.astype(np.float32) * mask_alpha + orig.astype(np.float32) * (1.0 - mask_alpha)).astype(np.uint8)
    final_hand[:, :, 3] = orig[:, :, 3]
    return final_hand


class TipOverlay:
    """Manages hand or stylus overlay rendering with alpha blending and dynamic tip anchor."""

    def __init__(
        self,
        hand_rgba: np.ndarray,
        target_height: int = 480,
        tip_anchor_x: float = 0.0,
        tip_anchor_y: float = 0.0,
    ):
        h, w = hand_rgba.shape[:2]
        scale = max(0.1, target_height / float(h))
        new_w = max(10, int(round(w * scale)))
        new_h = max(10, int(round(h * scale)))

        self.hand_resized = cv2.resize(hand_rgba, (new_w, new_h), interpolation=cv2.INTER_AREA)
        self.bgr = self.hand_resized[:, :, :3]
        self.alpha = (self.hand_resized[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
        self.anchor_x = int(round(new_w * tip_anchor_x))
        self.anchor_y = int(round(new_h * tip_anchor_y))

    @classmethod
    def from_file_or_fallback(
        cls,
        hand_path: Optional[str | Path] = None,
        target_height: int = 480,
        anchor_x: float = 0.0,
        anchor_y: float = 0.0,
        brand_text: Optional[str] = None,
    ) -> TipOverlay:
        """Load external PNG, apply dynamic brand text from config/env, or generate procedural stylus."""
        candidates = []
        if hand_path:
            candidates.append(Path(hand_path))
        candidates.extend([
            Path("assets/whiteboard/drawing-hand.png"),
            Path("assets/drawing-hand.png"),
            Path("assets/whiteboard/hand_stylus.png"),
        ])

        for c in candidates:
            if c.exists():
                img = _imread_any(c, cv2.IMREAD_UNCHANGED)
                if img is not None and img.ndim == 3 and img.shape[2] == 4:
                    try:
                        img = apply_pen_brand_text(img, brand_text=brand_text)
                    except Exception:
                        pass
                    return cls(img, target_height, tip_anchor_x=anchor_x, tip_anchor_y=anchor_y)

        # Procedural minimalist pen asset fallback
        pw, ph = 240, 360
        procedural = np.zeros((ph, pw, 4), dtype=np.uint8)
        # Draw dark pen body angled towards top-left (tip at 10, 10)
        cv2.line(procedural, (10, 10), (180, 320), (35, 38, 42, 255), thickness=16, lineType=cv2.LINE_AA)
        cv2.line(procedural, (10, 10), (180, 320), (180, 185, 190, 255), thickness=6, lineType=cv2.LINE_AA)
        cv2.circle(procedural, (10, 10), 6, (20, 20, 24, 255), -1, lineType=cv2.LINE_AA)
        return cls(procedural, target_height, tip_anchor_x=10.0 / pw, tip_anchor_y=10.0 / ph)

    def stamp(self, canvas_bgr: np.ndarray, tip_x: int, tip_y: int):
        """Alpha-blend hand asset onto canvas so its nib lands exactly at (tip_x, tip_y)."""
        ch, cw = canvas_bgr.shape[:2]
        hh, hw = self.hand_resized.shape[:2]

        top_left_x = tip_x - self.anchor_x
        top_left_y = tip_y - self.anchor_y

        x0 = max(0, top_left_x)
        y0 = max(0, top_left_y)
        x1 = min(cw, top_left_x + hw)
        y1 = min(ch, top_left_y + hh)

        if x0 >= x1 or y0 >= y1:
            return

        hx0 = x0 - top_left_x
        hy0 = y0 - top_left_y
        hx1 = hx0 + (x1 - x0)
        hy1 = hy0 + (y1 - y0)

        canvas_crop = canvas_bgr[y0:y1, x0:x1]
        hand_crop = self.bgr[hy0:hy1, hx0:hx1]
        alpha_crop = self.alpha[hy0:hy1, hx0:hx1]

        blended = (hand_crop * alpha_crop + canvas_crop * (1.0 - alpha_crop)).astype(np.uint8)
        canvas_bgr[y0:y1, x0:x1] = blended


def scaled_rect(region: Dict[str, Any], sx: float, sy: float, out_w: int, out_h: int) -> Tuple[int, int, int, int]:
    """Scale annotation canvas bounding box to target video coordinates [x0, y0, x1, y1]."""
    x0 = max(0, min(out_w, int(round(region.get("x", 0) * sx))))
    y0 = max(0, min(out_h, int(round(region.get("y", 0) * sy))))
    x1 = max(0, min(out_w, int(round((region.get("x", 0) + region.get("width", 0)) * sx))))
    y1 = max(0, min(out_h, int(round((region.get("y", 0) + region.get("height", 0)) * sy))))
    return x0, y0, x1, y1


class StreamWhiteboardRenderer:
    """Core renderer executing semantic mask partitioning and continuous ink/color stream drawing."""

    def __init__(
        self,
        image_bgr: np.ndarray,
        annotation: Dict[str, Any],
        config: Optional[StreamWhiteboardConfig] = None,
        hand_path: Optional[str | Path] = None,
        target_size: Optional[Tuple[int, int]] = None,
    ):
        self.cfg = config or StreamWhiteboardConfig()
        self.ann = annotation
        self.canvas_bgr = _hex_to_bgr(self.cfg.canvas_hex)

        # Output dimensions
        if target_size:
            self.out_w, self.out_h = target_size
        else:
            cw = annotation.get("canvas", {}).get("width", image_bgr.shape[1])
            ch = annotation.get("canvas", {}).get("height", image_bgr.shape[0])
            self.out_w, self.out_h = cw, ch

        # Ensure dimensions are even for video encoding
        self.out_w = (self.out_w // 2) * 2
        self.out_h = (self.out_h // 2) * 2

        # Scale factors from annotation canvas to output video
        ann_cw = annotation.get("canvas", {}).get("width", self.out_w)
        ann_ch = annotation.get("canvas", {}).get("height", self.out_h)
        self.sx = self.out_w / float(max(1, ann_cw))
        self.sy = self.out_h / float(max(1, ann_ch))

        # Color image resized to output dimensions
        self.color_img = cv2.resize(image_bgr, (self.out_w, self.out_h), interpolation=cv2.INTER_AREA)

        # Background matching: replace paper background with uniform canvas color
        if self.cfg.match_bg:
            self._harmonize_background()

        # Grayscale and adaptive threshold map for ink extraction
        gray = cv2.cvtColor(self.color_img, cv2.COLOR_BGR2GRAY)
        self.thresh_map = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10
        )
        self.ink_pixels = self.thresh_map < self.cfg.ink_threshold

        # Persistent canvas initialized with warm paper background
        self.drawn = np.empty((self.out_h, self.out_w, 3), dtype=np.uint8)
        self.drawn[...] = self.canvas_bgr

        # Tip overlay
        self.tip = TipOverlay.from_file_or_fallback(
            hand_path=hand_path,
            target_height=self.cfg.target_hand_height,
            anchor_x=self.cfg.tip_anchor_x,
            anchor_y=self.cfg.tip_anchor_y,
        )

    def _harmonize_background(self):
        """Sample corners and blend image background with canvas background."""
        img = self.color_img
        h, w = img.shape[:2]
        m = max(4, min(h, w) // 40)
        samples = [img[:m, :m], img[:m, -m:], img[-m:, :m], img[-m:, -m:]]
        bg = np.median(np.concatenate([s.reshape(-1, 3) for s in samples]), axis=0)
        diff = np.abs(img.astype(np.int16) - bg.astype(np.int16)).sum(axis=2)
        mask = diff < self.cfg.match_bg_threshold
        img[mask] = self.canvas_bgr

    def calculate_allowed_mask(self, element: Dict[str, Any], later_elements: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate invariant allowed mask = region - later_regions - protectedRegions."""
        mask = np.zeros((self.out_h, self.out_w), dtype=bool)
        x0, y0, x1, y1 = scaled_rect(element.get("region", {}), self.sx, self.sy, self.out_w, self.out_h)
        mask[y0:y1, x0:x1] = True

        for later in later_elements:
            lx0, ly0, lx1, ly1 = scaled_rect(later.get("region", {}), self.sx, self.sy, self.out_w, self.out_h)
            mask[ly0:ly1, lx0:lx1] = False

        for prot in element.get("reveal", {}).get("protectedRegions", []):
            px0, py0, px1, py1 = scaled_rect(prot, self.sx, self.sy, self.out_w, self.out_h)
            mask[py0:py1, px0:px1] = False

        return mask

    def extract_ink_path(self, allowed_mask: np.ndarray) -> List[Tuple[int, int]]:
        """Extract continuous ink stroke trajectory points inside allowed_mask."""
        active = self.ink_pixels & allowed_mask
        ys, xs = np.where(active)
        if len(xs) == 0:
            # Fallback to region center if no ink detected
            y_idx, x_idx = np.where(allowed_mask)
            if len(x_idx) == 0:
                return [(self.out_w // 2, self.out_h // 2)]
            return [(int(np.mean(x_idx)), int(np.mean(y_idx)))]

        # Sample points with step spacing
        points = []
        step = max(4, self.cfg.grid_edge)
        sampled_indices = np.random.choice(len(xs), size=min(len(xs), 200), replace=False)
        pts = np.column_stack((xs[sampled_indices], ys[sampled_indices]))

        # Greedy nearest neighbor ordering
        if len(pts) > 0:
            visited = np.zeros(len(pts), dtype=bool)
            curr = 0
            visited[curr] = True
            points.append((int(pts[curr, 0]), int(pts[curr, 1])))

            for _ in range(len(pts) - 1):
                last_pt = pts[curr]
                dists = np.sum((pts - last_pt) ** 2, axis=1).astype(np.float64)
                dists[visited] = np.inf
                next_idx = int(np.argmin(dists))
                if np.isinf(dists[next_idx]):
                    break
                visited[next_idx] = True
                curr = next_idx
                points.append((int(pts[curr, 0]), int(pts[curr, 1])))

        return points if points else [(self.out_w // 2, self.out_h // 2)]

    def render_to_video(self, output_path: str) -> str:
        """Render full whiteboard video with mask sequencing, stream ink, color reveal, and hand overlay."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        elements = sorted(self.ann.get("elements", []), key=lambda e: e.get("sequence", 0))
        total_duration_ms = self.ann.get("sceneDurationMs", 5000)
        fps = self.cfg.fps
        total_frames = max(1, int(round((total_duration_ms / 1000.0) * fps)))

        # Video writer setup
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (self.out_w, self.out_h))

        # Timing budget per element
        if elements:
            per_elem_ms = (total_duration_ms - int(self.cfg.gaze_seconds * 1000)) / float(len(elements))
        else:
            per_elem_ms = 0

        current_frame = 0

        try:
            for i, elem in enumerate(elements):
                later_elements = elements[i + 1:]
                allowed_mask = self.calculate_allowed_mask(elem, later_elements)

                # Element duration
                elem_duration_ms = elem.get("reveal", {}).get("durationMs", per_elem_ms)
                elem_frames = max(2, int(round((elem_duration_ms / 1000.0) * fps)))

                # Split frames: ink (2/3) vs color (1/3)
                w_total = self.cfg.ink_weight + self.cfg.color_weight
                ink_frames = max(1, int(round(elem_frames * (self.cfg.ink_weight / float(w_total)))))
                color_frames = max(1, elem_frames - ink_frames)

                # 1. Phase 1: Stream Ink Drawing
                ink_path = self.extract_ink_path(allowed_mask)
                n_pts = len(ink_path)

                for f_idx in range(ink_frames):
                    p_idx = int(round(f_idx * (n_pts - 1) / max(1, ink_frames - 1)))
                    tx, ty = ink_path[p_idx]

                    # Progressive ink reveal circle around tip
                    r = self.cfg.ink_reveal_radius
                    y0 = max(0, ty - r)
                    y1 = min(self.out_h, ty + r)
                    x0 = max(0, tx - r)
                    x1 = min(self.out_w, tx + r)

                    local_mask = allowed_mask[y0:y1, x0:x1] & self.ink_pixels[y0:y1, x0:x1]
                    # Paint dark sketch lines
                    self.drawn[y0:y1, x0:x1][local_mask] = (30, 30, 32)

                    # Snapshot with hand overlay
                    snap = self.drawn.copy()
                    self.tip.stamp(snap, tx, ty)
                    writer.write(snap)
                    current_frame += 1

                # Fully reveal ink lines in this allowed mask at end of ink phase
                self.drawn[allowed_mask & self.ink_pixels] = (30, 30, 32)

                # 2. Phase 2: Color Fill (Contour Wipe / Top-to-Bottom reveal)
                rx0, ry0, rx1, ry1 = scaled_rect(elem.get("region", {}), self.sx, self.sy, self.out_w, self.out_h)
                h_reg = max(1, ry1 - ry0)

                for f_idx in range(color_frames):
                    prog = (f_idx + 1) / float(color_frames)
                    curr_y = ry0 + int(round(h_reg * prog))

                    # Sweep hand horizontally across current wipe line
                    sweep_x = rx0 + int(round((rx1 - rx0) * (0.5 + 0.5 * math.sin(f_idx * 0.8))))
                    sweep_y = min(self.out_h - 1, curr_y)

                    # Reveal original full color pixels up to curr_y
                    color_mask = allowed_mask.copy()
                    color_mask[curr_y:, :] = False
                    self.drawn[color_mask] = self.color_img[color_mask]

                    snap = self.drawn.copy()
                    self.tip.stamp(snap, sweep_x, sweep_y)
                    writer.write(snap)
                    current_frame += 1

                # Fully reveal color in this element's allowed mask
                self.drawn[allowed_mask] = self.color_img[allowed_mask]

            # 3. Gaze hold phase: show complete drawn scene without hand
            remaining_frames = max(1, total_frames - current_frame)
            final_frame = self.drawn.copy()
            for _ in range(remaining_frames):
                writer.write(final_frame)
        finally:
            writer.release()

        return output_path
