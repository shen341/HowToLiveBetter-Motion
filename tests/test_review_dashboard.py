"""Unit tests for Review Dashboard and state transitions (TASK-5.1 / ADR-013)."""

import os
import shutil
import sqlite3
import tempfile
import unittest

from src.db import (
    get_connection,
    get_entry,
    get_statistics,
    init_db,
    mark_approved,
    reset_entry,
    update_status,
    upsert_entry,
)

from importlib.util import spec_from_file_location, module_from_spec
dashboard_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "04_review_dashboard.py")
spec = spec_from_file_location("review_dashboard", dashboard_script)
dashboard_mod = module_from_spec(spec)
spec.loader.exec_module(dashboard_mod)
get_entry_assets = dashboard_mod.get_entry_assets


class TestReviewDashboard(unittest.TestCase):
    """Test dashboard backend logic, asset resolution, and review workflow actions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_dash_")
        self.db_path = os.path.join(self.temp_dir, "test_pipeline.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        init_db(self.conn)

        # Seed sample entries
        self.sample_entry = {
            "id": "01_999",
            "source_file": "01.md",
            "chapter_index": 1,
            "chapter_title": "测试章节",
            "item_index": 999,
            "title": "测试条目标题",
            "cost_money": "0",
            "cost_time": "1分钟",
            "evidence_grade": "A",
            "status": "Completed"
        }
        upsert_entry(self.conn, self.sample_entry)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mark_approved_workflow(self):
        """Verify marking an entry as Approved updates status and notes."""
        entry_id = "01_999"
        # 1. Mark approved without notes
        res = mark_approved(self.conn, entry_id)
        self.assertTrue(res)
        entry = get_entry(self.conn, entry_id)
        self.assertEqual(entry["status"], "Approved")

        # 2. Mark approved with reviewer feedback note
        mark_approved(self.conn, entry_id, reviewer_notes="画质与音画同步极佳，准予发布")
        entry = get_entry(self.conn, entry_id)
        self.assertEqual(entry["status"], "Approved")
        self.assertIn("准予发布", entry["notes"])

    def test_reset_entry_workflow(self):
        """Verify resetting an entry back to Pending or Script_Generated."""
        entry_id = "01_999"
        update_status(self.conn, entry_id, status="Completed", error_message="Transient glitch")

        # Reset without clearing assets
        res = reset_entry(self.conn, entry_id, target_status="Script_Generated", clear_assets=False)
        self.assertTrue(res)
        entry = get_entry(self.conn, entry_id)
        self.assertEqual(entry["status"], "Script_Generated")
        self.assertIsNone(entry["error_message"])

        # Reset with clear_assets
        update_status(self.conn, entry_id, status="Failed", script_json='{"scenes": []}')
        reset_entry(self.conn, entry_id, target_status="Pending", clear_assets=True)
        entry = get_entry(self.conn, entry_id)
        self.assertEqual(entry["status"], "Pending")
        self.assertIsNone(entry["script_json"])

    def test_get_statistics_tracking(self):
        """Verify get_statistics includes Approved and Needs_Revision in summary counts."""
        stats = get_statistics(self.conn)
        summary = stats["status_summary"]
        self.assertIn("Approved", summary)
        self.assertIn("Needs_Revision", summary)
        self.assertEqual(stats["total_entries"], 1)

    def test_get_entry_assets_robustness(self):
        """Verify get_entry_assets handles existing and missing asset paths safely."""
        entry = get_entry(self.conn, "01_999")
        assets = get_entry_assets(entry)
        self.assertIsInstance(assets, dict)
        self.assertIn("video_path", assets)
        self.assertIn("cover_path", assets)
        self.assertIn("srt_path", assets)
        self.assertIn("storyboard", assets)
        # Should be None since files don't physically exist for dummy 01_999
        self.assertIsNone(assets["video_path"])
        self.assertIsNone(assets["cover_path"])


if __name__ == "__main__":
    unittest.main()
