"""Unit tests for Smooth Whiteboard Animation Engine (TASK-5.4)."""

import os
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

from src.prompt_builder import (
    STYLE_RECIPES,
    build_whiteboard_system_prompt,
    build_whiteboard_user_prompt,
    get_style_recipe,
)
from src.local_image_client import STYLE_LORA_PRESETS
from src.whiteboard.hand_compositor import HandCompositor, HandStroke
from src.whiteboard.layout_engine import BoardItem, BoardLayout, WhiteboardLayoutEngine


class TestWhiteboardStyleAndPrompts(unittest.TestCase):
    """Test w1_whiteboard style card and specialized prompt builder functions."""

    def test_w1_whiteboard_style_card_registered(self):
        """Verify w1_whiteboard style card is registered in STYLE_RECIPES and STYLE_LORA_PRESETS."""
        self.assertIn("w1_whiteboard", STYLE_RECIPES)
        recipe = get_style_recipe("w1_whiteboard")
        self.assertIn("极简", recipe["name"])
        self.assertIn("留白", recipe["description"])
        self.assertIn("ample negative space", recipe["keywords"])
        self.assertIn("crowded", recipe["negative"])

        self.assertIn("w1_whiteboard", STYLE_LORA_PRESETS)
        lora = STYLE_LORA_PRESETS["w1_whiteboard"]
        self.assertIn("safetensors", lora["lora_name"])
        self.assertIn("ample negative space", lora["trigger"])

    def test_build_whiteboard_prompts(self):
        """Verify whiteboard system and user prompts enforce zen negative space and single-subject rules."""
        sys_prompt = build_whiteboard_system_prompt(scene_count=6)
        self.assertIn("留白哲学", sys_prompt)
        self.assertIn("60%~75%", sys_prompt)
        self.assertIn("1~2 个最关键", sys_prompt)
        self.assertIn("board_spec", sys_prompt)

        sample_entry = {
            "id": "11_001",
            "chapter_title": "技术与设计取舍",
            "title": "极简配置与本地持久化",
            "cost_desc": "0元",
            "plain_text": "不要过度设计，只保留最核心的几个设计取舍，让系统坚固可靠。",
            "benefit_desc": "维护成本降低80%",
            "evidence_grade": "A",
            "notes": "简单是终极的精纯"
        }
        usr_prompt = build_whiteboard_user_prompt(sample_entry, scene_count=6)
        self.assertIn("技术与设计取舍", usr_prompt)
        self.assertIn("极简配置", usr_prompt)
        self.assertIn("w1_whiteboard", usr_prompt)
        self.assertIn("少即是多", usr_prompt)


class TestWhiteboardLayoutEngine(unittest.TestCase):
    """Test procedural canvas rendering, negative space calculation, and vector stroke generation."""

    def setUp(self):
        self.engine = WhiteboardLayoutEngine(width=1080, height=1920)

    def test_create_paper_canvas_and_base(self):
        """Verify paper canvas dimensions, color range, and title rendering."""
        canvas = self.engine.create_paper_canvas()
        self.assertEqual(canvas.size, (1080, 1920))
        arr = np.array(canvas)
        # Average color should be near #FAF8F5 (250, 248, 245)
        self.assertTrue(245 <= np.mean(arr[:, :, 0]) <= 255)
        self.assertTrue(243 <= np.mean(arr[:, :, 1]) <= 253)
        self.assertTrue(240 <= np.mean(arr[:, :, 2]) <= 250)

        layout = self.engine.build_sample_layout()
        base_canvas = self.engine.create_base_canvas(layout)
        self.assertEqual(base_canvas.size, (1080, 1920))

    def test_sample_layout_whitespace_ratio(self):
        """Verify layout respects zen negative space requirements (>= 65%)."""
        layout = self.engine.build_sample_layout()
        self.assertGreaterEqual(layout.whitespace_ratio, 0.65)
        self.assertEqual(len(layout.items), 4)

    def test_stroke_generators(self):
        """Verify procedural stroke generators output valid multi-point polylines."""
        box_strokes = self.engine.generate_rounded_box_strokes(200, 200, 160, 80)
        self.assertGreaterEqual(len(box_strokes), 1)
        self.assertGreater(len(box_strokes[0]), 10)

        cursor_strokes = self.engine.generate_cursor_strokes(200, 200, 40)
        self.assertGreaterEqual(len(cursor_strokes), 1)

        plane_strokes = self.engine.generate_paper_plane_strokes(400, 400, 100)
        self.assertGreaterEqual(len(plane_strokes), 1)

        net_strokes = self.engine.generate_network_graph_strokes(600, 600, 60)
        self.assertGreaterEqual(len(net_strokes), 3)


class TestHandCompositor(unittest.TestCase):
    """Test hand asset generation, smooth arc-length interpolation, and frame rendering."""

    def setUp(self):
        self.compositor = HandCompositor(width=1080, height=1920)
        self.engine = WhiteboardLayoutEngine(width=1080, height=1920)
        self.layout = self.engine.build_sample_layout()

    def test_hand_asset_attributes(self):
        """Verify hand image and shadow asset dimensions and alpha channel."""
        self.assertIsNotNone(self.compositor.hand_img)
        self.assertIsNotNone(self.compositor.hand_shadow)
        self.assertEqual(self.compositor.hand_img.mode, "RGBA")
        self.assertEqual(self.compositor.hand_shadow.mode, "RGBA")
        tip_x, tip_y = self.compositor.tip_offset
        self.assertGreater(tip_x, 0)
        self.assertGreater(tip_y, 0)

    def test_stroke_planning_and_timing(self):
        """Verify plan_strokes_from_layout creates sequential strokes with non-overlapping draw times."""
        duration = 3.5
        strokes = self.compositor.plan_strokes_from_layout(self.layout, total_duration=duration, draw_ratio=0.75)
        self.assertGreater(len(strokes), 5)
        for i in range(1, len(strokes)):
            self.assertGreaterEqual(strokes[i].start_time, strokes[i - 1].end_time)

    def test_interpolate_stroke_point(self):
        """Verify continuous polyline point interpolation."""
        pts = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)]
        p0 = self.compositor.interpolate_stroke_point(pts, 0.0)
        self.assertEqual(p0, (0.0, 0.0))

        p_half = self.compositor.interpolate_stroke_point(pts, 0.5)
        self.assertAlmostEqual(p_half[0], 100.0, delta=1.0)
        self.assertAlmostEqual(p_half[1], 0.0, delta=1.0)

        p1 = self.compositor.interpolate_stroke_point(pts, 1.0)
        self.assertEqual(p1, (100.0, 100.0))

    def test_render_frame_at_time(self):
        """Verify render_frame_at_time produces a valid uint8 image array at arbitrary timestamps."""
        base_canvas = self.engine.create_base_canvas(self.layout)
        static_board = self.engine.render_static_board(self.layout)
        strokes = self.compositor.plan_strokes_from_layout(self.layout, total_duration=3.0)

        for t in [0.2, 1.5, 2.8]:
            frame = self.compositor.render_frame_at_time(
                t=t,
                duration=3.0,
                layout=self.layout,
                strokes=strokes,
                base_canvas=base_canvas,
                static_completed_board=static_board,
            )
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (1920, 1080, 3))
            self.assertEqual(frame.dtype, np.uint8)


if __name__ == "__main__":
    unittest.main()
