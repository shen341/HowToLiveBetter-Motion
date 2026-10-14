"""03_video_assembler.py - Video assembly and audio mixing execution script.

Usage:
    python 03_video_assembler.py --entry-id 01_001
    python 03_video_assembler.py --limit 3
"""

import argparse
import functools
import io
import json
import os
import re
import sys
import time

# Ensure unbuffered UTF-8 output encoding on Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
except (AttributeError, io.UnsupportedOperation):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True, write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True, write_through=True)

print = functools.partial(print, flush=True)

from src.assembler import (
    PLATFORM_PRESETS,
    VideoAssembler,
    get_platform_preset,
)
from src.config import (
    DEFAULT_PLATFORM_PRESET,
    OUTPUT_FINAL_VIDEOS_DIR,
)
from src.db import (
    DEFAULT_DB_PATH,
    DEFAULT_PROGRESS_PATH,
    export_progress_json,
    get_connection,
    get_entry,
    list_entries,
    update_status,
)


def sanitize_filename(name: str) -> str:
    """Sanitize filename by removing illegal filesystem characters."""
    return re.sub(r'[\\/*?:"<>|,\s]+', "_", name).strip("_")


def assemble_one(
    entry: dict,
    assembler: VideoAssembler,
    conn,
    progress_path: str,
    custom_bgm: str = None,
    split_srt: bool = False,
    platform_preset: str = DEFAULT_PLATFORM_PRESET,
    current_index: int = 1,
    total_count: int = 1
) -> bool:
    """Assemble final MP4 for a single entry."""
    entry_id = entry["id"]
    chapter_title = entry["chapter_title"]
    title = entry["title"]

    print("=" * 65)
    print(f"🎞️ [视频 {current_index}/{total_count}] 正在合成短视频 [{entry_id}] 《{chapter_title}》 - {title}")
    print("=" * 65)

    raw_assets_dir = entry.get("raw_assets_dir")
    if not raw_assets_dir or not os.path.exists(raw_assets_dir):
        print(f"❌ 原始素材目录不存在: {raw_assets_dir}。请先运行 02_ai_generator.py 生成素材！")
        return False

    storyboard_path = os.path.join(raw_assets_dir, "storyboard.json")
    if not os.path.exists(storyboard_path):
        print(f"❌ 找不到分镜脚本: {storyboard_path}")
        return False

    with open(storyboard_path, "r", encoding="utf-8") as f:
        storyboard = json.load(f)

    clean_name = sanitize_filename(f"{entry_id}_{chapter_title}之{title}")
    output_mp4_path = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, f"{clean_name}.mp4")

    start_time = time.time()
    try:
        scenes_list = storyboard.get("scenes", [])
        scene_count = len(scenes_list)
        i2v_count = sum(1 for s in scenes_list if s.get("local_video_path") and os.path.exists(s.get("local_video_path")))
        if i2v_count > 0:
            print(f"🎬 [步骤 1/3] 串联 {scene_count} 幕视觉分镜（含 {i2v_count} 幕 I2V 物理微动 + {scene_count - i2v_count} 幕 Ken Burns 运镜，执行 Freeze-and-Drift 缓动扩展与 0.5s 叠化）...")
        else:
            print(f"🎬 [步骤 1/3] 串联 {scene_count} 幕视觉分镜，计算 Ken Burns 运镜与 0.5s 交叉淡入淡出...")
        print("✍️ [步骤 2/3] 渲染黄金比例顶部标题胶囊、动态大字卡片与磨砂玻璃旁白字幕...")
        print("🎵 [步骤 3/3] 混入环境轻音乐 BGM 并使用 MoviePy 多核渲染导出 1080x1920 MP4...")

        assembler.assemble_entry(
            entry_data=entry,
            storyboard=storyboard,
            output_path=output_mp4_path,
            bgm_path=custom_bgm,
            platform_preset=platform_preset,
        )

        elapsed = time.time() - start_time
        file_size_mb = os.path.getsize(output_mp4_path) / (1024 * 1024)
        print(f"✅ 视频渲染合成成功！")
        print(f"   • 输出文件: {output_mp4_path}")
        print(f"   • 文件大小: {file_size_mb:.2f} MB")
        print(f"   • 渲染耗时: {elapsed:.1f} 秒")

        # 确保配套的高清封面卡片存放在 final_videos 目录下，便于发布时直接作为首图取用
        raw_cover = os.path.join(raw_assets_dir, "cover.png")
        final_cover = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, f"{clean_name}_cover.png")
        if os.path.exists(raw_cover) and not os.path.exists(final_cover):
            try:
                import shutil
                shutil.copy2(raw_cover, final_cover)
                print(f"   • 同步发布首图: {final_cover}")
            except Exception:
                pass
        elif not os.path.exists(final_cover):
            try:
                from src.cover_generator import CoverGenerator
                first_img = os.path.join(raw_assets_dir, "scene_01.png") if os.path.exists(os.path.join(raw_assets_dir, "scene_01.png")) else None
                CoverGenerator().generate_cover(
                    entry=entry,
                    background_image_path=first_img,
                    output_path=final_cover,
                    storyboard_data=storyboard
                )
                print(f"   • 补充生成发布首图: {final_cover}")
            except Exception:
                pass

        # 同步/生成成片配套的独立 SRT 字幕文件
        final_srt = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, f"{clean_name}.srt")
        raw_srt = os.path.join(raw_assets_dir, "subtitles.srt")
        try:
            from src.srt_generator import SRTGenerator
            SRTGenerator().export_srt(storyboard, final_srt, split_sentences=split_srt)
            print(f"   • 同步独立字幕: {final_srt}")
            if not os.path.exists(raw_srt):
                SRTGenerator().export_srt(storyboard, raw_srt, split_sentences=split_srt)
        except Exception as e:
            print(f"   ⚠️ 独立字幕生成轻微异常: {e}")

        # 更新数据库状态为 Completed
        update_status(
            conn,
            entry_id,
            status="Completed",
            final_video_path=output_mp4_path
        )
        export_progress_json(conn, progress_path)
        print(f"🎉 [视频 {current_index}/{total_count}] 条目 [{entry_id}] 视频流水线完成！状态: Completed\n")
        return True

    except Exception as e:
        err_msg = f"视频合成渲染失败: {e}"
        print(f"❌ {err_msg}")
        update_status(conn, entry_id, status="Failed", error_message=err_msg, increment_retry=True)
        export_progress_json(conn, progress_path)
        return False


def main():
    parser = argparse.ArgumentParser(description="Assemble short videos from generated assets with subtitles and BGM.")
    parser.add_argument("--entry-id", type=str, default=None, help="Specific entry ID to assemble (e.g. 01_001)")
    parser.add_argument("--limit", type=int, default=1, help="Max entries to assemble (default: 1)")
    parser.add_argument("--force", action="store_true", help="Force re-assemble even if already completed")
    parser.add_argument("--bgm", type=str, default=None, help="Path to custom BGM audio file")
    parser.add_argument("--split-srt", action="store_true", help="Split scene narration into sub-sentence clauses in SRT export")
    parser.add_argument(
        "--preset",
        type=str,
        default=DEFAULT_PLATFORM_PRESET,
        choices=list(PLATFORM_PRESETS.keys()),
        help="Social platform encoding preset: 'default' (通用), 'xhs' (小红书抗二压), 'douyin' (抖音高清), 'wechat' (微信秒开), 'bilibili' (B站高码率)"
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--progress-path", default=DEFAULT_PROGRESS_PATH, help="Path to progress.json")
    args = parser.parse_args()

    conn = get_connection(args.db_path)
    assembler = VideoAssembler(default_preset=args.preset)

    preset_info = get_platform_preset(args.preset)
    print(f"⚙️ 目标平台预设: [{preset_info['name']}] (CRF={preset_info['crf']}, MaxRate={preset_info['maxrate']}, Audio={preset_info['audio_bitrate']})")
    print(f"   • 说明: {preset_info['description']}")

    if args.entry_id:
        target_entry = get_entry(conn, args.entry_id)
        if not target_entry:
            print(f"❌ 未找到条目: {args.entry_id}")
            sys.exit(1)
        entries = [target_entry]
    else:
        status_filter = None if args.force else "Media_Generated"
        entries = list_entries(conn, status=status_filter, limit=args.limit)

    if not entries:
        print("ℹ️ 没有待合成的条目 (状态需为 Media_Generated)。可通过 --entry-id 或 --force 指定条目。")
        sys.exit(0)

    total_count = len(entries)
    print(f"📋 即将批量合成 {total_count} 个短视频...")
    success_cnt = 0
    batch_start = time.time()

    for idx, entry in enumerate(entries, start=1):
        if assemble_one(
            entry,
            assembler,
            conn,
            args.progress_path,
            custom_bgm=args.bgm,
            split_srt=args.split_srt,
            platform_preset=args.preset,
            current_index=idx,
            total_count=total_count
        ):
            success_cnt += 1

    batch_elapsed = time.time() - batch_start
    print("-" * 65)
    print(f"🏁 视频合成批处理完成: 成功 {success_cnt} / {total_count} 条 (总耗时: {batch_elapsed:.1f}s)")
    print("-" * 65)


if __name__ == "__main__":
    main()
