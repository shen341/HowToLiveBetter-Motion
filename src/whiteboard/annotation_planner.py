"""Autonomous Annotation Planner for Whiteboard Stream Animation.
Analyzes scene image contours and subtitle events to produce semantic annotation.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


class AnnotationPlanner:
    """Plans semantic elements, bounding regions, and non-overlapping timeline for a whiteboard scene."""

    def __init__(self, canvas_width: int = 1080, canvas_height: int = 1920):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

    def detect_visual_regions(
        self,
        image_bgr: np.ndarray,
        max_regions: int = 3,
        min_area_ratio: float = 0.02,
    ) -> List[Dict[str, int]]:
        """Detect salient visual subject bounding boxes using Otsu thresholding and contour hierarchy."""
        h, w = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        # Invert so ink/features are white foreground
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological close to merge nearby strokes of the same subject
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        total_area = float(h * w)
        boxes = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area / total_area < min_area_ratio:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            # Add padding
            pad_x = int(bw * 0.08)
            pad_y = int(bh * 0.08)
            rx = max(0, x - pad_x)
            ry = max(0, y - pad_y)
            rw = min(w - rx, bw + pad_x * 2)
            rh = min(h - ry, bh + pad_y * 2)
            boxes.append({"x": rx, "y": ry, "width": rw, "height": rh, "area": area})

        # Sort largest to smallest
        boxes.sort(key=lambda b: b["area"], reverse=True)
        selected = boxes[:max_regions]

        # If no contours detected (e.g. extremely clean vector line), provide balanced central partition
        if not selected:
            selected = [{
                "x": int(w * 0.1),
                "y": int(h * 0.15),
                "width": int(w * 0.8),
                "height": int(h * 0.7),
                "area": total_area * 0.5,
            }]

        # Sort narrative sequence: predominantly top-to-bottom
        selected.sort(key=lambda b: (b["y"] // (h // 4), b["x"]))

        # Remove temporary area key
        return [{"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]} for b in selected]

    def plan_scene_annotation(
        self,
        scene_id: str,
        image: np.ndarray | str | Path,
        duration_sec: float = 5.0,
        subtitles: Optional[List[str]] = None,
        story_basis: str = "",
    ) -> Dict[str, Any]:
        """Generate structured annotation dictionary adhering to Whiteboard Skill specifications."""
        if isinstance(image, (str, Path)):
            raw = np.fromfile(str(image), dtype=np.uint8)
            image_bgr = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        else:
            image_bgr = image

        if image_bgr is None:
            image_bgr = np.full((self.canvas_height, self.canvas_width, 3), 245, dtype=np.uint8)

        ih, iw = image_bgr.shape[:2]
        total_duration_ms = max(2000, int(round(duration_sec * 1000)))

        # Subtitles or narrative chunks
        subs = subtitles if subtitles else ([story_basis] if story_basis else ["重要科普与生活常识讲解"])

        # Detect regions in image
        regions = self.detect_visual_regions(image_bgr, max_regions=max(1, len(subs)))

        # If more subtitles than detected regions, subdivide largest region
        while len(regions) < len(subs):
            largest_idx = max(range(len(regions)), key=lambda i: regions[i]["width"] * regions[i]["height"])
            r = regions.pop(largest_idx)
            # Split vertically
            half_h = r["height"] // 2
            regions.append({"x": r["x"], "y": r["y"], "width": r["width"], "height": half_h})
            regions.append({"x": r["x"], "y": r["y"] + half_h, "width": r["width"], "height": half_h})

        # Reserve gaze hold at the end (500ms)
        gaze_ms = 500
        active_time_ms = max(1000, total_duration_ms - gaze_ms)
        per_elem_ms = active_time_ms // len(regions)

        elements = []
        for idx, reg in enumerate(regions):
            seq = idx + 1
            start_ms = idx * per_elem_ms + 100
            dur_ms = max(600, per_elem_ms - 150)
            sub_text = subs[idx] if idx < len(subs) else subs[-1]

            # Calculate protectedRegions against subsequent regions with overlap
            protected = []
            for next_reg in regions[idx + 1:]:
                # Check bounding box intersection
                ix0 = max(reg["x"], next_reg["x"])
                iy0 = max(reg["y"], next_reg["y"])
                ix1 = min(reg["x"] + reg["width"], next_reg["x"] + next_reg["width"])
                iy1 = min(reg["y"] + reg["height"], next_reg["y"] + next_reg["height"])
                if ix1 > ix0 and iy1 > iy0:
                    protected.append({
                        "x": ix0,
                        "y": iy0,
                        "width": ix1 - ix0,
                        "height": iy1 - iy0,
                    })

            elements.append({
                "id": f"elem_{seq:02d}",
                "label": f"分镜核心主体 {seq}",
                "sequence": seq,
                "narrativeRole": f"第 {seq} 步递进式叙事表达",
                "subtitle": sub_text,
                "region": reg,
                "reveal": {
                    "direction": "top_to_bottom",
                    "startMs": start_ms,
                    "durationMs": dur_ms,
                    "maskPaddingPx": 16,
                    "protectedRegions": protected,
                },
            })

        annotation = {
            "sceneId": scene_id,
            "canvas": {"width": iw, "height": ih},
            "storyBasis": story_basis or " ".join(subs),
            "sceneDurationMs": total_duration_ms,
            "elements": elements,
        }
        return annotation

    def save_annotation(self, annotation: Dict[str, Any], output_json_path: str | Path) -> str:
        """Serialize annotation dict to formatted JSON on disk."""
        path = Path(output_json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(annotation, f, ensure_ascii=False, indent=2)
        return str(path)
