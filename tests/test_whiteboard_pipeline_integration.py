"""Integration tests for Whiteboard Smooth Motion Pipeline (Stage 2: TASK-5.4)."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.assembler import VideoAssembler
from src.db import get_connection, init_db, upsert_entry, get_entry
from src.muse_client import MuseClient, is_i2v_scene, is_whiteboard_scene
from src.whiteboard.layout_engine import WhiteboardLayoutEngine
from src.whiteboard.hand_compositor import HandCompositor
import importlib


class TestWhiteboardPipelineIntegration(unittest.TestCase):
    """Verify whiteboard pipeline end-to-end integration across AI generation and video assembly."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.progress_path = os.path.join(self.temp_dir, "progress.json")
        self.conn = get_connection(self.db_path)
        init_db(self.conn)

        self.sample_entry = {
            "id": "wb_001",
            "source_file": "test.md",
            "chapter_index": 1,
            "chapter_title": "极简生活",
            "item_index": 1,
            "title": "留白与深思",
            "plain_text": "剔除冗余杂乱，留下核心概念，在空间中获得清晰深思。",
            "cost_desc": "0成本",
            "benefit_desc": "心智带宽提升80%",
            "evidence_grade": "A",
            "notes": "Less is more"
        }
        upsert_entry(self.conn, self.sample_entry)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_whiteboard_scene_classifier_and_i2v_isolation(self):
        """Verify is_whiteboard_scene is isolated and never triggers is_i2v_scene."""
        for idx in range(1, 7):
            self.assertTrue(is_whiteboard_scene(idx, 6, "whiteboard"))
            self.assertFalse(is_i2v_scene(idx, 6, "whiteboard"))
            self.assertFalse(is_whiteboard_scene(idx, 6, "static"))
            self.assertFalse(is_whiteboard_scene(idx, 6, "i2v-tier1"))

    def test_generate_script_whiteboard_structure(self):
        """Verify generate_script produces dedicated board_spec and whiteboard motion type in mock mode."""
        client = MuseClient(mock=True)
        script = client.generate_script(self.sample_entry, motion_mode="whiteboard")

        self.assertEqual(script["art_style_id"], "w1_whiteboard")
        self.assertEqual(len(script["scenes"]), 6)
        for s in script["scenes"]:
            self.assertEqual(s.get("motion_type_mode"), "whiteboard")
            self.assertIn("board_spec", s)
            self.assertIn("board_title", s["board_spec"])
            self.assertIn("whitespace_ratio", s["board_spec"])

    def test_layout_engine_generate_scene_layout(self):
        """Verify WhiteboardLayoutEngine dynamically generates layout and stroke trajectories."""
        layout_eng = WhiteboardLayoutEngine(width=1080, height=1920)
        scene_data = {
            "scene_index": 4,
            "kinetic_typography": {"text": "证据 A 级"},
            "primary_subject": "权威徽章",
            "board_spec": {
                "board_title": "证据 A 级",
                "underline_accent": "#7BC8A4",
                "key_subject": "权威徽章",
                "board_keywords": "Grade A",
                "whitespace_ratio": "70%"
            }
        }
        layout, canvas, strokes = layout_eng.generate_scene_layout(scene_data, scene_index=4)
        self.assertEqual(canvas.size, (1080, 1920))
        self.assertGreater(len(strokes), 0)
        self.assertEqual(layout.scene_title, "证据 A 级")

    @patch("src.tts_client.TTSClient.generate_speech")
    def test_ai_generator_process_entry_whiteboard(self, mock_tts):
        """Verify process_entry with whiteboard motion mode creates whiteboard video slice."""
        def fake_speech(text, output_path):
            with open(output_path, "wb") as f:
                f.write(b"\x00" * 128)
            return 2.0

        mock_tts.side_effect = fake_speech

        from src.tts_client import TTSClient
        tts_client = TTSClient()
        client = MuseClient(mock=True)

        # Import 02_ai_generator
        gen_module = importlib.import_module("02_ai_generator")

        with patch.object(gen_module, "OUTPUT_RAW_ASSETS_DIR", self.temp_dir):
            success = gen_module.process_entry(
                entry=self.sample_entry,
                client=client,
                tts_client=tts_client,
                conn=self.conn,
                progress_path=self.progress_path,
                force=True,
                motion_mode="whiteboard",
                scenes_count=6,
            )
            self.assertTrue(success)

            asset_dir = os.path.join(self.temp_dir, "wb_001")
            storyboard_path = os.path.join(asset_dir, "storyboard.json")
            self.assertTrue(os.path.exists(storyboard_path))

            with open(storyboard_path, "r", encoding="utf-8") as f:
                sb_data = json.load(f)

            self.assertEqual(sb_data["art_style_id"], "w1_whiteboard")
            scenes = sb_data["scenes"]
            self.assertEqual(len(scenes), 6)

            for idx in range(1, 7):
                vid_path = os.path.join(asset_dir, f"motion_{idx:02d}.mp4")
                img_path = os.path.join(asset_dir, f"scene_{idx:02d}.png")
                self.assertTrue(os.path.exists(vid_path), f"Missing whiteboard video: {vid_path}")
                self.assertTrue(os.path.exists(img_path), f"Missing whiteboard base image: {img_path}")
                self.assertEqual(scenes[idx - 1]["motion_type_mode"], "whiteboard")

            # Verify VideoAssembler can assemble whiteboard clips
            assembler = VideoAssembler(width=1080, height=1920, fps=30)
            final_mp4_path = os.path.join(self.temp_dir, "final_test.mp4")
            # Assemble single clip test
            clip = assembler.assemble_scene_clip(scenes[0], duration=scenes[0]["duration_sec"])
            self.assertIsNotNone(clip)
            self.assertEqual(clip.size, (1080, 1920))
            clip.close()


if __name__ == "__main__":
    unittest.main()
