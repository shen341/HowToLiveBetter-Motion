"""02_ai_generator.py - Storyboard, multimodal assets, and TTS voiceover generation module.

Usage:
    python 02_ai_generator.py --entry-id 01_001
    python 02_ai_generator.py --limit 3
    python 02_ai_generator.py --mock --limit 1
"""

import argparse
import functools
import io
import json
import os
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

from src.config import (
    AI_MODE,
    API_MAX_RETRIES,
    API_TIMEOUT_SECONDS,
    DEFAULT_MOTION_MODE,
    OUTPUT_RAW_ASSETS_DIR,
    RATE_LIMIT_MUSE_RPM,
    RATE_LIMIT_TTS_RPM,
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
from src.cover_generator import CoverGenerator
from src.muse_client import MuseClient, is_i2v_scene, is_whiteboard_scene
from src.srt_generator import SRTGenerator
from src.tts_client import TTSClient
from src.whiteboard.layout_engine import WhiteboardLayoutEngine
from src.whiteboard.hand_compositor import HandCompositor


def process_entry(
    entry: dict,
    client: MuseClient,
    tts_client: TTSClient,
    conn,
    progress_path: str,
    force: bool = False,
    style_mode: str = "auto",
    scenes_count: int = 6,
    motion_mode: str = "static",
    current_index: int = 1,
    total_count: int = 1
) -> bool:
    """Process a single entry: generate storyboard script, visual assets, and synchronized TTS speech."""
    entry_id = entry["id"]
    chapter_title = entry["chapter_title"]
    title = entry["title"]
    item_start_time = time.time()

    if motion_mode == "whiteboard" and style_mode == "auto":
        style_mode = "w1_whiteboard"

    print("=" * 65)
    print(f"🎬 [条目 {current_index}/{total_count}] 正在生成 [{entry_id}] 《{chapter_title}》 - {title}")
    print("=" * 65)

    asset_dir = os.path.join(OUTPUT_RAW_ASSETS_DIR, entry_id)
    os.makedirs(asset_dir, exist_ok=True)
    storyboard_path = os.path.join(asset_dir, "storyboard.json")

    # 1. 生成分镜脚本 (调用 muse-spark 或 mock)
    try:
        t_script = time.time()
        print(f"🧠 [步骤 1/3] 正在调用大模型生成结构化分镜脚本 (画风: {style_mode} | 幕数: {scenes_count} 幕 | 动效: {motion_mode})...")
        script_data = client.generate_script(
            entry, style_mode=style_mode, scene_count=scenes_count, motion_mode=motion_mode
        )
        script_dur = time.time() - t_script

        # 确保视频标题格式统一规范
        expected_title_prefix = f"{chapter_title}之"
        if not script_data.get("video_title", "").startswith(expected_title_prefix):
            script_data["video_title"] = f"{chapter_title}之{title}"

        # 落盘分镜 JSON
        with open(storyboard_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 分镜脚本落盘成功 (耗时 {script_dur:.1f}s): {storyboard_path}")
        print(f"      • 视频标题: {script_data.get('video_title')}")
        print(f"      • 选定艺术画风: {script_data.get('art_style_name')} ({script_data.get('art_style_id')})")
        print(f"      • 风格决策依据: {script_data.get('art_style_reason', 'AI 深度理解内容语义自主决策')}")
        print(f"      • 分镜场景数: {len(script_data.get('scenes', []))} 幕")
        print(f"      • 完整旁白: {script_data.get('narration_text_full')[:50]}...")

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
        total_scenes = len(scenes)
        print(f"🎨 [步骤 2/3] 正在批量生成多模态视觉分镜与 TTS 语音讲解 (共 {total_scenes} 幕)...")

        total_audio_duration = 0.0

        for idx, scene in enumerate(scenes, start=1):
            scene_img_name = f"scene_{idx:02d}.png"
            scene_img_path = os.path.join(asset_dir, scene_img_name)
            prompt = scene.get("image_prompt", "")
            kinetic_word = scene.get("kinetic_typography", {}).get("text", "")
            narration_text = scene.get("narration_segment", "")

            # 2.1 生图与底板准备
            print(f"   🖼️ [分镜 {idx}/{total_scenes}] 浮现字:「{kinetic_word}」 | 旁白: {narration_text[:25]}...")
            wb_layout_info = None
            if is_whiteboard_scene(idx, total_scenes, motion_mode):
                layout_eng = WhiteboardLayoutEngine()
                layout_obj, base_canvas, strokes_list = layout_eng.generate_scene_layout(scene, scene_index=idx)
                wb_layout_info = (layout_obj, base_canvas, strokes_list)
                if not os.path.exists(scene_img_path) or force:
                    base_canvas.save(scene_img_path, quality=95)
                    size_kb = os.path.getsize(scene_img_path) / 1024 if os.path.exists(scene_img_path) else 0
                    print(f"      ✅ 白板米白底板就绪 (大小 {size_kb:.0f}KB) -> {scene_img_name}")
                else:
                    print(f"      ⚡ 白板底板已存在: {scene_img_name}")
                scene["local_image_path"] = scene_img_path
            else:
                if not os.path.exists(scene_img_path) or force:
                    t_img = time.time()
                    print(f"      🎨 正在调用 Muse-Image 绘制 1024x1792 原画...")
                    client.generate_image(prompt, scene_img_path, style_id=style_id)
                    dur_img = time.time() - t_img
                    size_kb = os.path.getsize(scene_img_path) / 1024 if os.path.exists(scene_img_path) else 0
                    print(f"      ✅ 原画绘制就绪 (耗时 {dur_img:.1f}s, 大小 {size_kb:.0f}KB) -> {scene_img_name}")
                else:
                    print(f"      ⚡ 原画素材已存在，跳过重新绘制: {scene_img_name}")
                scene["local_image_path"] = scene_img_path

            # 2.2 生成对应分镜的 TTS 语音 (zh-CN-YunzeNeural)
            voice_name = f"voice_{idx:02d}.mp3"
            voice_path = os.path.join(asset_dir, voice_name)
            if narration_text:
                if not os.path.exists(voice_path) or force:
                    t_tts = time.time()
                    print(f"      🎙️ 正在转换 TTS 讲解语音 (音色: {tts_client.voice})...")
                    audio_dur = tts_client.generate_speech(narration_text, voice_path)
                    dur_tts = time.time() - t_tts
                    scene_dur = round(max(audio_dur + 0.5, 3.0), 2)
                    print(f"      ✅ 语音转换完成 (音频时长 {audio_dur:.2f}s | 耗时 {dur_tts:.1f}s -> 分镜动态时长: {scene_dur:.2f}s)")
                else:
                    from moviepy import AudioFileClip
                    clip = AudioFileClip(voice_path)
                    audio_dur = float(clip.duration)
                    clip.close()
                    scene_dur = round(max(audio_dur + 0.5, 3.0), 2)
                    print(f"      ⚡ 语音文件已存在: {voice_name} (音频时长: {audio_dur:.2f}s -> 分镜动态时长: {scene_dur:.2f}s)")

                scene["local_audio_path"] = voice_path
                scene["audio_duration_sec"] = round(audio_dur, 2)
                scene["duration_sec"] = scene_dur
                total_audio_duration += audio_dur
            else:
                scene["local_audio_path"] = None
                scene["audio_duration_sec"] = 0.0

            # 2.3 动效切片视频生成: 白板流畅书写 (TASK-5.4) vs 图生视频 I2V (TASK-5.0)
            if is_whiteboard_scene(idx, total_scenes, motion_mode):
                video_name = f"motion_{idx:02d}.mp4"
                video_path = os.path.join(asset_dir, video_name)
                if not os.path.exists(video_path) or force:
                    t_vid = time.time()
                    if wb_layout_info is None:
                        layout_eng = WhiteboardLayoutEngine()
                        _, base_canvas, strokes_list = layout_eng.generate_scene_layout(scene, scene_index=idx)
                    else:
                        _, base_canvas, strokes_list = wb_layout_info

                    write_dur = min(max(scene_dur * 0.75, 2.5), 4.5)
                    print(f"      ✍️ [手绘白板] 正在使用纯金属触控笔合成 1080x1920 30fps 流畅写画切片 (书写 {write_dur:.1f}s / 分镜 {scene_dur:.1f}s)...")
                    compositor = HandCompositor()
                    compositor.render_drawing_video(
                        base_canvas=base_canvas,
                        strokes=strokes_list,
                        output_mp4_path=video_path,
                        duration_sec=write_dur,
                        fps=30
                    )
                    dur_vid = time.time() - t_vid
                    v_size_kb = os.path.getsize(video_path) / 1024 if os.path.exists(video_path) else 0
                    print(f"      ✅ 手绘白板流畅切片就绪 (耗时 {dur_vid:.1f}s, 大小 {v_size_kb:.0f}KB) -> {video_name}")
                    scene["local_video_path"] = video_path
                    scene["motion_type_mode"] = "whiteboard"
                else:
                    print(f"      ⚡ 手绘白板视频切片已存在: {video_name}")
                    scene["local_video_path"] = video_path
                    scene["motion_type_mode"] = "whiteboard"

            elif is_i2v_scene(idx, total_scenes, motion_mode):
                video_name = f"motion_{idx:02d}.mp4"
                video_path = os.path.join(asset_dir, video_name)
                video_prompt = scene.get("video_motion_prompt", "Camera quick punch-in zoom onto subject, organic micro motion")
                if not os.path.exists(video_path) or force:
                    t_vid = time.time()
                    print(f"      🎬 [I2V 微动] 正在以首帧原画调用 Muse-Video 驱动 3.0s 物理微动作...")
                    try:
                        client.generate_video(
                            prompt=video_prompt,
                            output_path=video_path,
                            image_path=scene_img_path,
                            duration_sec=3.0
                        )
                        dur_vid = time.time() - t_vid
                        v_size_kb = os.path.getsize(video_path) / 1024 if os.path.exists(video_path) else 0
                        print(f"      ✅ I2V 微动切片就绪 (耗时 {dur_vid:.1f}s, 大小 {v_size_kb:.0f}KB) -> {video_name}")
                        scene["local_video_path"] = video_path
                        scene["motion_type_mode"] = "i2v"
                    except Exception as ve:
                        print(f"      ⚠️ I2V 视频生成异常 ({ve})，自动降级为静态原画 + Ken Burns 模式")
                        scene["local_video_path"] = None
                        scene["motion_type_mode"] = "ken_burns"
                else:
                    print(f"      ⚡ I2V 视频切片已存在: {video_name}")
                    scene["local_video_path"] = video_path
                    scene["motion_type_mode"] = "i2v"
            else:
                scene["local_video_path"] = None
                scene["motion_type_mode"] = "ken_burns"

        # 更新全局目标时长
        script_data["target_duration_sec"] = round(sum(s.get("duration_sec", 6.0) for s in scenes) - (len(scenes) - 1) * 0.5, 2)
        print(f"   📊 全片总净时长 (含转场叠加): {script_data['target_duration_sec']} 秒")

        # 2.3 自动生成 1080x1920 短视频高辨识度专属封面卡片 (TASK-4.1)
        try:
            print("   🖼️ 正在生成短视频专属 1080x1920 封面卡片 (Cover Card)...")
            t_cover = time.time()
            cover_gen = CoverGenerator()
            first_scene_img = scenes[0].get("local_image_path") if scenes else None
            cover_path = cover_gen.generate_cover(
                entry=entry,
                background_image_path=first_scene_img,
                storyboard_data=script_data
            )
            script_data["cover_image_path"] = cover_path
            print(f"      ✅ 封面卡片生成完成 (耗时 {time.time()-t_cover:.1f}s): {cover_path}")
        except Exception as e:
            print(f"      ⚠️ 封面卡片生成轻微异常 (不阻塞主流程): {e}")

        # 更新回写带本地素材路径的 storyboard.json
        with open(storyboard_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)

        # 生成独立分镜 SRT 字幕文件
        raw_srt_path = os.path.join(asset_dir, "subtitles.srt")
        try:
            print("   📝 正在导出独立分镜级 SRT 字幕...")
            SRTGenerator().export_srt(script_data, raw_srt_path)
            print(f"      ✅ 独立分镜 SRT 字幕生成: {raw_srt_path}")
        except Exception as e:
            print(f"      ⚠️ SRT 字幕导出轻微异常 (不阻塞主流程): {e}")

        # 3. 更新状态为 Media_Generated
        print("💾 [步骤 3/3] 更新条目状态至数据库与进度快照...")
        update_status(
            conn,
            entry_id,
            status="Media_Generated",
            script_json=json.dumps(script_data, ensure_ascii=False),
            raw_assets_dir=asset_dir
        )
        export_progress_json(conn, progress_path)
        item_total_dur = time.time() - item_start_time
        print(f"🎉 [条目 {current_index}/{total_count}] 条目 [{entry_id}] 素材与语音全部就绪！(耗时: {item_total_dur:.1f}s) 状态: Media_Generated\n")
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
    parser.add_argument(
        "--scenes",
        type=int,
        default=6,
        choices=[4, 6, 8],
        help="Number of storyboard scenes (default: 6 for Golden 6 Scenes)"
    )
    parser.add_argument(
        "--rpm-muse",
        type=int,
        default=RATE_LIMIT_MUSE_RPM,
        help=f"Max requests per minute for Muse AI (default: {RATE_LIMIT_MUSE_RPM})"
    )
    parser.add_argument(
        "--rpm-tts",
        type=int,
        default=RATE_LIMIT_TTS_RPM,
        help=f"Max requests per minute for Cloudflare TTS (default: {RATE_LIMIT_TTS_RPM})"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=API_MAX_RETRIES,
        help=f"Max retries for transient API errors with backoff (default: {API_MAX_RETRIES})"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=API_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds to prevent blocking indefinitely (default: {API_TIMEOUT_SECONDS}s)"
    )
    parser.add_argument(
        "--motion-mode",
        type=str,
        default=DEFAULT_MOTION_MODE,
        choices=["static", "i2v-tier1", "i2v-all", "whiteboard"],
        help=f"Motion mode: 'static' (Ken Burns only), 'i2v-tier1' (Scenes 1 & 5 I2V), 'i2v-all' (All 6 scenes I2V), 'whiteboard' (Smooth handdrawn whiteboard animation). Default: {DEFAULT_MOTION_MODE}"
    )
    parser.add_argument(
        "--ai-mode",
        type=str,
        default=AI_MODE,
        choices=["hybrid", "local", "cloud"],
        help=f"AI execution architecture: 'hybrid' (Gemini script + local ComfyUI), 'local' (Ollama + ComfyUI), 'cloud' (Muse/YourselfAI). Default: {AI_MODE}"
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--progress-path", default=DEFAULT_PROGRESS_PATH, help="Path to progress.json")
    args = parser.parse_args()

    conn = get_connection(args.db_path)

    # Initialize clients with rate limiting and exponential backoff
    client = MuseClient(
        ai_mode=args.ai_mode,
        mock=args.mock,
        rate_limit_rpm=args.rpm_muse,
        max_retries=args.max_retries,
        timeout=args.timeout,
    )
    tts_client = TTSClient(
        rate_limit_rpm=args.rpm_tts,
        max_retries=args.max_retries,
    )

    if client.mock:
        print("💡 当前运行环境为 [离线/模拟测试模式] (未检测到有效 API 密钥或开启了 --mock 参数)")
    elif client.ai_mode == "hybrid":
        comfy_status = "🟢 已就绪" if client.local_image_client.is_available() else "⚪ 未启动 (自动云端容灾)"
        print(f"🌟 当前运行架构为 [黄金混合模式] (AI_MODE=hybrid)")
        print(f"   • 阶段一 爆款文案/分镜: 云端 {client.text_model} (极速 1.5s 绝无重复)")
        print(f"   • 阶段二 语音解说: 保持免费极速 Edge-TTS ({tts_client.voice})")
        print(f"   • 阶段三 本地艺术原画: ComfyUI [{comfy_status}] ({client.local_image_client.base_url})")
    elif client.ai_mode == "local":
        comfy_status = "🟢 已就绪" if client.local_image_client.is_available() else "⚪ 未启动 (自动云端容灾)"
        print(f"🏠 当前运行架构为 [本地私有化 AI 模式] (AI_MODE=local)")
        print(f"   • 阶段一 本地大模型: {client.base_url} [模型: {client.text_model}]")
        print(f"   • 阶段二 语音解说: 保持免费极速 Edge-TTS ({tts_client.voice})")
        print(f"   • 阶段三 本地艺术原画: ComfyUI [{comfy_status}] ({client.local_image_client.base_url})")
    else:
        print(f"☁️ 当前运行架构为 [云端 API 模式] (AI_MODE=cloud)")
        print(f"   • 阶段一 云端大模型: {client.base_url} [模型: {client.text_model}] [速率限额: {args.rpm_muse} RPM]")

        print(f"   • 阶段二 语音解说: 保持免费极速 Edge-TTS ({tts_client.voice})")
        print(f"   • 阶段三 云端艺术原画: Muse-Image 1024x1792")

    if client.fallback_client:
        print(f"🛡️ 备选容灾路线已就绪: {client.fallback_base_url} [生图: {client.fallback_image_model} | 文本: {client.fallback_text_model}]")
    else:
        print("ℹ️ 备选生图路线未启用 (如需开启请在 .env 中设置 YOURSELFAI_API_KEY)")
    print(f"🎙️ 当前已就绪 TTS 语音服务: {tts_client.api_url} [音色: {tts_client.voice} | 限额: {args.rpm_tts} RPM]")
    print(f"🔄 瞬时异常容灾机制: 开启指数退避重试 (最大 {args.max_retries} 次重试, 2s -> 4s -> 8s)")
    print(f"🎨 画风配置策略: [{args.style}] ('auto' 为 AI 自主语义决策)")

    print(f"🎬 场景分镜规范: [{args.scenes} 幕] (黄金叙事脉冲节奏)")
    if args.motion_mode == "static":
        print(f"🎞️ 动效模式: [static] (纯Ken Burns镜头推拉，不调用I2V视频API，处理速度最快)")
    elif args.motion_mode == "i2v-tier1":
        print(f"🎞️ 动效模式: [i2v-tier1] (第1/5幕物理微动，平衡速度与视觉冲击力)")
    elif args.motion_mode == "whiteboard":
        print(f"✍️ 动效模式: [whiteboard] (极简手绘白板流畅全动效，纯触控笔写画，留白率>=65%)")
    else:
        print(f"🎞️ 动效模式: [i2v-all] (全片6幕微动，调用量大耗时较长)")

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

    total_count = len(entries_to_process)
    print(f"📋 即将批量处理 {total_count} 个条目...")
    success_count = 0
    batch_start_time = time.time()

    for idx, entry in enumerate(entries_to_process, start=1):
        success = process_entry(
            entry,
            client,
            tts_client,
            conn,
            args.progress_path,
            force=args.force,
            style_mode=args.style,
            scenes_count=args.scenes,
            motion_mode=args.motion_mode,
            current_index=idx,
            total_count=total_count
        )
        if success:
            success_count += 1

    batch_elapsed = time.time() - batch_start_time
    print("-" * 65)
    print(f"🏁 批处理完成: 成功 {success_count} / {total_count} 条 (总耗时: {batch_elapsed:.1f}s)")
    print("-" * 65)


if __name__ == "__main__":
    main()
