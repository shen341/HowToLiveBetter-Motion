"""Whiteboard Doodle Explainer Engine for HowToLiveBetter-Motion.
Supports both procedural SVG layouts and semantic stream raster whiteboard animations.
"""

from src.whiteboard.layout_engine import WhiteboardLayoutEngine, BoardItem, BoardLayout
from src.whiteboard.hand_compositor import HandCompositor, HandStroke
from src.whiteboard.stream_renderer import (
    StreamWhiteboardRenderer,
    StreamWhiteboardConfig,
    TipOverlay,
    scaled_rect,
)
from src.whiteboard.annotation_planner import AnnotationPlanner

__all__ = [
    "WhiteboardLayoutEngine",
    "BoardItem",
    "BoardLayout",
    "HandCompositor",
    "HandStroke",
    "StreamWhiteboardRenderer",
    "StreamWhiteboardConfig",
    "TipOverlay",
    "scaled_rect",
    "AnnotationPlanner",
]
