"""04_review_dashboard.py - Lightweight Web Review Dashboard for HowToLiveBetter-Motion.

A local Streamlit-based review dashboard for creators and engineers to:
1. Review generated vertical videos (1080x1920), covers, and standalone SRT subtitles.
2. Inspect storyboard scenes, high-res keyframe art, TTS voiceover, and I2V micro-motion clips.
3. Manage workflow status: Mark Approved, Request Revision, or Reset for re-generation.
4. Filter by status, chapter, evidence grade, and keywords across all 677 entries.

Usage:
    streamlit run 04_review_dashboard.py
    python 04_review_dashboard.py  (auto-launches streamlit)
"""

import io
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# UTF-8 stdout configuration for Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
except (AttributeError, io.UnsupportedOperation):
    pass

import streamlit as st
from src.config import (
    DEFAULT_PLATFORM_PRESET,
    OUTPUT_FINAL_VIDEOS_DIR,
    OUTPUT_RAW_ASSETS_DIR,
)
from src.db import (
    DEFAULT_DB_PATH,
    DEFAULT_PROGRESS_PATH,
    export_progress_json,
    get_connection,
    get_entry,
    get_statistics,
    list_entries,
    mark_approved,
    reset_entry,
    update_status,
)


def get_entry_assets(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve all associated physical assets (video, cover, SRT, storyboard) for an entry."""
    entry_id = entry["id"]
    raw_dir = entry.get("raw_assets_dir") or os.path.join(OUTPUT_RAW_ASSETS_DIR, entry_id)

    # 1. Final video MP4
    video_path = entry.get("final_video_path")
    if not video_path or not os.path.exists(video_path):
        video_path = None
        if os.path.exists(OUTPUT_FINAL_VIDEOS_DIR):
            for fname in os.listdir(OUTPUT_FINAL_VIDEOS_DIR):
                if fname.startswith(f"{entry_id}_") and fname.endswith(".mp4"):
                    candidate = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, fname)
                    if os.path.exists(candidate) and os.path.getsize(candidate) > 1024:
                        video_path = candidate
                        break

    # 2. Cover image (final_videos or raw_assets)
    cover_path = None
    if os.path.exists(OUTPUT_FINAL_VIDEOS_DIR):
        for fname in os.listdir(OUTPUT_FINAL_VIDEOS_DIR):
            if fname.startswith(f"{entry_id}_") and fname.endswith("_cover.png"):
                cover_path = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, fname)
                break
    if not cover_path:
        raw_cover = os.path.join(raw_dir, "cover.png")
        if os.path.exists(raw_cover):
            cover_path = raw_cover

    # 3. Subtitles SRT (final_videos or raw_assets)
    srt_path = None
    if os.path.exists(OUTPUT_FINAL_VIDEOS_DIR):
        for fname in os.listdir(OUTPUT_FINAL_VIDEOS_DIR):
            if fname.startswith(f"{entry_id}_") and fname.endswith(".srt"):
                srt_path = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, fname)
                break
    if not srt_path:
        raw_srt = os.path.join(raw_dir, "subtitles.srt")
        if os.path.exists(raw_srt):
            srt_path = raw_srt

    # 4. Storyboard JSON
    storyboard = None
    storyboard_path = os.path.join(raw_dir, "storyboard.json")
    if os.path.exists(storyboard_path):
        try:
            with open(storyboard_path, "r", encoding="utf-8") as f:
                storyboard = json.load(f)
        except Exception:
            pass

    # 5. Copywriting JSON & TXT (TASK-5.2)
    copywriting = None
    copy_json_path = os.path.join(raw_dir, "copywriting.json")
    if os.path.exists(copy_json_path):
        try:
            with open(copy_json_path, "r", encoding="utf-8") as f:
                copywriting = json.load(f)
        except Exception:
            pass

    return {
        "raw_dir": raw_dir,
        "video_path": video_path,
        "cover_path": cover_path,
        "srt_path": srt_path,
        "storyboard": storyboard,
        "copywriting": copywriting,
    }


def render_dashboard():
    """Main Streamlit application layout and logic."""
    st.set_page_config(
        page_title="HowToLiveBetter-Motion 审核看板",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom styling
    st.markdown("""
        <style>
        .metric-card {
            background-color: #1e2530;
            border-radius: 10px;
            padding: 14px 18px;
            border: 1px solid #2e3846;
        }
        .status-pill {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 600;
        }
        .pill-completed { background-color: #2e7d32; color: #fff; }
        .pill-approved { background-color: #f59e0b; color: #111; font-weight: bold; }
        .pill-media { background-color: #0284c7; color: #fff; }
        .pill-pending { background-color: #4b5563; color: #fff; }
        .pill-failed { background-color: #dc2626; color: #fff; }
        .pill-revision { background-color: #9333ea; color: #fff; }
        </style>
    """, unsafe_allow_html=True)

    conn = get_connection()

    # 1. Header Banner
    st.title("🎬 HowToLiveBetter-Motion 视频审核看板")
    st.caption("《高性价比生活指南》短视频工业化流水线 · 创作者人机协作与全生命周期质检平台")

    # 2. Global KPIs
    stats = get_statistics(conn)
    total_entries = stats.get("total_entries", 677)
    summary = stats.get("status_summary", {})
    completed_cnt = summary.get("Completed", 0)
    approved_cnt = summary.get("Approved", 0)
    media_cnt = summary.get("Media_Generated", 0)
    pending_cnt = summary.get("Pending", 0)
    failed_cnt = summary.get("Failed", 0)
    revision_cnt = summary.get("Needs_Revision", 0)

    delivered_total = completed_cnt + approved_cnt
    progress_ratio = delivered_total / max(total_entries, 1)

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("📚 总条目库", f"{total_entries}")
    kpi2.metric("⭐ 审核通过", f"{approved_cnt}", help="已由创作者确认并审核通过的成片")
    kpi3.metric("🎬 成片已合成", f"{completed_cnt}", help="流水线已导出 MP4 成片的条目")
    kpi4.metric("🎨 素材已就绪", f"{media_cnt}", help="分镜原画与 TTS 语音已就绪")
    kpi5.metric("⏳ 待跑批队列", f"{pending_cnt}", help="尚未开始生成分镜与素材")
    kpi6.metric("⚠️ 需修订/失败", f"{revision_cnt + failed_cnt}", help="生成失败或被创作者标记需重抽")

    st.progress(min(max(progress_ratio, 0.0), 1.0), text=f"交付完成率: {progress_ratio*100:.1f}% ({delivered_total} / {total_entries} 条成片就绪)")

    st.markdown("---")

    # 3. Sidebar Filters & Navigation
    st.sidebar.header("🔍 检索与筛选矩阵")

    # Status filter
    status_options = ["全部 (All)", "⭐ Approved (已审核)", "✅ Completed (已成片)", "🎨 Media_Generated (素材就绪)", "⏳ Pending (待处理)", "📝 Needs_Revision (需修订)", "❌ Failed (失败)"]
    status_map = {
        "⭐ Approved (已审核)": "Approved",
        "✅ Completed (已成片)": "Completed",
        "🎨 Media_Generated (素材就绪)": "Media_Generated",
        "⏳ Pending (待处理)": "Pending",
        "📝 Needs_Revision (需修订)": "Needs_Revision",
        "❌ Failed (失败)": "Failed",
    }
    selected_status_display = st.sidebar.selectbox("条目处理状态", status_options, index=0)
    status_filter = status_map.get(selected_status_display)

    # Chapter filter
    chapters = stats.get("chapters", [])
    chapter_options = ["全部章节 (All Chapters)"] + [f"第 {c['chapter_index']:02d} 章: {c['chapter_title']} ({c['completed_items']}/{c['total_items']})" for c in chapters]
    selected_chapter_display = st.sidebar.selectbox("所属章节", chapter_options, index=0)
    chapter_filter = None
    if selected_chapter_display != "全部章节 (All Chapters)":
        chapter_filter = int(selected_chapter_display.split("第 ")[1].split(" 章")[0])

    # Search keyword
    search_keyword = st.sidebar.text_input("关键词搜索 (ID / 标题)", placeholder="例如: 01_001 或 安全带").strip()

    # Query entries
    all_matched = list_entries(conn, status=status_filter, chapter_index=chapter_filter)
    if search_keyword:
        kw = search_keyword.lower()
        all_matched = [e for e in all_matched if kw in e["id"].lower() or kw in e["title"].lower() or kw in (e["plain_text"] or "").lower()]

    st.sidebar.caption(f"当前条件共检索到 **{len(all_matched)}** 条匹配条目")

    if not all_matched:
        st.warning("⚠️ 没有找到符合筛选条件的条目。请调整左侧筛选器。")
        return

    # Entry selector format helper
    def format_entry_label(e: Dict[str, Any]) -> str:
        s = e.get("status", "Pending")
        emoji = "⏳"
        if s == "Approved":
            emoji = "⭐"
        elif s == "Completed":
            emoji = "✅"
        elif s == "Media_Generated":
            emoji = "🎨"
        elif s == "Failed":
            emoji = "❌"
        elif s == "Needs_Revision":
            emoji = "📝"
        return f"{emoji} [{e['id']}] 《{e['chapter_title']}》 - {e['title'][:20]}"

    entry_selector = st.sidebar.selectbox(
        "选择待审核条目",
        options=all_matched,
        format_func=format_entry_label,
        index=0
    )

    if not entry_selector:
        return

    # 4. Main Entry Detail View
    entry = entry_selector
    entry_id = entry["id"]
    assets = get_entry_assets(entry)

    # Entry Title Banner
    badge_html = f"<span class='status-pill pill-{entry['status'].lower()}'>{entry['status']}</span>"
    st.markdown(f"### [{entry_id}] {entry['chapter_title']} · {entry['title']} {badge_html}", unsafe_allow_html=True)

    # Metadata badges
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    grade = entry.get("evidence_grade") or "A"
    col_m1.info(f"🏅 **证据等级**: {grade} 级")
    col_m2.info(f"💰 **金钱成本**: {entry.get('cost_money') or '0'}")
    col_m3.info(f"⏱️ **时间代价**: {entry.get('cost_time') or '极少'}")
    col_m4.info(f"🧠 **意志力代价**: {entry.get('cost_willpower') or '低'}")
    col_m5.success(f"📈 **核心收益**: {entry.get('benefit_metric') or entry.get('benefit_level') or '显著'}")

    st.markdown(" ")

    # Two-Column Layout
    col_left, col_right = st.columns([4, 6])

    # Left Column: Video Delivery & Assets
    with col_left:
        st.subheader("🎥 交付成片与视听播放")
        video_path = assets.get("video_path")

        if video_path and os.path.exists(video_path):
            st.video(video_path)
            v_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            st.success(f"✅ **成片就绪**: `{os.path.basename(video_path)}` ({v_size_mb:.2f} MB)")
            with open(video_path, "rb") as vf:
                st.download_button(
                    label="⬇️ 下载成片 MP4",
                    data=vf.read(),
                    file_name=os.path.basename(video_path),
                    mime="video/mp4",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ 当前条目尚未渲染导出最终 MP4 成片。")
            if entry["status"] in ("Media_Generated", "Pending"):
                st.info("💡 素材已准备完毕，可在下方点击「立即装配成片」或通过命令行执行 `03_video_assembler.py`。")

        st.markdown("---")
        st.subheader("🖼️ 专属竖屏封面卡片")
        cover_path = assets.get("cover_path")
        if cover_path and os.path.exists(cover_path):
            st.image(cover_path, caption=f"发布专属封面: {os.path.basename(cover_path)}", use_container_width=True)
            with open(cover_path, "rb") as cf:
                st.download_button(
                    label="⬇️ 下载发布首图 PNG",
                    data=cf.read(),
                    file_name=os.path.basename(cover_path),
                    mime="image/png",
                    use_container_width=True
                )
        else:
            st.info("ℹ️ 尚未生成专属封面卡片。")

        st.markdown("---")
        st.subheader("📝 独立外挂 SRT 字幕")
        srt_path = assets.get("srt_path")
        if srt_path and os.path.exists(srt_path):
            with open(srt_path, "r", encoding="utf-8", errors="ignore") as sf:
                srt_content = sf.read()
            st.download_button(
                label="⬇️ 下载配套软字幕 SRT (剪映开箱即用)",
                data=srt_content,
                file_name=os.path.basename(srt_path),
                mime="text/plain",
                use_container_width=True
            )
            with st.expander("查看 SRT 时间轴明细"):
                st.text(srt_content[:1500] + ("\n...(更多已截断)" if len(srt_content) > 1500 else ""))
        else:
            st.info("ℹ️ 尚未导出独立 SRT 字幕。")

    # Right Column: Storyboard, Art Style & Multimodal Inspection
    with col_right:
        st.subheader("🎨 分镜脚本与多模态素材质检")
        storyboard = assets.get("storyboard")

        if storyboard:
            style_name = storyboard.get("art_style_name", "吉卜力暖调手绘风")
            style_id = storyboard.get("art_style_id", "25_ghibli")
            style_reason = storyboard.get("art_style_reason", "AI 自主语义识别决策")
            target_dur = storyboard.get("target_duration_sec", 30)

            st.markdown(f"**艺术风格**: `{style_name}` (`{style_id}`) | **全片净时长**: `{target_dur}s`")
            st.caption(f"🧠 **AI 选风决策依据**: {style_reason}")

            scenes = storyboard.get("scenes", [])
            st.write(f"**分镜幕数**: 共 {len(scenes)} 幕黄金叙事脉冲")

            tabs = st.tabs([f"第 {s.get('scene_index', i+1)} 幕" for i, s in enumerate(scenes)])
            for idx, (tab, scene) in enumerate(zip(tabs, scenes), start=1):
                with tab:
                    scene_idx = scene.get("scene_index", idx)
                    kinetic = scene.get("kinetic_typography", {}).get("text", "")
                    dur_sec = scene.get("duration_sec", 5.0)
                    audio_dur = scene.get("audio_duration_sec", 0.0)

                    st.markdown(f"#### 第 {scene_idx} 幕 · 浮现大字: 「<span style='color:#f59e0b;'>{kinetic}</span>」 ({dur_sec:.1f}s)", unsafe_allow_html=True)
                    st.write(f"🎙️ **口播旁白**: {scene.get('narration_segment', '')}")

                    # Voice Audio Player
                    audio_path = scene.get("local_audio_path")
                    if audio_path and os.path.exists(audio_path):
                        st.audio(audio_path)
                        st.caption(f"TTS 音频时长: {audio_dur:.2f}s | 画面展示时长: {dur_sec:.2f}s (以声定景已对齐)")

                    # Visual Asset Display
                    col_s_img, col_s_motion = st.columns(2)
                    with col_s_img:
                        img_path = scene.get("local_image_path")
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, caption=f"首帧原画: scene_{scene_idx:02d}.png", use_container_width=True)
                        else:
                            st.caption("原画图像文件未找到")

                    with col_s_motion:
                        vid_path = scene.get("local_video_path")
                        motion_mode = scene.get("motion_type_mode", "ken_burns")
                        if vid_path and os.path.exists(vid_path):
                            st.success("🎞️ **I2V 物理微动作已生成** (Freeze-and-Drift 缓动)")
                            st.video(vid_path)
                            st.caption(f"动量控制 Prompt: `{scene.get('video_motion_prompt', '')}`")
                        else:
                            st.info("🖼️ **Ken Burns 2D 镜头运镜** (平移/推拉/交叉溶解)")
                            st.caption(f"视觉动作规划: {scene.get('visual_action', '平移推拉')}")
                            if scene.get("video_motion_prompt"):
                                st.caption(f"预留微动 Prompt: `{scene.get('video_motion_prompt')}`")
        else:
            st.warning("⚠️ 尚未检测到 `storyboard.json` 分镜脚本。可在下方通过命令行生成。")

        # Multi-Platform Copywriting Section (TASK-5.2)
        st.markdown("---")
        st.subheader("📢 多平台爆款营销文案与标签")
        copywriting = assets.get("copywriting")
        if not copywriting:
            col_gen_copy, _ = st.columns([5, 5])
            if col_gen_copy.button("✨ 立即生成多平台文案 (小红书/抖音/视频号)", use_container_width=True):
                from src.copywriter import Copywriter
                cw = Copywriter(mock=False)
                clean_name = f"{entry_id}_{entry['chapter_title']}之{entry['title']}"
                raw_json = os.path.join(assets["raw_dir"], "copywriting.json")
                final_txt = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, f"{clean_name}_copywriting.txt")
                copywriting = cw.generate_copywriting(entry, storyboard=storyboard, output_json_path=raw_json, output_txt_path=final_txt)
                st.success("🎉 多平台营销文案生成成功！")
                st.rerun()
        else:
            c_tab1, c_tab2, c_tab3 = st.tabs(["📕 小红书专属", "🎵 抖音短视频", "🟢 微信视频号"])
            with c_tab1:
                xhs = copywriting.get("xhs", {})
                st.markdown("**【爆款候选标题】**")
                for i, t in enumerate(xhs.get("title_candidates", []), 1):
                    st.code(t, language="text")
                st.markdown("**【正文干货与导语】**")
                st.text_area("📱 小红书发布正文 (一键全选复制)", value=xhs.get("full_post", ""), height=220, key=f"xhs_{entry_id}")
                st.caption("🏷️ **推荐标签**: " + " ".join([f"`{t}`" for t in xhs.get("tags", [])]))

            with c_tab2:
                dy = copywriting.get("douyin", {})
                st.markdown(f"**视频展示标题**: `{dy.get('title', '')}`")
                st.markdown(f"**黄金 3 秒完播钩子**: `{dy.get('hook', '')}`")
                st.text_area("🎵 抖音视频描述", value=dy.get("caption", ""), height=100, key=f"dy_{entry_id}")
                st.caption("🏷️ **热门话题**: " + " ".join([f"`{t}`" for t in dy.get("tags", [])]))

            with c_tab3:
                wx = copywriting.get("wechat", {})
                st.markdown(f"**视频号公信力标题**: `{wx.get('title', '')}`")
                st.text_area("🟢 朋友圈 / 社群转发推荐语", value=wx.get("share_text", ""), height=120, key=f"wx_{entry_id}")
                st.caption("🏷️ **话题标签**: " + " ".join([f"`{t}`" for t in wx.get("tags", [])]))

        # Knowledge Source Info
        st.markdown("---")
        with st.expander("📖 查阅知识库原文与论证细节", expanded=False):
            st.markdown(f"**建议标题**: {entry.get('title')}")
            st.markdown(f"**论据原文**: {entry.get('plain_text') or entry.get('raw_content')}")
            if entry.get("notes"):
                st.markdown(f"**审核批注/备注**: {entry.get('notes')}")

    # 5. Reviewer Workflow Action Toolbox
    st.markdown("---")
    st.subheader("🛠️ 创作者人机审核与工单流转")

    act_col1, act_col2, act_col3 = st.columns([3, 4, 3])

    with act_col1:
        st.markdown("##### 1. 确认审核状态")
        if st.button("⭐ 审核通过 (Mark Approved)", type="primary", use_container_width=True):
            mark_approved(conn, entry_id)
            export_progress_json(conn, DEFAULT_PROGRESS_PATH)
            st.balloons()
            st.success(f"🎉 条目 [{entry_id}] 已标记为 Approved 审核通过！")
            st.rerun()

        if entry["status"] == "Approved":
            st.caption("✅ 当前条目已处于 Approved 状态，已归入发布就绪资产包。")

    with act_col2:
        st.markdown("##### 2. 填写修订意见 / 重抽批注")
        rev_notes = st.text_input("修订要求 (例如: 原画第3幕主体不清晰，需重抽)", value=entry.get("notes") or "", key=f"note_{entry_id}")
        if st.button("📝 标记需修订 (Needs Revision)", use_container_width=True):
            update_status(conn, entry_id, status="Needs_Revision")
            if rev_notes:
                with conn:
                    conn.execute("UPDATE entries SET notes = ? WHERE id = ?", (rev_notes, entry_id))
            export_progress_json(conn, DEFAULT_PROGRESS_PATH)
            st.warning(f"⚠️ 条目 [{entry_id}] 已标记为 Needs_Revision！批注已记录。")
            st.rerun()

    with act_col3:
        st.markdown("##### 3. 重置流水线状态")
        reset_target = st.selectbox("重置目标阶段", ["Pending (完全重做)", "Script_Generated (保留脚本重做素材)", "Media_Generated (仅重装视频)"], index=0)
        target_map = {
            "Pending (完全重做)": "Pending",
            "Script_Generated (保留脚本重做素材)": "Script_Generated",
            "Media_Generated (仅重装视频)": "Media_Generated",
        }
        if st.button("🔄 重置当前条目状态", use_container_width=True):
            st_val = target_map[reset_target]
            clear_all = (st_val == "Pending")
            reset_entry(conn, entry_id, target_status=st_val, clear_assets=clear_all)
            export_progress_json(conn, DEFAULT_PROGRESS_PATH)
            st.info(f"🔄 条目 [{entry_id}] 状态已重置为 {st_val}！")
            st.rerun()


if __name__ == "__main__":
    # If executed directly with python, automatically launch Streamlit
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        is_streamlit = get_script_run_ctx() is not None
    except Exception:
        is_streamlit = False

    if is_streamlit:
        render_dashboard()
    else:
        print("🚀 检测到直接调用 Python，正在为您启动 Streamlit 审核看板...")
        print(f"👉 访问地址: http://localhost:8501")
        cmd = [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)] + sys.argv[1:]
        subprocess.run(cmd)
