"""Copywriting and social media hashtag generation engine for HowToLiveBetter-Motion (TASK-5.2 / ADR-014).

Generates multi-platform copy adapted to:
1. Xiaohongshu (XHS): Catchy emoji titles, pain-point hooks, structured bullet notes, high-ranking tags.
2. Douyin: Ultra-punchy 3s retention hooks, concise title (<20 chars), high-traffic tags.
3. WeChat Channels: Authoritative, gentle shareable text for family/Moments circles.
"""

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# UTF-8 stdout configuration for Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
except (AttributeError, io.UnsupportedOperation):
    pass

from src.config import (
    MODEL_TEXT,
    OUTPUT_FINAL_VIDEOS_DIR,
    OUTPUT_RAW_ASSETS_DIR,
)
from src.db import (
    DEFAULT_DB_PATH,
    get_connection,
    get_entry,
    list_entries,
)
from src.muse_client import MuseClient
from src.rate_limiter import retry_with_backoff


def build_copywriting_prompt(entry: Dict[str, Any], storyboard: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """Build system and user prompts for multi-platform copywriting generation."""
    system_prompt = """你是一位精通小红书（爆款种草）、抖音（完播率算法）与微信视频号（熟人社交裂变）的顶级短视频营销文案专家。
你的任务是将提供的硬核生活健康指南条目，转化为一套多平台适配的爆款发布文案、标题矩阵与高权重标签。

【平台风格规范】
1. 小红书 (Xiaohongshu):
   - 标题候选：生成 3 个备选标题（20字以内），带情绪 Emoji，痛点反问/颠覆常识/数值量化，极具点击冲动。
   - 导语：直击日常普遍误区或隐形盲点，语气真诚亲切。
   - 正文干货：结构清晰，使用 📌、💡、⚠️、💰 等符号分点列出机理、真实证据与代价对比。
   - 行动呼吁 (CTA)：引导点赞收藏，温情呼吁转发给最在乎的亲友。
   - 标签矩阵：6~8 个垂直高权重 Hashtags（如 #生活百科 #硬核科普 #高性价比生活）。
2. 抖音 (Douyin):
   - 视频标题：精炼短标题（18字以内），适合信息流大字呈现。
   - 黄金 3 秒完播文案 (Hook)：一句话勾起好奇心，阻止下滑。
   - 视频描述：带 3~4 个高频热门话题。
3. 微信视频号 (WeChat Channels):
   - 标题：沉稳大方、高公信力。
   - 推荐转发语：适合转发相亲相爱一家人或朋友圈的温和科普金句。

【输出格式要求】
必须严格输出纯 JSON，切勿包含任何额外 Markdown 问候语：
{
  "xhs": {
    "title_candidates": ["标题1", "标题2", "标题3"],
    "intro": "导语文案...",
    "body_points": ["核心点1", "核心点2", "核心点3"],
    "call_to_action": "呼吁行动文案...",
    "tags": ["#生活百科", "#硬核科普"]
  },
  "douyin": {
    "title": "精炼标题",
    "hook": "黄金3秒钩子文案",
    "caption": "完整视频描述文案",
    "tags": ["#涨知识", "#硬核科普"]
  },
  "wechat": {
    "title": "视频号公信力标题",
    "share_text": "朋友圈/群转发推荐语",
    "tags": ["#生活智慧", "#健康守护"]
  }
}
"""

    chapter_title = entry.get("chapter_title", "生活指南")
    item_title = entry.get("title", "健康安全建议")
    plain_text = entry.get("plain_text") or entry.get("raw_content") or ""
    cost_desc = entry.get("cost_desc", "几乎不花钱")
    benefit_desc = entry.get("benefit_desc", "显著降低风险")
    evidence_grade = entry.get("evidence_grade", "A")

    user_prompt = f"""【条目基础信息】
- 专栏章节：《{chapter_title}》
- 核心标题：{item_title}
- 证据等级：{evidence_grade} 级硬核循证
- 执行代价：{cost_desc}
- 核心收益：{benefit_desc}
- 原文详情：
{plain_text[:400]}

请根据以上知识点，为该条目生成小红书、抖音与微信视频号的三平台爆款文案 JSON。
"""
    return system_prompt, user_prompt


class Copywriter:
    """Multi-platform copywriting and tag generator engine."""

    def __init__(self, client: Optional[MuseClient] = None, mock: bool = False):
        self.client = client or MuseClient(mock=mock)
        self.mock = self.client.mock or mock

    def generate_copywriting(
        self,
        entry: Dict[str, Any],
        storyboard: Optional[Dict[str, Any]] = None,
        output_json_path: Optional[str] = None,
        output_txt_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate platform copy, save to JSON/TXT, and return structured dictionary."""
        entry_id = entry.get("id", "01_001")
        item_title = entry.get("title", "生活指南建议")

        if self.mock:
            copy_data = self._mock_copywriting_generation(entry, storyboard)
        else:
            system_prompt, user_prompt = build_copywriting_prompt(entry, storyboard)

            def _do_generate():
                return self.client.client.chat.completions.create(
                    model=MODEL_TEXT,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7
                )

            try:
                response = retry_with_backoff(
                    _do_generate,
                    max_retries=self.client.max_retries,
                    initial_delay=self.client.retry_delay,
                    service_name="Muse-Spark-Copywriter",
                    limiter=self.client.limiter,
                )
                raw_content = response.choices[0].message.content
                copy_data = self._clean_and_parse_json(raw_content, entry, storyboard)
            except Exception as e:
                print(f"⚠️ Live copywriting generation failed ({e}), falling back to structured templates...")
                copy_data = self._mock_copywriting_generation(entry, storyboard)

        copy_data["entry_id"] = entry_id
        copy_data["title"] = item_title
        copy_data["generated_at"] = datetime.now().isoformat()

        # Build composite formatted text for Xiaohongshu
        xhs = copy_data.get("xhs", {})
        full_xhs_post = self._format_xhs_full_post(entry, xhs)
        copy_data["xhs"]["full_post"] = full_xhs_post

        # Save artifacts if requested
        if output_json_path:
            os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(copy_data, f, ensure_ascii=False, indent=2)

        if output_txt_path:
            os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
            formatted_text = self.format_all_platforms_text(entry, copy_data)
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(formatted_text)

        return copy_data

    def _format_xhs_full_post(self, entry: Dict[str, Any], xhs: Dict[str, Any]) -> str:
        """Format a ready-to-copy Xiaohongshu post with title, body points, CTA, and tags."""
        titles = xhs.get("title_candidates", [])
        chosen_title = titles[0] if titles else f"关于{entry.get('title')}，很多人都做错了⚠️"
        intro = xhs.get("intro", "")
        body_points = xhs.get("body_points", [])
        cta = xhs.get("call_to_action", "用最少代价换最大确定性，转给在乎的人！")
        tags = " ".join(xhs.get("tags", ["#生活百科", "#硬核科普", "#高性价比生活"]))

        points_text = "\n".join([f"📌 {pt}" for pt in body_points])

        return f"""{chosen_title}

{intro}

{points_text}

💡 {cta}

{tags}"""

    def format_all_platforms_text(self, entry: Dict[str, Any], copy_data: Dict[str, Any]) -> str:
        """Render beautiful, clearly separated multi-platform text for human creators."""
        entry_id = entry.get("id", "")
        chapter_title = entry.get("chapter_title", "")
        title = entry.get("title", "")
        xhs = copy_data.get("xhs", {})
        douyin = copy_data.get("douyin", {})
        wechat = copy_data.get("wechat", {})

        xhs_titles = "\n".join([f"  备选 {i+1}：{t}" for i, t in enumerate(xhs.get("title_candidates", []))])
        xhs_points = "\n".join([f"  • {p}" for p in xhs.get("body_points", [])])
        xhs_tags = " ".join(xhs.get("tags", []))

        douyin_tags = " ".join(douyin.get("tags", []))
        wechat_tags = " ".join(wechat.get("tags", []))

        return f"""======================================================================
📢 《{chapter_title}》之 {title} [{entry_id}] · 多平台发布营销文案
======================================================================

----------------------------------------------------------------------
📕【小红书专属种草发布文案 (Xiaohongshu)】
----------------------------------------------------------------------
【爆款候选标题】
{xhs_titles}

【推荐导语】
{xhs.get('intro', '')}

【正文干货要点】
{xhs_points}

【行动呼吁 (CTA)】
{xhs.get('call_to_action', '')}

【高权重话题标签】
{xhs_tags}

【📱 小红书一键全选复制排版】：
{xhs.get('full_post', '')}

----------------------------------------------------------------------
🎵【抖音短视频发布文案 (Douyin)】
----------------------------------------------------------------------
【视频展示标题】：{douyin.get('title', '')}
【黄金 3 秒完播钩子】：{douyin.get('hook', '')}
【视频描述文案】：{douyin.get('caption', '')}
【热门话题】：{douyin_tags}

----------------------------------------------------------------------
🟢【微信视频号/社群发布文案 (WeChat Channels)】
----------------------------------------------------------------------
【公信力标题】：{wechat.get('title', '')}
【朋友圈/社群转发语】：{wechat.get('share_text', '')}
【话题标签】：{wechat_tags}
======================================================================
"""

    def _clean_and_parse_json(
        self,
        raw_content: str,
        entry: Dict[str, Any],
        storyboard: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Strip markdown fences and parse LLM JSON robustly."""
        clean = raw_content.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()

        try:
            data = json.loads(clean)
            if isinstance(data, dict) and ("xhs" in data or "douyin" in data):
                return data
        except Exception:
            pass

        decoder = json.JSONDecoder()
        for idx in range(len(clean)):
            if clean[idx] == '{':
                try:
                    cand, _ = decoder.raw_decode(clean[idx:])
                    if isinstance(cand, dict) and ("xhs" in cand or "douyin" in cand):
                        return cand
                except Exception:
                    continue

        return self._mock_copywriting_generation(entry, storyboard)

    def _mock_copywriting_generation(
        self,
        entry: Dict[str, Any],
        storyboard: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate high-quality rule-based copywriting tailored to the entry topic."""
        title = entry.get("title", "生活健康建议")
        chapter_title = entry.get("chapter_title", "生活指南")
        evidence_grade = entry.get("evidence_grade", "A")
        cost_desc = entry.get("cost_desc", "几乎不花钱，只需多花几秒")
        benefit_desc = entry.get("benefit_desc", "显著降低潜在风险")
        plain_text = entry.get("plain_text") or entry.get("raw_content") or ""

        # Extract numerical or compelling keyword if present
        nums = re.findall(r"\d+(?:\.\d+)?%?", plain_text)
        num_str = nums[0] if nums else "成倍"

        # Platform specific copy construction
        xhs_titles = [
            f"关于{title}，很多人第1步就做错了⚠️",
            f"不花钱的保命动作！为什么一定要{title}？🚗",
            f"90%的人都忽略了！原来{title}差距这么大💡"
        ]
        if "安全带" in title:
            xhs_titles = [
                "车里这根带子，关键时刻真能救命！后排千万别大意⚠️",
                "不花钱的保命动作！为什么坐后排也必须系安全带？🚗",
                "90%的人都忽略了！后排不系安全带致死率差这么多💡"
            ]

        xhs_intro = f"每次遇到类似情况，很多人总觉得“这没多大影响”。但权威科学数据一对比，真的颠覆日常认知！😱"
        if "安全带" in title:
            xhs_intro = "上车你是不是也习惯了“后排没摄像头就不系”？交通权威数据直接说人话，后排不系致死率翻倍！😱"

        xhs_body_points = [
            f"硬核真相：科学研究证实，做好这一步能让相关致命风险下降 {num_str}！",
            f"权威背书：全书经过严格循证，证据等级达到 {evidence_grade} 级最高标准。",
            f"执行代价：{cost_desc}，用极微小的动作消除巨大不确定性。",
            f"核心收益：{benefit_desc}，真正的高性价比生活习惯。"
        ]

        xhs_cta = f"高性价比人生第一原则：用最小代价换取最大确定性。赶紧转给身边最在乎的人！❤️"

        xhs_tags = [
            "#生活百科",
            "#硬核科普",
            "#高性价比生活",
            "#涨知识",
            f"#{chapter_title}",
            "#健康日常"
        ]

        # Douyin
        douyin_title = f"{title}：一个极少人注意的习惯"
        douyin_hook = f"你知道吗？关于{title}，90%的人做法全错了！"
        douyin_caption = f"不花钱只花几秒，关键时刻降一半风险！用最小代价换最大确定性。#涨知识 #硬核科普 #生活技巧"
        douyin_tags = ["#涨知识", "#硬核科普", "#生活指南", "#生活小妙招"]

        # WeChat Channels
        wechat_title = f"高性价比人生指南：关于《{title}》的硬核科学建议"
        wechat_share = f"生活里极少人注意的小习惯，背后却有顶级科学证据背书。不花钱、少走弯路，转给家人朋友一起对照！"
        wechat_tags = ["#生活智慧", "#健康守护", "#家庭生活", "#科学认知"]

        return {
            "xhs": {
                "title_candidates": xhs_titles,
                "intro": xhs_intro,
                "body_points": xhs_body_points,
                "call_to_action": xhs_cta,
                "tags": xhs_tags
            },
            "douyin": {
                "title": douyin_title,
                "hook": douyin_hook,
                "caption": douyin_caption,
                "tags": douyin_tags
            },
            "wechat": {
                "title": wechat_title,
                "share_text": wechat_share,
                "tags": wechat_tags
            }
        }


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent OS file naming issues."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip().replace(" ", "_")


def main():
    parser = argparse.ArgumentParser(description="Generate multi-platform social media copy and hashtags.")
    parser.add_argument("--entry-id", type=str, default=None, help="Process a specific entry (e.g. 01_001)")
    parser.add_argument("--chapter", type=int, default=None, help="Filter entries by chapter")
    parser.add_argument("--limit", type=int, default=1, help="Max entries to process (default: 1)")
    parser.add_argument("--all", action="store_true", help="Process all entries")
    parser.add_argument("--mock", action="store_true", help="Force mock offline template mode")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    args = parser.parse_args()

    conn = get_connection(args.db_path)

    if args.entry_id:
        target = get_entry(conn, args.entry_id)
        if not target:
            print(f"❌ 未找到条目: {args.entry_id}")
            sys.exit(1)
        entries_to_process = [target]
    else:
        limit = None if args.all else args.limit
        entries_to_process = list_entries(conn, chapter_index=args.chapter, limit=limit)

    if not entries_to_process:
        print("ℹ️ 没有符合条件的条目。")
        sys.exit(0)

    print(f"📋 即将为 {len(entries_to_process)} 个条目生成多平台营销文案与标签...")
    copywriter = Copywriter(mock=args.mock)

    for idx, entry in enumerate(entries_to_process, start=1):
        eid = entry["id"]
        ch_title = entry["chapter_title"]
        title = entry["title"]
        clean_name = sanitize_filename(f"{eid}_{ch_title}之{title}")

        raw_dir = entry.get("raw_assets_dir") or os.path.join(OUTPUT_RAW_ASSETS_DIR, eid)
        json_path = os.path.join(raw_dir, "copywriting.json")
        txt_path = os.path.join(OUTPUT_FINAL_VIDEOS_DIR, f"{clean_name}_copywriting.txt")

        print(f"[{idx}/{len(entries_to_process)}] 正在为 [{eid}] 《{title}》 生成小红书/抖音/视频号文案...")
        res = copywriter.generate_copywriting(
            entry=entry,
            output_json_path=json_path,
            output_txt_path=txt_path
        )

        xhs_title = res.get("xhs", {}).get("title_candidates", [""])[0]
        print(f"   ✅ 小红书主推标题: {xhs_title}")
        print(f"   💾 保存结构化 JSON: {json_path}")
        print(f"   📝 保存发布文本 TXT: {txt_path}\n")

    print(f"🎉 全部 {len(entries_to_process)} 个条目的营销文案已成功生成！")


if __name__ == "__main__":
    from datetime import datetime
    main()
