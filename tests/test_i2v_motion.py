"""Unit tests for I2V Hybrid Motion Pipeline (TASK-5.0 / ADR-010)."""

import os
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

from moviepy import VideoClip, VideoFileClip
from src.assembler import VideoAssembler
from src.muse_client import MuseClient, is_i2v_scene


class TestI2VSceneClassifier(unittest.TestCase):
    """Test is_i2v_scene tier classification and mode routing."""

    def test_static_mode(self):
        """In static mode, all scenes should return False."""
        for mode in ["static", "none", "off", "ken_burns", "", " STATIC "]:
            for idx in range(1, 7):
                self.assertFalse(is_i2v_scene(idx, total_scenes=6, motion_mode=mode))

    def test_i2v_all_mode(self):
        """In i2v-all mode, all scenes should return True."""
        for mode in ["i2v-all", "all", "full", "I2V-ALL"]:
            for idx in range(1, 7):
                self.assertTrue(is_i2v_scene(idx, total_scenes=6, motion_mode=mode))

    def test_i2v_tier1_mode_6_scenes(self):
        """In i2v-tier1 mode with 6 scenes, only Scene 1 (Hook) and Scene 5 (Action) return True."""
        tier1_modes = ["i2v-tier1", "tier1", "smart", "I2V-TIER1 "]
        for mode in tier1_modes:
            self.assertTrue(is_i2v_scene(1, total_scenes=6, motion_mode=mode), "Scene 1 should be Tier-1 Hook")
            self.assertFalse(is_i2v_scene(2, total_scenes=6, motion_mode=mode))
            self.assertFalse(is_i2v_scene(3, total_scenes=6, motion_mode=mode))
            self.assertFalse(is_i2v_scene(4, total_scenes=6, motion_mode=mode))
            self.assertTrue(is_i2v_scene(5, total_scenes=6, motion_mode=mode), "Scene 5 should be Tier-1 Action")
            self.assertFalse(is_i2v_scene(6, total_scenes=6, motion_mode=mode))

    def test_i2v_tier1_mode_4_scenes(self):
        """In i2v-tier1 mode with 4 scenes, Scene 1 and Scene 3 (second to last) return True."""
        self.assertTrue(is_i2v_scene(1, total_scenes=4, motion_mode="i2v-tier1"))
        self.assertFalse(is_i2v_scene(2, total_scenes=4, motion_mode="i2v-tier1"))
        self.assertTrue(is_i2v_scene(3, total_scenes=4, motion_mode="i2v-tier1"))
        self.assertFalse(is_i2v_scene(4, total_scenes=4, motion_mode="i2v-tier1"))


class TestI2VMotionGenerationAndAssembler(unittest.TestCase):
    """Test mock video slice synthesis and Freeze-and-Drift assembly logic."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="test_i2v_")
        cls.test_image_path = os.path.join(cls.temp_dir, "test_frame.png")
        # Create a 1080x1920 test image
        img = Image.new("RGB", (1080, 1920), color=(40, 80, 120))
        img.save(cls.test_image_path)

        cls.client = MuseClient(mock=True)
        cls.assembler = VideoAssembler(width=1080, height=1920, fps=24)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_mock_video_generation(self):
        """Verify mock video generation produces a valid, readable MP4 video clip."""
        out_video = os.path.join(self.temp_dir, "motion_01.mp4")
        res = self.client.generate_video(
            prompt="Camera quick punch-in zoom onto subject",
            output_path=out_video,
            image_path=self.test_image_path,
            duration_sec=3.0
        )
        self.assertEqual(res, out_video)
        self.assertTrue(os.path.exists(out_video))
        self.assertGreater(os.path.getsize(out_video), 1000)

        vclip = VideoFileClip(out_video)
        self.assertAlmostEqual(vclip.duration, 3.0, delta=0.2)
        self.assertEqual(vclip.size, [1080, 1920])
        vclip.close()

    def test_freeze_and_drift_expansion(self):
        """Test extending shorter video clip (3.0s) to target duration (4.6s) with Freeze-and-Drift."""
        # 1. Create a 2.5s source video
        src_video = os.path.join(self.temp_dir, "short_motion.mp4")
        self.client.generate_video(
            prompt="Micro motion test",
            output_path=src_video,
            image_path=self.test_image_path,
            duration_sec=2.5
        )

        target_dur = 4.2
        composite_clip = self.assembler.create_freeze_and_drift_clip(
            video_path=src_video,
            target_duration=target_dur,
            motion_type="zoom_in",
            fallback_image_path=self.test_image_path
        )

        self.assertAlmostEqual(composite_clip.duration, target_dur, delta=0.05)
        # Verify frames can be retrieved across both the main motion and drift intervals
        frame_mid_motion = composite_clip.get_frame(1.2)
        frame_in_drift = composite_clip.get_frame(3.5)
        self.assertEqual(frame_mid_motion.shape, (1920, 1080, 3))
        self.assertEqual(frame_in_drift.shape, (1920, 1080, 3))
        composite_clip.close()

    def test_freeze_and_drift_subclip_when_longer(self):
        """Test subclip behavior when source video (3.0s) is longer than target duration (2.0s)."""
        src_video = os.path.join(self.temp_dir, "motion_01.mp4")
        if not os.path.exists(src_video):
            self.client.generate_video("test", src_video, self.test_image_path, 3.0)

        composite_clip = self.assembler.create_freeze_and_drift_clip(
            video_path=src_video,
            target_duration=2.0,
            motion_type="zoom_in"
        )
        self.assertAlmostEqual(composite_clip.duration, 2.0, delta=0.05)
        composite_clip.close()

    def test_freeze_and_drift_fallback_on_missing_file(self):
        """Test graceful fallback to animated image clip if video path is missing."""
        missing_video = os.path.join(self.temp_dir, "non_existent.mp4")
        clip = self.assembler.create_freeze_and_drift_clip(
            video_path=missing_video,
            target_duration=3.5,
            motion_type="zoom_in",
            fallback_image_path=self.test_image_path
        )
        self.assertAlmostEqual(clip.duration, 3.5, delta=0.05)
        clip.close()

    def test_assemble_scene_clip_with_i2v(self):
        """Test assemble_scene_clip layering with I2V background and typography overlays."""
        src_video = os.path.join(self.temp_dir, "motion_01.mp4")
        scene_data = {
            "scene_index": 1,
            "duration_sec": 4.5,
            "local_image_path": self.test_image_path,
            "local_video_path": src_video,
            "kinetic_typography": {"text": "不要早死"},
            "narration_segment": "日常生活中我们常常忽略的安全细节。"
        }
        scene_clip = self.assembler.assemble_scene_clip(scene_data, duration=4.5, motion_type="zoom_in")
        self.assertAlmostEqual(scene_clip.duration, 4.5, delta=0.05)
        self.assertEqual(scene_clip.size, (1080, 1920))
        scene_clip.close()


if __name__ == "__main__":
    unittest.main()
