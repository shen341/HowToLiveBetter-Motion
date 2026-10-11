"""03_video_assembler.py - Video assembly and audio mixing execution script.

Usage:
    python 03_video_assembler.py --entry-id 01_001
    python 03_video_assembler.py --limit 3
"""

import argparse
import io
import json
import os
import re
import sys
import time

# Ensure UTF-8 output encoding on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from src.assembler import VideoAssembler
from src.config import OUTPUT_FINAL_VIDEOS_DIR
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


def assemble_one(entry: dict, assembler: VideoAssembler, conn, progress_path: str, custom_bgm: str = None) -> bool:
    """Assemble final MP4 for a single entry."""
    entry_id = entry["id"]
    chapter_title = entry["chapter_title"]
    title = entry["title"]

    print("=" * 65)
    print(f"🎞️ 正在合成短视频 [{entry_id}] 《{chapter_title}》 - {title}")
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
        print("🎬 步骤 1/3: 正在串联多幕分镜画面与运镜动效...")
        print("✍️ 步骤 2/3: 渲染动态大字卡片与多行胶囊旁白字幕...")
        print("🎵 步骤 3/3: 混入环境轻音乐 BGM 并渲染导出 1080x1920 MP4...")

        assembler.assemble_entry(
            entry_data=entry,
            storyboard=storyboard,
            output_path=output_mp4_path,
            bgm_path=custom_bgm
        )

        elapsed = time.time() - start_time
        file_size_mb = os.path.getsize(output_mp4_path) / (1024 * 1024)
        print(f"✅ 合成渲染成功！")
        print(f"   • 输出文件: {output_mp4_path}")
        print(f"   • 文件大小: {file_size_mb:.2f} MB")
        print(f"   • 耗时: {elapsed:.1f} 秒")

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

        # 更新数据库状态为 Completed
        update_status(
            conn,
            entry_id,
            status="Completed",
            final_video_path=output_mp4_path
        )
        export_progress_json(conn, progress_path)
        print(f"🎉 状态已归档: [Completed]\n")
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
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--progress-path", default=DEFAULT_PROGRESS_PATH, help="Path to progress.json")
    args = parser.parse_args()

    conn = get_connection(args.db_path)
    assembler = VideoAssembler()

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

    print(f"📋 即将合成 {len(entries)} 个视频...")
    success_cnt = 0
    for entry in entries:
        if assemble_one(entry, assembler, conn, args.progress_path, custom_bgm=args.bgm):
            success_cnt += 1

    print("-" * 65)
    print(f"🏁 视频合成批处理完成: 成功 {success_cnt} / {len(entries)} 条")
    print("-" * 65)


if __name__ == "__main__":
    main()
