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



class TestSVGParserAndLibrary(unittest.TestCase):
    """Test SVG parsing, projection scaling, and semantic keyword matching."""

    def test_svg_parser_primitives(self):
        """Verify SVG parser converts paths, circles, rects, and lines into scaled polylines."""
        from src.whiteboard.svg_parser import parse_svg_content, scale_and_center_strokes

        svg_sample = """<svg viewBox="0 0 100 100">
            <path d="M 10,10 L 90,10 C 90,50 50,90 10,90 Z" />
            <circle cx="50" cy="50" r="20" />
            <rect x="20" y="20" width="30" height="30" />
            <line x1="10" y1="10" x2="90" y2="90" />
        </svg>"""
        strokes = parse_svg_content(svg_sample)
        self.assertEqual(len(strokes), 4)

        scaled = scale_and_center_strokes(strokes, center_x=540, center_y=850, target_width=300)
        self.assertEqual(len(scaled), 4)
        for s in scaled:
            self.assertGreater(len(s), 1)

    def test_svg_library_builtin_icons(self):
        """Verify built-in SVGs (automobile, seatbelt, crash_warning, shield_badge, etc.) parse properly."""
        from src.whiteboard.svg_library import SVGIconLibrary, BUILTIN_SVGS

        lib = SVGIconLibrary()
        for icon_id in BUILTIN_SVGS:
            strokes = lib.get_icon_strokes(icon_id, center_x=540, center_y=850, target_width=360)
            self.assertIsNotNone(strokes, f"Failed to get strokes for {icon_id}")
            self.assertGreater(len(strokes), 0)

    def test_svg_library_semantic_matching(self):
        """Verify semantic keyword matching accurately maps automobile for car crash keywords."""
        from src.whiteboard.svg_library import SVGIconLibrary

        lib = SVGIconLibrary()
        # Scene 3: "安全带" "车祸" "死在车里" -> automobile
        matched = lib.match_icon("坐前排系上安全带，出车祸时被撞死的概率大约降一半。坐轻型卡车前排的降六成。")
        self.assertEqual(matched, "automobile")

        # Scene 4: "证据等级 A 级" -> shield_badge
        matched_ev = lib.match_icon("证据等级达到 A 级权威标准，权威数据真实可信。")
        self.assertEqual(matched_ev, "shield_badge")

        # Scene 5: "天平对比" "投入产出" "成本" "收益" -> balance_scale
        matched_cost = lib.match_icon("天平对比 投入产出 执行成本：不花钱，每次上车多花 2 秒；而收益却是：致命伤风险下降。", preferred_priority=["balance_scale"])
        self.assertEqual(matched_cost, "balance_scale")

    def test_custom_svg_icons_semantic_matching(self):
        """Verify user-added custom SVG icons match their specific Chinese domain keywords."""
        from src.whiteboard.svg_library import SVGIconLibrary

        lib = SVGIconLibrary()
        cases = [
            # Batch 1 (6 items)
            ("生病、肚子疼、不舒服 等", "abdominal_feeling"),
            ("银行卡、信用卡、卡片", "bank-card"),
            ("哭泣、哭、悲伤", "crying_feeling"),
            ("赌博、打牌、骰子", "gambling"),
            ("开心、胜利、优秀", "happy_feeling"),
            ("医院、卫生机构", "hospital"),
            # Batch 2 (12 items)
            ("艾滋病", "aids"),
            ("药物、疫苗、药品", "drug"),
            ("救助、帮助", "help"),
            ("医疗检查、病情", "medical-examination"),
            ("摩托车、电动车", "motor"),
            ("金属", "metal-bar"),
            ("放射源", "radiation-alt"),
            ("女性、女人", "female"),
            ("男性、男人", "male"),
            ("儿童、小孩、少儿、幼儿", "children"),
            ("死亡、死亡率", "dead"),
            ("摔倒、骨折", "fall-down"),
        ]
        for query, expected_id in cases:
            matched = lib.match_icon(query)
            self.assertEqual(matched, expected_id, f"Query '{query}' expected '{expected_id}' but got '{matched}'")
            strokes = lib.get_icon_strokes(query)
            self.assertIsNotNone(strokes, f"Failed to get strokes for query '{query}'")
            self.assertGreater(len(strokes), 0, f"Empty strokes for '{query}'")


class TestSentenceExtractionNoTruncation(unittest.TestCase):
    """Test extract_complete_sentences ensures zero sentence truncation."""

    def test_extract_complete_sentences(self):
        from src.muse_client import extract_complete_sentences

        text1 = "底层逻辑非常清晰：坐前排系上安全带，出车祸时被撞死的概率大约降一半。坐轻型卡车前排的降六成。美国 2022 年死在车里的人，能查到系没系带的，有一半没系。"
        res1 = extract_complete_sentences(text1, max_chars=55)
        self.assertEqual(res1, "底层逻辑非常清晰：坐前排系上安全带，出车祸时被撞死的概率大约降一半。坐轻型卡车前排的降六成。")
        self.assertNotIn("美国 2022 年死在车里", res1)
        self.assertTrue(res1.endswith("。"))

        text2 = "美国交通安全主管部门（NHTSA）估计，系安全带能让轿车前排乘员受致命伤的风险下降 45%。轻型卡车前排下降 60%。"
        res2 = extract_complete_sentences(text2, max_chars=45)
        self.assertEqual(res2, "美国交通安全主管部门（NHTSA）估计，系安全带能让轿车前排乘员受致命伤的风险下降 45%。")
        self.assertTrue(res2.endswith("。"))


class TestLayoutEngineSceneSemanticStrokes(unittest.TestCase):
    """Test WhiteboardLayoutEngine dynamically generates automobile strokes for Scene 3."""

    def test_scene_3_automobile_generation(self):
        from src.whiteboard.layout_engine import WhiteboardLayoutEngine

        engine = WhiteboardLayoutEngine()
        scene_3 = {
            "scene_index": 3,
            "board_spec": {
                "board_title": "底层逻辑",
                "key_subject": "汽车安全",
                "board_keywords": "汽车 安全带 车祸防护",
            },
            "primary_subject": "安全带与汽车碰撞受力防护机制",
            "narration_segment": "底层逻辑非常清晰：坐前排系上安全带，出车祸时被撞死的概率大约降一半。坐轻型卡车前排的降六成。",
        }
        layout, base_canvas, strokes = engine.generate_scene_layout(scene_3, scene_index=3)
        self.assertEqual(layout.scene_title, "底层逻辑")
        self.assertGreaterEqual(len(strokes), 8)  # Automobile has 10 strokes
        self.assertEqual(base_canvas.size, (1080, 1920))


if __name__ == "__main__":
    unittest.main()

