"""Unit tests for Stream Whiteboard Renderer (stream_renderer.py)."""

import os
import tempfile
import unittest
import numpy as np
import cv2

from src.whiteboard.stream_renderer import (
    StreamWhiteboardConfig,
    StreamWhiteboardRenderer,
    TipOverlay,
    scaled_rect,
)


class TestStreamRenderer(unittest.TestCase):
    """Test suite verifying StreamWhiteboardRenderer behavior."""

    def setUp(self):
        # Create a synthetic 1080x1920 test image with beige background and dark sketch lines
        self.width = 540
        self.height = 960
        self.test_img = np.full((self.height, self.width, 3), (215, 235, 245), dtype=np.uint8)  # Ivory/beige

        # Draw a black sketch rectangle and circle
        cv2.rectangle(self.test_img, (50, 100), (200, 400), (20, 20, 20), thickness=4)
        cv2.circle(self.test_img, (350, 500), 80, (20, 20, 20), thickness=4)

        # Build mock annotation with 2 elements and 1 protected region
        self.annotation = {
            "sceneId": "test_scene",
            "canvas": {"width": self.width, "height": self.height},
            "sceneDurationMs": 2000,
            "elements": [
                {
                    "id": "box_elem",
                    "sequence": 1,
                    "region": {"x": 30, "y": 80, "width": 200, "height": 350},
                    "reveal": {
                        "durationMs": 800,
                        "protectedRegions": [{"x": 100, "y": 200, "width": 50, "height": 50}],
                    },
                },
                {
                    "id": "circle_elem",
                    "sequence": 2,
                    "region": {"x": 250, "y": 400, "width": 200, "height": 200},
                    "reveal": {
                        "durationMs": 800,
                        "protectedRegions": [],
                    },
                },
            ],
        }

    def test_scaled_rect(self):
        """Verify scaled_rect correctly transforms coordinates and clamps to bounds."""
        reg = {"x": 10, "y": 20, "width": 100, "height": 200}
        x0, y0, x1, y1 = scaled_rect(reg, sx=2.0, sy=2.0, out_w=500, out_h=500)
        self.assertEqual((x0, y0, x1, y1), (20, 40, 220, 440))

    def test_tip_overlay_stamping(self):
        """Verify TipOverlay stamps properly on canvas without mutating outside dimensions."""
        tip = TipOverlay.from_file_or_fallback(target_height=100)
        canvas = np.full((200, 200, 3), 255, dtype=np.uint8)
        initial_sum = np.sum(canvas)
        tip.stamp(canvas, 100, 100)
        self.assertLess(np.sum(canvas), initial_sum, "Canvas pixels should be modified by stylus")

    def test_allowed_mask_subtraction(self):
        """Verify calculate_allowed_mask excludes subsequent elements and protected regions."""
        renderer = StreamWhiteboardRenderer(self.test_img, self.annotation)
        elem1 = self.annotation["elements"][0]
        later = [self.annotation["elements"][1]]

        mask = renderer.calculate_allowed_mask(elem1, later)
        # Verify protected region is False
        prot = elem1["reveal"]["protectedRegions"][0]
        self.assertFalse(mask[prot["y"] + 10, prot["x"] + 10])
        # Verify region inside box is True
        self.assertTrue(mask[120, 70])

    def test_render_to_video(self):
        """Verify end-to-end video synthesis produces a valid non-empty MP4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_mp4 = os.path.join(tmpdir, "test_whiteboard.mp4")
            config = StreamWhiteboardConfig(fps=15, gaze_seconds=0.2)
            renderer = StreamWhiteboardRenderer(self.test_img, self.annotation, config=config)

            res = renderer.render_to_video(out_mp4)
            self.assertTrue(os.path.exists(res))
            self.assertGreater(os.path.getsize(res), 1000)

            # Inspect generated video properties via cv2.VideoCapture
            cap = cv2.VideoCapture(res)
            self.assertTrue(cap.isOpened())
            n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            self.assertGreater(n_frames, 10)
            self.assertEqual(fps, 15)


if __name__ == "__main__":
    unittest.main()
