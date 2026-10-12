"""test_platform_presets.py - Unit tests for platform bitrate and encoding presets."""

import os
import unittest
from unittest.mock import MagicMock, patch

from src.assembler import (
    PLATFORM_PRESETS,
    VideoAssembler,
    get_platform_preset,
    list_platform_presets,
)


class TestPlatformPresets(unittest.TestCase):
    """Test platform encoding presets dictionary and helper functions."""

    def test_presets_exist_and_complete(self):
        expected_platforms = {"default", "xhs", "douyin", "wechat", "bilibili"}
        self.assertTrue(expected_platforms.issubset(set(PLATFORM_PRESETS.keys())))

        for key, p in PLATFORM_PRESETS.items():
            self.assertIn("name", p)
            self.assertIn("crf", p)
            self.assertIn("preset", p)
            self.assertIn("audio_bitrate", p)
            self.assertIn("maxrate", p)
            self.assertIn("bufsize", p)
            self.assertIn("description", p)
            self.assertIsInstance(p["crf"], int)
            self.assertTrue(16 <= p["crf"] <= 28)

    def test_get_platform_preset_case_insensitive_and_fallback(self):
        # Case insensitive
        xhs_upper = get_platform_preset("XHS")
        self.assertEqual(xhs_upper["name"], PLATFORM_PRESETS["xhs"]["name"])
        self.assertEqual(xhs_upper["crf"], 21)

        douyin_mixed = get_platform_preset(" DouYin ")
        self.assertEqual(douyin_mixed["name"], PLATFORM_PRESETS["douyin"]["name"])

        # Unknown fallback
        fallback = get_platform_preset("unknown_platform_123")
        self.assertEqual(fallback["name"], PLATFORM_PRESETS["default"]["name"])

        # None fallback
        fallback_none = get_platform_preset(None)
        self.assertEqual(fallback_none["name"], PLATFORM_PRESETS["default"]["name"])

    def test_list_platform_presets(self):
        all_presets = list_platform_presets()
        self.assertEqual(len(all_presets), len(PLATFORM_PRESETS))
        self.assertIn("xhs", all_presets)

    def test_assembler_initialization_with_preset(self):
        assembler = VideoAssembler(default_preset="douyin")
        self.assertEqual(assembler.default_preset, "douyin")


if __name__ == "__main__":
    unittest.main()
