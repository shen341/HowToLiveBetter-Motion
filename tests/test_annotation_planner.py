"""Unit tests for AnnotationPlanner (annotation_planner.py)."""

import json
import os
import tempfile
import unittest
import numpy as np
import cv2

from src.whiteboard.annotation_planner import AnnotationPlanner


class TestAnnotationPlanner(unittest.TestCase):
    """Test suite for AnnotationPlanner region detection and annotation scheduling."""

    def setUp(self):
        self.planner = AnnotationPlanner(canvas_width=1080, canvas_height=1920)
        # Create synthetic image with 2 distinct subjects
        self.img = np.full((1920, 1080, 3), 245, dtype=np.uint8)
        # Subject 1 (top-left)
        cv2.rectangle(self.img, (100, 200), (450, 600), (20, 20, 20), -1)
        # Subject 2 (bottom-right)
        cv2.rectangle(self.img, (600, 1100), (950, 1600), (20, 20, 20), -1)

    def test_detect_visual_regions(self):
        """Verify detect_visual_regions discovers distinct visual bounding boxes."""
        regions = self.planner.detect_visual_regions(self.img, max_regions=3)
        self.assertGreaterEqual(len(regions), 2)
        for r in regions:
            self.assertIn("x", r)
            self.assertIn("y", r)
            self.assertIn("width", r)
            self.assertIn("height", r)
            self.assertGreater(r["width"], 50)
            self.assertGreater(r["height"], 50)

    def test_plan_scene_annotation_structure(self):
        """Verify plan_scene_annotation creates specification-compliant annotation dictionary."""
        subs = ["第一步：识别生活常见风险", "第二步：采取零成本规避行动"]
        ann = self.planner.plan_scene_annotation(
            scene_id="scene_01",
            image=self.img,
            duration_sec=6.0,
            subtitles=subs,
            story_basis="安全生活指南",
        )

        self.assertEqual(ann["sceneId"], "scene_01")
        self.assertEqual(ann["canvas"]["width"], 1080)
        self.assertEqual(ann["canvas"]["height"], 1920)
        self.assertEqual(ann["sceneDurationMs"], 6000)
        self.assertGreaterEqual(len(ann["elements"]), 2)

        # Check sequence ordering and non-overlapping startMs
        for i, elem in enumerate(ann["elements"]):
            self.assertEqual(elem["sequence"], i + 1)
            self.assertIn("reveal", elem)
            self.assertGreater(elem["reveal"]["durationMs"], 0)
            self.assertIn("protectedRegions", elem["reveal"])

    def test_save_annotation(self):
        """Verify save_annotation outputs valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "test.annotation.json")
            ann = self.planner.plan_scene_annotation("s01", self.img, 4.0)
            saved_path = self.planner.save_annotation(ann, json_file)

            self.assertTrue(os.path.exists(saved_path))
            with open(saved_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["sceneId"], "s01")


if __name__ == "__main__":
    unittest.main()
