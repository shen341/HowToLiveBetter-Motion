"""tests/test_image_fallback.py - Unit tests for Muse image and script generation fallback routes."""

import base64
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.muse_client import MuseClient, is_i2v_scene


class TestImageFallback(unittest.TestCase):
    """Test fallback disaster recovery routes for image and script generation."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_img = os.path.join(self.test_dir, "test_scene.png")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_muse_client_fallback_init(self):
        """Test MuseClient initializes fallback client properly when configured."""
        client = MuseClient(
            api_key="test_primary_key",
            base_url="https://yourselfai.org/muse/v1",
            fallback_api_key="test_fallback_key",
            fallback_base_url="https://yourselfai.org/v1",
            fallback_image_model="gemini-3.1-flash-image",
            fallback_text_model="gemini-3.8-flash-high",
            timeout=15.0,
        )
        self.assertFalse(client.mock)
        self.assertIsNotNone(client.client)
        self.assertIsNotNone(client.fallback_client)
        self.assertEqual(client.fallback_image_model, "gemini-3.1-flash-image")
        self.assertEqual(client.fallback_text_model, "gemini-3.8-flash-high")
        self.assertEqual(client.timeout, 15.0)

    @patch("src.muse_client.requests.post")
    def test_image_fallback_triggered_on_primary_failure(self, mock_requests_post):
        """When primary muse-image fails, fallback to gemini-3.1-flash-image via /v1/chat/completions."""
        client = MuseClient(
            api_key="test_key",
            fallback_api_key="test_fallback_key",
            fallback_base_url="https://yourselfai.org/v1",
            fallback_image_model="gemini-3.1-flash-image",
            max_retries=1,
            retry_delay=0.01,
        )

        # Primary client fails with 429 RateLimitError
        client.client.images.generate = MagicMock(side_effect=Exception("HTTP 429 Too Many Requests"))

        # Fallback chat completions succeeds with YourselfAI format (choices[0].message.images)
        fake_b64 = base64.b64encode(b"PNG_FAKE_IMAGE_DATA_12345").decode("utf-8")
        mock_chat_resp = MagicMock()
        mock_chat_resp.status_code = 200
        mock_chat_resp.json.return_value = {
            "id": "test_id_123",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "images": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{fake_b64}"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        mock_requests_post.return_value = mock_chat_resp

        result_path = client.generate_image("A beautiful scenery", self.output_img)

        self.assertEqual(result_path, self.output_img)
        self.assertTrue(os.path.exists(self.output_img))
        with open(self.output_img, "rb") as f:
            self.assertEqual(f.read(), b"PNG_FAKE_IMAGE_DATA_12345")

        # Verify calls
        client.client.images.generate.assert_called()
        mock_requests_post.assert_called()
        call_args = mock_requests_post.call_args
        self.assertEqual(call_args[0][0], "https://yourselfai.org/v1/chat/completions")
        self.assertEqual(call_args[1]["json"]["model"], "gemini-3.1-flash-image")

    def test_image_fallback_standard_openai_model(self):
        """When fallback model is a standard OpenAI image model (e.g. gpt-image-2.5), use images.generate."""
        client = MuseClient(
            api_key="test_key",
            fallback_api_key="test_fallback_key",
            fallback_base_url="https://yourselfai.org/v1",
            fallback_image_model="gpt-image-2.5",
            max_retries=1,
            retry_delay=0.01,
        )

        client.client.images.generate = MagicMock(side_effect=Exception("HTTP 429 Too Many Requests"))

        fake_b64 = base64.b64encode(b"PNG_FAKE_IMAGE_DATA_67890").decode("utf-8")
        mock_data_item = MagicMock()
        mock_data_item.b64_json = fake_b64
        mock_data_item.url = None
        mock_resp = MagicMock()
        mock_resp.data = [mock_data_item]
        client.fallback_client.images.generate = MagicMock(return_value=mock_resp)

        result_path = client.generate_image("A cyberpunk city", self.output_img)

        self.assertEqual(result_path, self.output_img)
        self.assertTrue(os.path.exists(self.output_img))
        with open(self.output_img, "rb") as f:
            self.assertEqual(f.read(), b"PNG_FAKE_IMAGE_DATA_67890")

        client.fallback_client.images.generate.assert_called_with(
            model="gpt-image-2.5",
            prompt="A cyberpunk city",
            size="1024x1792"
        )

    def test_image_degradation_when_both_routes_fail(self):
        """When both primary and fallback routes fail, gracefully degrade to styled mock placeholder."""
        client = MuseClient(
            api_key="test_key",
            fallback_api_key="test_fallback_key",
            fallback_image_model="gemini-3.1-flash-image",
            max_retries=1,
            retry_delay=0.01,
        )

        client.client.images.generate = MagicMock(side_effect=Exception("Primary 502 Bad Gateway"))
        with patch("src.muse_client.requests.post", side_effect=Exception("Fallback 503 Unavailable")):
            result_path = client.generate_image("A test prompt", self.output_img)

        self.assertEqual(result_path, self.output_img)
        self.assertTrue(os.path.exists(self.output_img))
        self.assertGreater(os.path.getsize(self.output_img), 1000)

    def test_script_fallback_triggered_on_primary_failure(self):
        """When muse-spark fails, fallback to gemini-3.8-flash-high to generate script."""
        client = MuseClient(
            api_key="test_key",
            fallback_api_key="test_fallback_key",
            fallback_text_model="gemini-3.8-flash-high",
            max_retries=1,
            retry_delay=0.01,
        )

        client.client.chat.completions.create = MagicMock(side_effect=Exception("Muse-Spark connection timed out"))

        mock_choice = MagicMock()
        mock_choice.message.content = '{"art_style_id": "25_ghibli", "scenes": [{"scene_index": 1, "image_prompt": "test"}]}'
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        client.fallback_client.chat.completions.create = MagicMock(return_value=mock_resp)

        entry = {
            "id": "01_001",
            "chapter_title": "测试章节",
            "chapter_index": 1,
            "title": "测试条目",
            "plain_text": "内容测试",
            "cost_desc": "无",
            "benefit_desc": "健康",
            "evidence_grade": "A",
        }

        script_data = client.generate_script(entry, scene_count=4)
        self.assertIn("scenes", script_data)
        self.assertEqual(script_data["art_style_id"], "25_ghibli")
        client.fallback_client.chat.completions.create.assert_called_once()

    def test_motion_mode_helper(self):
        """Verify is_i2v_scene accurately filters scenes for static, i2v-tier1, and i2v-all."""
        # Static mode: NEVER calls I2V
        for sc in range(1, 7):
            self.assertFalse(is_i2v_scene(sc, total_scenes=6, motion_mode="static"))
            self.assertFalse(is_i2v_scene(sc, total_scenes=6, motion_mode=""))

        # i2v-tier1: ONLY Scene 1 & Scene 5
        self.assertTrue(is_i2v_scene(1, total_scenes=6, motion_mode="i2v-tier1"))
        self.assertFalse(is_i2v_scene(2, total_scenes=6, motion_mode="i2v-tier1"))
        self.assertFalse(is_i2v_scene(3, total_scenes=6, motion_mode="i2v-tier1"))
        self.assertFalse(is_i2v_scene(4, total_scenes=6, motion_mode="i2v-tier1"))
        self.assertTrue(is_i2v_scene(5, total_scenes=6, motion_mode="i2v-tier1"))
        self.assertFalse(is_i2v_scene(6, total_scenes=6, motion_mode="i2v-tier1"))

        # i2v-all: ALL scenes
        for sc in range(1, 7):
            self.assertTrue(is_i2v_scene(sc, total_scenes=6, motion_mode="i2v-all"))


if __name__ == "__main__":
    unittest.main()
