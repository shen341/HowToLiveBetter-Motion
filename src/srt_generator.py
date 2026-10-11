"""SRT subtitle generator module for HowToLiveBetter-Motion.

Generates standalone, standard .srt subtitle files aligned with the video timeline
and synchronized TTS speech tracks, accounting for 0.5s crossfade overlap.
"""

import argparse
import io
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional


def format_srt_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS,mmm string according to standard SRT specifications.

    Examples:
        format_srt_time(0.0) -> "00:00:00,000"
        format_srt_time(1.234) -> "00:00:01,234"
        format_srt_time(65.5) -> "00:01:05,500"
    """
    total_ms = int(round(max(0.0, seconds) * 1000))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    sec = total_sec % 60
    total_min = total_sec // 60
    min_ = total_min % 60
    hours = total_min // 60
    return f"{hours:02d}:{min_:02d}:{sec:02d},{ms:03d}"


def get_audio_file_duration(audio_path: str) -> Optional[float]:
    """Inspect local audio file duration with graceful fallback."""
    if not audio_path or not os.path.exists(audio_path):
        return None
    try:
        if audio_path.lower().endswith(".wav"):
            import wave
            with wave.open(audio_path, "r") as w:
                return w.getnframes() / float(w.getframerate())
        from moviepy import AudioFileClip
        clip = AudioFileClip(audio_path)
        dur = float(clip.duration)
        clip.close()
        return dur
    except Exception:
        return None


class SRTGenerator:
    """Engine for generating standard SRT subtitle files from storyboard timelines."""

    def __init__(self, transition_overlap: float = 0.5):
        """
        Args:
            transition_overlap: Overlap duration between consecutive scenes in seconds (default: 0.5s).
        """
        self.transition_overlap = transition_overlap

    def calculate_scene_timelines(self, storyboard: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate the precise global video timeline timestamps for each scene and its narration speech.

        Matches the exact timeline mechanics in VideoAssembler.assemble_entry:
        - Scene 0 starts at 0.0s
        - Scene i starts at (Scene i-1 start + Scene i-1 duration - transition_overlap)
        - Scene 0 audio starts at 0.10s
        - Scene i audio starts at (Scene i start + 0.15s)
        - Scene audio ends at (audio start + audio duration)
        """
        scenes = storyboard.get("scenes", [])
        if not scenes:
            return []

        timeline_entries: List[Dict[str, Any]] = []
        current_scene_start = 0.0

        for idx, scene in enumerate(scenes):
            scene_dur = float(scene.get("duration_sec", 6.0))

            if idx == 0:
                scene_start = 0.0
                current_scene_start = scene_dur
                audio_start = 0.10
            else:
                scene_start = current_scene_start - self.transition_overlap
                current_scene_start = scene_start + scene_dur
                audio_start = scene_start + 0.15

            # Resolve audio duration
            audio_dur = scene.get("audio_duration_sec")
            if audio_dur is None:
                audio_path = scene.get("local_audio_path")
                audio_dur = get_audio_file_duration(audio_path) if audio_path else None
            if audio_dur is None:
                audio_dur = max(1.0, scene_dur - 0.5)
            else:
                audio_dur = float(audio_dur)

            audio_end = audio_start + audio_dur
            scene_end = scene_start + scene_dur

            narration = scene.get("narration_segment", "").strip()

            timeline_entries.append({
                "scene_index": scene.get("scene_index", idx + 1),
                "scene_start": round(scene_start, 3),
                "scene_end": round(scene_end, 3),
                "scene_duration": round(scene_dur, 3),
                "audio_start": round(audio_start, 3),
                "audio_end": round(audio_end, 3),
                "audio_duration": round(audio_dur, 3),
                "narration": narration
            })

        return timeline_entries

    def _split_into_clauses(self, text: str) -> List[str]:
        """Split a narration string into natural, readable clauses for short video display."""
        if not text:
            return []

        # Split on sentence terminals and major punctuation
        raw_parts = re.split(r'([。！？；;\n]+)', text)
        sentences = []
        for i in range(0, len(raw_parts), 2):
            chunk = raw_parts[i].strip()
            punct = raw_parts[i + 1].strip() if i + 1 < len(raw_parts) else ""
            full_clause = (chunk + punct).strip()
            if full_clause:
                sentences.append(full_clause)

        # If a single clause is still very long (> 22 chars), split at commas
        final_clauses = []
        for s in sentences:
            if len(s) > 22 and ('，' in s or ',' in s):
                sub_parts = re.split(r'([，,])', s)
                cur = ""
                for j in range(0, len(sub_parts), 2):
                    sub_chunk = sub_parts[j].strip()
                    sub_punct = sub_parts[j + 1].strip() if j + 1 < len(sub_parts) else ""
                    piece = sub_chunk + sub_punct
                    if len(cur) + len(piece) <= 20:
                        cur += piece
                    else:
                        if cur:
                            final_clauses.append(cur)
                        cur = piece
                if cur:
                    final_clauses.append(cur)
            else:
                final_clauses.append(s)

        return final_clauses if final_clauses else [text]

    def generate_srt_entries(
        self,
        storyboard: Dict[str, Any],
        split_sentences: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate structured subtitle entries with timestamps and text.

        Args:
            storyboard: Parsed storyboard JSON dictionary.
            split_sentences: Whether to split scene narration into shorter sentence-level entries.

        Returns:
            List of dicts containing index, start_sec, end_sec, start_str, end_str, and text.
        """
        scene_timelines = self.calculate_scene_timelines(storyboard)
        srt_entries: List[Dict[str, Any]] = []
        entry_idx = 1

        for s in scene_timelines:
            narration = s["narration"]
            audio_start = s["audio_start"]
            audio_dur = s["audio_duration"]

            if not narration:
                continue

            if not split_sentences:
                # Scene-level subtitle entry (1:1 with scene and narration audio)
                srt_entries.append({
                    "index": entry_idx,
                    "start_sec": audio_start,
                    "end_sec": s["audio_end"],
                    "start_str": format_srt_time(audio_start),
                    "end_str": format_srt_time(s["audio_end"]),
                    "text": narration
                })
                entry_idx += 1
            else:
                # Proportional sentence/clause level splitting
                clauses = self._split_into_clauses(narration)
                total_chars = sum(len(re.sub(r'[\s\W_]+', '', c)) or len(c) for c in clauses)
                if total_chars == 0:
                    total_chars = len(clauses)

                cur_t = audio_start
                for c_idx, c in enumerate(clauses):
                    c_chars = len(re.sub(r'[\s\W_]+', '', c)) or len(c)
                    ratio = c_chars / total_chars
                    c_dur = audio_dur * ratio
                    c_end = cur_t + c_dur
                    if c_idx == len(clauses) - 1:
                        c_end = s["audio_end"]

                    srt_entries.append({
                        "index": entry_idx,
                        "start_sec": cur_t,
                        "end_sec": c_end,
                        "start_str": format_srt_time(cur_t),
                        "end_str": format_srt_time(c_end),
                        "text": c
                    })
                    entry_idx += 1
                    cur_t = c_end

        return srt_entries

    def generate_srt_text(
        self,
        storyboard: Dict[str, Any],
        split_sentences: bool = False
    ) -> str:
        """Generate standard SRT formatted text string."""
        entries = self.generate_srt_entries(storyboard, split_sentences=split_sentences)
        blocks = []
        for e in entries:
            block = f"{e['index']}\n{e['start_str']} --> {e['end_str']}\n{e['text']}"
            blocks.append(block)

        return "\n\n".join(blocks) + "\n"

    def export_srt(
        self,
        storyboard: Dict[str, Any],
        output_path: str,
        split_sentences: bool = False
    ) -> str:
        """Export SRT subtitle file to disk.

        Args:
            storyboard: Storyboard JSON dictionary.
            output_path: Path where the .srt file will be saved.
            split_sentences: If True, splits narration into clauses.

        Returns:
            Absolute path of the written .srt file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        srt_content = self.generate_srt_text(storyboard, split_sentences=split_sentences)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        return os.path.abspath(output_path)


def main():
    """CLI utility to generate and verify standalone SRT subtitle files."""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    parser = argparse.ArgumentParser(description="Generate standalone SRT subtitles from storyboard.json.")
    parser.add_argument("--storyboard", type=str, default=None, help="Path to storyboard.json file")
    parser.add_argument("--entry-id", type=str, default=None, help="Entry ID (e.g. 01_001) to look up in output/raw_assets")
    parser.add_argument("--output", type=str, default=None, help="Target .srt output file path")
    parser.add_argument("--split", action="store_true", help="Split scene narration into sub-sentence clauses")
    args = parser.parse_args()

    storyboard_path = args.storyboard
    if not storyboard_path and args.entry_id:
        storyboard_path = os.path.join("output", "raw_assets", args.entry_id, "storyboard.json")

    if not storyboard_path or not os.path.exists(storyboard_path):
        print(f"❌ 找不到分镜脚本文件: {storyboard_path}")
        sys.exit(1)

    with open(storyboard_path, "r", encoding="utf-8") as f:
        storyboard = json.load(f)

    output_path = args.output
    if not output_path:
        out_dir = os.path.dirname(storyboard_path)
        output_path = os.path.join(out_dir, "subtitles.srt")

    generator = SRTGenerator()
    saved_path = generator.export_srt(storyboard, output_path, split_sentences=args.split)

    print(f"✅ SRT 字幕文件生成成功: {saved_path}")
    print("-" * 50)
    with open(saved_path, "r", encoding="utf-8") as f:
        print(f.read())
    print("-" * 50)


if __name__ == "__main__":
    main()
