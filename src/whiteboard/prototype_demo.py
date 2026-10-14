"""Prototype demonstration script for Smooth Whiteboard Animation (TASK-5.4).
Renders the reference whiteboard scene from the attachment to output/prototype_whiteboard.mp4.
"""

import os
import sys
import time
from PIL import Image

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.whiteboard.hand_compositor import HandCompositor
from src.whiteboard.layout_engine import WhiteboardLayoutEngine


def run_prototype_demo(output_path: str = "output/prototype_whiteboard.mp4", duration: float = 4.0, fps: int = 30):
    """Generate a smooth 1080x1920 whiteboard explainer video slice and preview keyframes."""
    print("=" * 70)
    print("[Whiteboard Engine] Starting Smooth Whiteboard Animation Prototype...")
    print("=" * 70)


    start_time = time.time()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 1. Initialize Layout and Hand Compositor
    engine = WhiteboardLayoutEngine(width=1080, height=1920)
    compositor = HandCompositor(width=1080, height=1920)

    # 2. Build layout matching user attachment
    layout = engine.build_sample_layout()
    print(f"[Layout] Title: {layout.scene_title}")
    print(f"[Layout] Elements: {len(layout.items)} items (Whitespace ratio >= {int(layout.whitespace_ratio * 100)}%)")

    base_canvas = engine.create_base_canvas(layout)
    static_board = engine.render_static_board(layout)
    strokes = compositor.plan_strokes_from_layout(layout, total_duration=duration, draw_ratio=0.75)
    print(f"[Strokes] Planned {len(strokes)} continuous kinematic stroke segments")

    # 3. Export key preview snapshot frames for inspection
    preview_dir = os.path.join(os.path.dirname(output_path), "whiteboard_preview_frames")
    os.makedirs(preview_dir, exist_ok=True)

    test_timestamps = [0.4, 1.8, 3.2]
    preview_paths = []
    for t_val in test_timestamps:
        frame_arr = compositor.render_frame_at_time(
            t=t_val,
            duration=duration,
            layout=layout,
            strokes=strokes,
            base_canvas=base_canvas,
            static_completed_board=static_board,
        )
        snap_path = os.path.join(preview_dir, f"frame_t{int(t_val*10)}d.png")
        Image.fromarray(frame_arr).save(snap_path)
        preview_paths.append(snap_path)
        print(f"  [Snapshot] Saved frame (t={t_val:.1f}s): {snap_path}")

    # 4. Render VideoClip with MoviePy
    print(f"[Render] Synthesizing 1080x1920 {fps}fps smooth video stream (Duration: {duration}s)...")
    clip = compositor.create_whiteboard_clip(duration=duration, layout=layout, engine=engine)

    # Write MP4 via MoviePy / ffmpeg
    clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        preset="fast",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger=None,  # Clean console output
    )

    elapsed = time.time() - start_time
    file_size_kb = os.path.getsize(output_path) / 1024.0
    print("=" * 70)
    print(f"[Success] Render complete: {output_path}")
    print(f"[Metrics] Elapsed: {elapsed:.2f}s | Size: {file_size_kb:.1f} KB | Speed: {fps * duration / elapsed:.1f} fps")
    print("=" * 70)

    return output_path, preview_paths


if __name__ == "__main__":
    run_prototype_demo()
