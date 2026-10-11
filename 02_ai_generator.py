"""02_ai_generator.py - Storyboard, multimodal assets, and TTS voiceover generation module.

Usage:
    python 02_ai_generator.py --entry-id 01_001
    python 02_ai_generator.py --limit 3
    python 02_ai_generator.py --mock --limit 1
"""

import argparse
import io
import json
import os
import sys
import time

# Ensure UTF-8 output encoding on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from src.config import OUTPUT_RAW_ASSETS_DIR
from src.db import (
    DEFAULT_DB_PATH,
    DEFAULT_PROGRESS_PATH,
    export_progress_json,
    get_connection,
    get_entry,
    list_entries,
    update_status,
)
from src.cover_generator import CoverGenerator
from src.muse_client import MuseClient
from src.tts_client import TTSClient


def process_entry(
    entry: dict,
    client: MuseClient,
    tts_client: TTSClient,
    conn,
    progress_path: str,
    force: bool = False,
    style_mode: str = "auto"
) -> bool:
    """Process a single entry: generate storyboard script, visual assets, and synchronized TTS speech."""
    entry_id = entry["id"]
    chapter_title = entry["chapter_title"]
    title = entry["title"]

    print("=" * 65)
    print(f"🎬 正在生成条目 [{entry_id}] 《{chapter_title}》 - {title}")
    print("=" * 65)

    asset_dir = os.path.join(OUTPUT_RAW_ASSETS_DIR, entry_id)
    os.makedirs(asset_dir, exist_ok=True)
    storyboard_path = os.path.join(asset_dir, "storyboard.json")

    # 1. 生成分镜脚本 (调用 muse-spark 或 mock)
    try:
        print(f"🧠 步骤 1/3: 调用大模型生成结构化分镜脚本 (风格模式: {style_mode})...")
        script_data = client.generate_script(entry, style_mode=style_mode)

        # 确保视频标题格式统一规范
        expected_title_prefix = f"{chapter_title}之"
        if not script_data.get("video_title", "").startswith(expected_title_prefix):
            script_data["video_title"] = f"{chapter_title}之{title}"

        # 落盘分镜 JSON
        with open(storyboard_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 分镜脚本落盘: {storyboard_path}")
        print(f"   • 视频标题: {script_data.get('video_title')}")
        print(f"   • 选定艺术画风: {script_data.get('art_style_name')} ({script_data.get('art_style_id')})")
        print(f"   • 风格决策依据: {script_data.get('art_style_reason', 'AI 深度理解内容语义自主决策')}")
        print(f"   • 分镜场景数: {len(script_data.get('scenes', []))} 幕")
        print(f"   • 完整旁白: {script_data.get('narration_text_full')[:50]}...")

        # 更新数据库状态为 Script_Generated
        update_status(
            conn,
            entry_id,
            status="Script_Generated",
            script_json=json.dumps(script_data, ensure_ascii=False),
            raw_assets_dir=asset_dir
        )
    except Exception as e:
        err_msg = f"分镜脚本生成异常: {e}"
        print(f"❌ {err_msg}")
        update_status(conn, entry_id, status="Failed", error_message=err_msg, increment_retry=True)
        return False

    # 2. 生成多模态分镜图像与语音解说音频
    try:
        scenes = script_data.get("scenes", [])
        style_id = script_data.get("art_style_id", "25_ghibli")
        print(f"🎨 步骤 2/3: 正在批量生成多模态视觉分镜与 TTS 语音讲解 (共 {len(scenes)} 镜)...")

        total_audio_duration = 0.0

        for idx, scene in enumerate(scenes, start=1):
            scene_img_name = f"scene_{idx:02d}.png"
            scene_img_path = os.path.join(asset_dir, scene_img_name)
            prompt = scene.get("image_prompt", "")
            kinetic_word = scene.get("kinetic_typography", {}).get("text", "")
            narration_text = scene.get("narration_segment", "")

            # 2.1 生图
            print(f"   🖼️ [第 {idx} 镜] 浮现字:「{kinetic_word}」 | 旁白: {narration_text[:25]}...")
            if not os.path.exists(scene_img_path) or force:
                client.generate_image(prompt, scene_img_path, style_id=style_id)
            scene["local_image_path"] = scene_img_path

            # 2.2 生成对应分镜的 TTS 语音 (zh-CN-YunzeNeural)
            voice_name = f"voice_{idx:02d}.mp3"
            voice_path = os.path.join(asset_dir, voice_name)
            if narration_text:
                print(f"      🎙️ 正在转换 TTS 讲解语音 (音色: {tts_client.voice})...")
                audio_dur = tts_client.generate_speech(narration_text, voice_path)
                scene["local_audio_path"] = voice_path
                scene["audio_duration_sec"] = round(audio_dur, 2)

                # 以声定景：分镜时长 = 语音时长 + 0.5s 舒适呼吸留白
                scene_dur = round(max(audio_dur + 0.5, 3.0), 2)
                scene["duration_sec"] = scene_dur
                total_audio_duration += audio_dur
                print(f"      ⏱️ 语音时长: {audio_dur:.2f}s -> 分镜动态同步时长: {scene_dur:.2f}s")
            else:
                scene["local_audio_path"] = None
                scene["audio_duration_sec"] = 0.0

        # 更新全局目标时长
        script_data["target_duration_sec"] = round(sum(s.get("duration_sec", 6.0) for s in scenes) - (len(scenes) - 1) * 0.5, 2)
        print(f"📊 全片总净时长 (含转场叠加): {script_data['target_duration_sec']} 秒")

        # 2.3 自动生成 1080x1920 短视频高辨识度专属封面卡片 (TASK-4.1)
        try:
            print("   🖼️ 正在生成短视频专属 1080x1920 封面卡片 (Cover Card)...")
            cover_gen = CoverGenerator()
            first_scene_img = scenes[0].get("local_image_path") if scenes else None
            cover_path = cover_gen.generate_cover(
                entry=entry,
                background_image_path=first_scene_img,
                storyboard_data=script_data
            )
            script_data["cover_image_path"] = cover_path
            print(f"      ✅ 封面卡片生成完成: {cover_path}")
        except Exception as e:
            print(f"      ⚠️ 封面卡片生成轻微异常 (不阻塞主流程): {e}")

        # 更新回写带本地素材路径的 storyboard.json
        with open(storyboard_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)

        # 3. 更新状态为 Media_Generated
        print("💾 步骤 3/3: 更新条目状态至数据库与进度快照...")
        update_status(
            conn,
            entry_id,
            status="Media_Generated",
            script_json=json.dumps(script_data, ensure_ascii=False),
            raw_assets_dir=asset_dir
        )
        export_progress_json(conn, progress_path)
        print(f"🎉 条目 [{entry_id}] 素材与语音生成完毕！状态: Media_Generated\n")
        return True

    except Exception as e:
        err_msg = f"视觉/音频素材生成异常: {e}"
        print(f"❌ {err_msg}")
        update_status(conn, entry_id, status="Failed", error_message=err_msg, increment_retry=True)
        export_progress_json(conn, progress_path)
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate storyboards, multimodal media, and TTS voiceover.")
    parser.add_argument("--entry-id", type=str, default=None, help="Specific entry ID to process (e.g. 01_001)")
    parser.add_argument("--chapter", type=int, default=None, help="Filter by chapter index")
    parser.add_argument("--status", type=str, default="Pending", help="Filter by current status (default: Pending)")
    parser.add_argument("--limit", type=int, default=1, help="Maximum number of entries to process (default: 1)")
    parser.add_argument("--force", action="store_true", help="Force re-generation even if status is not Pending")
    parser.add_argument("--mock", action="store_true", help="Force mock generator mode without API calls")
    parser.add_argument(
        "--style",
        type=str,
        default="auto",
        help="Visual art style mode: 'auto' (AI autonomous choice, default), 'chapter' (chapter rule-based), or specific ID (25_ghibli, y1_kurzgesagt, y2_vox, 13_pop, 24_hopper, 17_ink, 14_pixel)"
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--progress-path", default=DEFAULT_PROGRESS_PATH, help="Path to progress.json")
    args = parser.parse_args()

    conn = get_connection(args.db_path)

    # Initialize clients
    client = MuseClient(mock=args.mock)
    tts_client = TTSClient()

    if client.mock:
        print("💡 当前运行环境为 [离线/模拟测试模式] (未检测到有效 MUSE_API_KEY 或开启了 --mock 参数)")
    else:
        print(f"🔌 当前已连接 Muse AI API: {client.base_url}")
    print(f"🎙️ 当前已就绪 TTS 语音服务: {tts_client.api_url} [音色: {tts_client.voice}]")
    print(f"🎨 画风配置策略: [{args.style}] ('auto' 为 AI 自主语义决策)")

    if args.entry_id:
        target_entry = get_entry(conn, args.entry_id)
        if not target_entry:
            print(f"❌ 未找到条目: {args.entry_id}")
            sys.exit(1)
        entries_to_process = [target_entry]
    else:
        status_filter = None if args.force else args.status
        entries_to_process = list_entries(conn, status=status_filter, chapter_index=args.chapter, limit=args.limit)

    if not entries_to_process:
        print("ℹ️ 没有符合条件的待处理条目。可通过 --force 或 --status 指定状态。")
        sys.exit(0)

    print(f"📋 即将处理 {len(entries_to_process)} 个条目...")
    success_count = 0

    for entry in entries_to_process:
        success = process_entry(
            entry,
            client,
            tts_client,
            conn,
            args.progress_path,
            force=args.force,
            style_mode=args.style
        )
        if success:
            success_count += 1

    print("-" * 65)
    print(f"🏁 批处理完成: 成功 {success_count} / {len(entries_to_process)} 条")
    print("-" * 65)


if __name__ == "__main__":
    main()
