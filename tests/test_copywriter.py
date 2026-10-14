"""Unit tests for multi-platform copywriting and tag generation (TASK-5.2 / ADR-014)."""

import json
import os
import shutil
import tempfile
import unittest

from src.copywriter import Copywriter, build_copywriting_prompt


class TestCopywriter(unittest.TestCase):
    """Test copywriting prompt building, template generation, parsing, and file output."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_copy_")
        self.copywriter = Copywriter(mock=True)

        self.sample_entry = {
            "id": "01_001",
            "source_file": "01.md",
            "chapter_index": 1,
            "chapter_title": "不要早死",
            "item_index": 1,
            "title": "系安全带，前排后排都系",
            "cost_money": "0",
            "cost_time": "2秒",
            "cost_willpower": "低",
            "benefit_level": "极高",
            "benefit_metric": "致死率降50%",
            "cost_desc": "不花钱，每次上车多花2秒",
            "benefit_desc": "致命伤风险下降45%至60%",
            "evidence_grade": "A",
            "plain_text": "坐前排系上安全带，出车祸时被撞死的概率大约降一半。坐轻型卡车前排的降六成。美国2022年死在车里的人，能查到系没系带的，有一半没系。",
            "raw_content": "坐前排系上安全带..."
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_copywriting_prompt(self):
        """Verify prompt construction embeds all key fields and platform requirements."""
        sys_prompt, usr_prompt = build_copywriting_prompt(self.sample_entry)
        self.assertIn("小红书", sys_prompt)
        self.assertIn("抖音", sys_prompt)
        self.assertIn("微信视频号", sys_prompt)
        self.assertIn("不要早死", usr_prompt)
        self.assertIn("系安全带", usr_prompt)
        self.assertIn("A 级", usr_prompt)

    def test_mock_generation_structure(self):
        """Verify mock generation produces complete structures for XHS, Douyin, and WeChat."""
        res = self.copywriter._mock_copywriting_generation(self.sample_entry)
        self.assertIn("xhs", res)
        self.assertIn("douyin", res)
        self.assertIn("wechat", res)

        # XHS structure
        xhs = res["xhs"]
        self.assertGreaterEqual(len(xhs["title_candidates"]), 2)
        self.assertTrue(any("⚠️" in t or "🚗" in t or "💡" in t for t in xhs["title_candidates"]))
        self.assertTrue(len(xhs["body_points"]) >= 3)
        self.assertTrue(all(t.startswith("#") for t in xhs["tags"]))

        # Douyin structure
        dy = res["douyin"]
        self.assertTrue(bool(dy["title"]))
        self.assertTrue(bool(dy["hook"]))
        self.assertTrue(bool(dy["caption"]))
        self.assertTrue(all(t.startswith("#") for t in dy["tags"]))

        # WeChat structure
        wx = res["wechat"]
        self.assertTrue(bool(wx["title"]))
        self.assertTrue(bool(wx["share_text"]))
        self.assertTrue(all(t.startswith("#") for t in wx["tags"]))

    def test_generate_and_save_artifacts(self):
        """Verify output files (JSON and TXT) are correctly written and formatted."""
        json_out = os.path.join(self.temp_dir, "copywriting.json")
        txt_out = os.path.join(self.temp_dir, "copywriting.txt")

        res = self.copywriter.generate_copywriting(
            entry=self.sample_entry,
            output_json_path=json_out,
            output_txt_path=txt_out
        )

        self.assertTrue(os.path.exists(json_out))
        self.assertTrue(os.path.exists(txt_out))

        # Check JSON integrity
        with open(json_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["entry_id"], "01_001")
        self.assertIn("full_post", data["xhs"])

        # Check TXT formatting
        with open(txt_out, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("📕【小红书专属种草发布文案", text)
        self.assertIn("🎵【抖音短视频发布文案", text)
        self.assertIn("🟢【微信视频号/社群发布文案", text)
        self.assertIn("#生活百科", text)

    def test_clean_and_parse_json_resilience(self):
        """Verify markdown fence removal and fallback parsing."""
        fenced = """```json
{
  "xhs": {
    "title_candidates": ["标题A", "标题B"],
    "intro": "导语A",
    "body_points": ["点1"],
    "call_to_action": "行动",
    "tags": ["#标签"]
  },
  "douyin": {
    "title": "抖音标题",
    "hook": "钩子",
    "caption": "描述",
    "tags": ["#抖音"]
  },
  "wechat": {
    "title": "微信标题",
    "share_text": "转发语",
    "tags": ["#微信"]
  }
}
```"""
        parsed = self.copywriter._clean_and_parse_json(fenced, self.sample_entry)
        self.assertIn("xhs", parsed)
        self.assertEqual(parsed["xhs"]["title_candidates"][0], "标题A")

        # Malformed JSON fallback
        malformed = "Sorry, I cannot generate JSON today."
        fallback_parsed = self.copywriter._clean_and_parse_json(malformed, self.sample_entry)
        self.assertIn("xhs", fallback_parsed)
        self.assertIn("douyin", fallback_parsed)


if __name__ == "__main__":
    unittest.main()
