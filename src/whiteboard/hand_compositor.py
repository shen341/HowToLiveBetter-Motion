"""Hand Compositor simulating realistic pen movement, soft drop shadow, and stroke reveal."""

import math
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from src.whiteboard.layout_engine import BoardLayout, WhiteboardLayoutEngine


@dataclass
class HandStroke:
    """A single continuous stroke segment with timing and geometry."""
    points: List[Tuple[float, float]]
    start_time: float
    end_time: float
    item_id: str = ""
    stroke_color: Tuple[int, int, int] = (30, 30, 30)
    stroke_width: int = 4
    is_drawing: bool = True  # If False, transit movement with pen lifted


class HandCompositor:
    """Simulates realistic human hand holding a stylus with dynamic shadow and trajectory interpolation."""

    def __init__(self, width: int = 1080, height: int = 1920):
        self.width = width
        self.height = height
        self.hand_img, self.hand_shadow, self.tip_offset = self._load_or_create_hand_asset()

    def _load_or_create_hand_asset(self) -> Tuple[Image.Image, Image.Image, Tuple[int, int]]:
        """Load external hand transparent PNG or procedurally generate high-resolution hand asset."""
        candidate = os.path.join("assets", "whiteboard", "hand_stylus.png")
        if os.path.exists(candidate):
            try:
                img = Image.open(candidate).convert("RGBA")
                shadow = self._build_shadow(img)
                return img, shadow, (75, 45)
            except Exception:
                pass

        # Pure elegant minimalist stylus pen (no human hand overlay)
        pen_w, pen_h = 260, 340
        img = Image.new("RGBA", (pen_w, pen_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Pen nib anchor: Top-left of the asset
        tip_x, tip_y = 25, 25

        # 1. Dark fine writing nib
        nib_pts = [
            (tip_x, tip_y),
            (tip_x + 5, tip_y + 12),
            (tip_x + 12, tip_y + 5),
        ]
        draw.polygon(nib_pts, fill=(24, 24, 28, 255))

        # 2. Conical collar transition
        cone_pts = [
            (tip_x + 5, tip_y + 12),
            (tip_x + 12, tip_y + 5),
            (tip_x + 24, tip_y + 17),
            (tip_x + 17, tip_y + 24),
        ]
        draw.polygon(cone_pts, fill=(185, 192, 202, 255))

        # 3. Metallic accent ring
        ring_pts = [
            (tip_x + 17, tip_y + 24),
            (tip_x + 24, tip_y + 17),
            (tip_x + 29, tip_y + 22),
            (tip_x + 22, tip_y + 29),
        ]
        draw.polygon(ring_pts, fill=(65, 72, 84, 255))

        # 4. Long sleek stylus barrel angled down-right (~45 deg)
        barrel_pts = [
            (tip_x + 22, tip_y + 29),
            (tip_x + 29, tip_y + 22),
            (tip_x + 195, tip_y + 188),
            (tip_x + 188, tip_y + 195),
        ]
        # Soft metallic white/silver fill
        draw.polygon(barrel_pts, fill=(244, 246, 250, 255))
        # Subtle barrel boundary outline
        draw.line([(tip_x + 22, tip_y + 29), (tip_x + 188, tip_y + 195)], fill=(160, 168, 178, 220), width=1)
        draw.line([(tip_x + 29, tip_y + 22), (tip_x + 195, tip_y + 188)], fill=(180, 188, 198, 220), width=1)

        # 5. Lengthwise specular highlight streak along top ridge
        draw.line(
            [(tip_x + 26, tip_y + 25), (tip_x + 192, tip_y + 191)],
            fill=(255, 255, 255, 240),
            width=3
        )

        # 6. Rounded top cap / end button
        cap_pts = [
            (tip_x + 188, tip_y + 195),
            (tip_x + 195, tip_y + 188),
            (tip_x + 208, tip_y + 201),
            (tip_x + 201, tip_y + 208),
        ]
        draw.polygon(cap_pts, fill=(210, 216, 225, 255))
        draw.line([(tip_x + 201, tip_y + 208), (tip_x + 208, tip_y + 201)], fill=(140, 148, 158, 255), width=2)

        shadow = self._build_shadow(img)
        return img, shadow, (tip_x, tip_y)

    def _build_shadow(self, pen_rgba: Image.Image) -> Image.Image:
        """Create a soft diffuse drop-shadow from the pen alpha channel."""
        r, g, b, a = pen_rgba.split()
        shadow_alpha = a.point(lambda p: int(p * 0.28))
        shadow_img = Image.merge("RGBA", (
            Image.new("L", pen_rgba.size, 20),
            Image.new("L", pen_rgba.size, 20),
            Image.new("L", pen_rgba.size, 25),
            shadow_alpha
        ))
        return shadow_img.filter(ImageFilter.GaussianBlur(radius=8))


    def plan_strokes_from_layout(
        self, layout: BoardLayout, total_duration: float, draw_ratio: float = 0.72
    ) -> List[HandStroke]:
        """Convert board layout elements into time-synchronized hand strokes."""
        # Draw time vs contemplative pause time
        active_draw_time = total_duration * draw_ratio
        all_raw_strokes = []

        # 1. Underline stroke first (Quick intro hook)
        title_underline = [
            (90 + i * 6.0, 210 + math.sin(i * 0.18) * 2.5) for i in range(40)
        ]
        all_raw_strokes.append({
            "points": title_underline,
            "color": (226, 135, 67),
            "width": 6,
            "item_id": "title_underline"
        })

        # 2. Item strokes
        for item in layout.items:
            for s in item.strokes:
                if len(s) >= 2:
                    all_raw_strokes.append({
                        "points": s,
                        "color": (35, 35, 35),
                        "width": 4,
                        "item_id": item.item_id
                    })

        if not all_raw_strokes:
            return []

        # Time allocation per stroke based on path length
        stroke_lengths = []
        for s in all_raw_strokes:
            pts = s["points"]
            length = sum(
                math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
                for i in range(1, len(pts))
            )
            stroke_lengths.append(max(length, 10.0))

        total_len = sum(stroke_lengths)
        strokes: List[HandStroke] = []
        current_t = 0.3  # Short 0.3s breath at start

        transit_gap = 0.08  # Fast 80ms hand transit between strokes

        for idx, s in enumerate(all_raw_strokes):
            duration_for_stroke = (stroke_lengths[idx] / total_len) * (active_draw_time - 0.5)
            duration_for_stroke = max(0.12, duration_for_stroke)

            start_t = current_t
            end_t = start_t + duration_for_stroke

            strokes.append(
                HandStroke(
                    points=s["points"],
                    start_time=start_t,
                    end_time=end_t,
                    item_id=s.get("item_id", ""),
                    stroke_color=s["color"],
                    stroke_width=s["width"],
                    is_drawing=True
                )
            )

            current_t = end_t + transit_gap

        return strokes

    def interpolate_stroke_point(
        self, points: List[Tuple[float, float]], progress: float
    ) -> Tuple[float, float]:
        """Interpolate (x, y) along a multi-point polyline at given progress [0.0, 1.0]."""
        if not points:
            return (0.0, 0.0)
        if len(points) == 1 or progress <= 0.0:
            return points[0]
        if progress >= 1.0:
            return points[-1]

        # Calculate segments
        seg_lens = [
            math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
            for i in range(1, len(points))
        ]
        total_len = sum(seg_lens)
        if total_len <= 1e-4:
            return points[0]

        target_dist = progress * total_len
        accum = 0.0

        for i, s_len in enumerate(seg_lens):
            if accum + s_len >= target_dist:
                seg_prog = (target_dist - accum) / max(s_len, 1e-4)
                p1 = points[i]
                p2 = points[i + 1]
                return (
                    p1[0] + (p2[0] - p1[0]) * seg_prog,
                    p1[1] + (p2[1] - p1[1]) * seg_prog,
                )
            accum += s_len

        return points[-1]

    def render_frame_at_time(
        self,
        t: float,
        duration: float,
        layout: BoardLayout,
        strokes: List[HandStroke],
        base_canvas: Image.Image,
        static_completed_board: Image.Image,
    ) -> np.ndarray:
        """Render frame array at timestamp t with incremental ink drawing and hand overlay."""
        # 1. Base frame starts with paper canvas (with pre-rendered title)
        frame = base_canvas.copy()
        draw = ImageDraw.Draw(frame)

        # Track completed items to render their fills & text labels
        item_completion = {}
        for s in strokes:
            if s.item_id:
                item_completion[s.item_id] = max(item_completion.get(s.item_id, 0.0), s.end_time)

        layout_eng = WhiteboardLayoutEngine(self.width, self.height)
        for item in layout.items:
            comp_t = item_completion.get(item.item_id, 0.0)
            if t >= comp_t and comp_t > 0:
                layout_eng.render_item_fill_and_labels(draw, item)

        last_pen_pos = (self.width + 200, self.height + 200)
        is_hand_active = False

        # If drawing phase completed, smoothly slide hand out towards bottom-right
        draw_end_t = strokes[-1].end_time if strokes else duration * 0.75

        # 2. Draw all strokes up to time t
        for s in strokes:
            if t < s.start_time:
                continue

            elif t >= s.end_time:
                # Fully drawn stroke
                if len(s.points) >= 2:
                    draw.line(s.points, fill=s.stroke_color, width=s.stroke_width, joint="curve")

            else:
                # Actively drawing stroke!
                is_hand_active = True
                prog = (t - s.start_time) / max(s.end_time - s.start_time, 0.01)
                prog = min(max(prog, 0.0), 1.0)

                # Segment of points up to prog
                curr_tip = self.interpolate_stroke_point(s.points, prog)
                last_pen_pos = curr_tip

                # Micro-jitter for organic human pen contact (±0.6px)
                jitter_x = math.sin(t * 70.0) * 0.6
                jitter_y = math.cos(t * 85.0) * 0.6
                last_pen_pos = (curr_tip[0] + jitter_x, curr_tip[1] + jitter_y)

                # Draw partial points
                partial_points = []
                for p in s.points:
                    if math.hypot(p[0] - curr_tip[0], p[1] - curr_tip[1]) > 1.0:
                        partial_points.append(p)
                    else:
                        break
                partial_points.append(curr_tip)
                if len(partial_points) >= 2:
                    draw.line(partial_points, fill=s.stroke_color, width=s.stroke_width, joint="curve")

        # 3. Progressive Reveal of Completed Elements
        if t >= draw_end_t:
            # Cross-fade to finalized static board for pristine final contemplation
            blend_p = min(max((t - draw_end_t) / 0.5, 0.0), 1.0)
            if blend_p > 0.0:
                frame = Image.blend(frame, static_completed_board, blend_p)
                draw = ImageDraw.Draw(frame)

        # 4. Hand Overlay Rendering
        if t < draw_end_t + 0.6:
            if not is_hand_active:
                # Hand is in transit between strokes or exiting
                if t < draw_end_t:
                    # Transit: Find next upcoming stroke
                    next_s = next((st for st in strokes if st.start_time > t), None)
                    prev_s = next((st for st in reversed(strokes) if st.end_time <= t), None)
                    if prev_s and next_s:
                        transit_p = (t - prev_s.end_time) / max(next_s.start_time - prev_s.end_time, 0.01)
                        # Smooth cubic easing
                        transit_p = min(max(transit_p, 0.0), 1.0)
                        smooth_p = transit_p * transit_p * (3.0 - 2.0 * transit_p)
                        p_from = prev_s.points[-1]
                        p_to = next_s.points[0]
                        last_pen_pos = (
                            p_from[0] + (p_to[0] - p_from[0]) * smooth_p,
                            p_from[1] + (p_to[1] - p_from[1]) * smooth_p - 15.0 * math.sin(transit_p * math.pi),
                        )
                else:
                    # Exit phase: Slide down-right
                    exit_p = (t - draw_end_t) / 0.6
                    exit_p = min(max(exit_p, 0.0), 1.0)
                    smooth_p = exit_p * exit_p
                    last_pen_pos = (
                        strokes[-1].points[-1][0] + smooth_p * 500,
                        strokes[-1].points[-1][1] + smooth_p * 600,
                    )

            # Paste hand and shadow
            tip_x, tip_y = self.tip_offset
            hand_left = int(last_pen_pos[0] - tip_x)
            hand_top = int(last_pen_pos[1] - tip_y)

            # Drop shadow offset (+8, +10)
            frame.paste(self.hand_shadow, (hand_left + 8, hand_top + 10), self.hand_shadow)
            # Pen foreground
            frame.paste(self.hand_img, (hand_left, hand_top), self.hand_img)


        return np.array(frame)

    def create_whiteboard_clip(
        self,
        duration: float,
        layout: Optional[BoardLayout] = None,
        engine: Optional[WhiteboardLayoutEngine] = None,
    ):
        """Create a MoviePy VideoClip rendering the dynamic hand-drawn whiteboard scene."""
        from moviepy import VideoClip

        eng = engine or WhiteboardLayoutEngine(self.width, self.height)
        lay = layout or eng.build_sample_layout()

        base_canvas = eng.create_base_canvas(lay)
        static_board = eng.render_static_board(lay)
        strokes = self.plan_strokes_from_layout(lay, total_duration=duration)

        def make_frame(t):
            return self.render_frame_at_time(
                t=t,
                duration=duration,
                layout=lay,
                strokes=strokes,
                base_canvas=base_canvas,
                static_completed_board=static_board,
            )

        return VideoClip(make_frame, duration=duration)
