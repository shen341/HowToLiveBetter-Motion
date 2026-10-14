"""Unit tests for Local AI roadmap adaptation, AI_MODE switching, and LocalImageClient (ADR-015 Phase 1 & 3)."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.config import (
    LOCAL_COMFYUI_URL,
    LOCAL_LLM_BASE_URL,
    LOCAL_LLM_MODEL,
    MUSE_BASE_URL,
    TTS_API_URL,
)
from src.local_image_client import LocalImageClient, STYLE_LORA_PRESETS
from src.muse_client import MuseClient
from src.tts_client import TTSClient


class TestLocalAIMode(unittest.TestCase):
    """Test AI_MODE switching, Ollama local routing, and ComfyUI image generation."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_local_ai_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_local_mode_client_initialization(self):
        """When ai_mode='local', client defaults to local Ollama endpoints and LocalImageClient."""
        client = MuseClient(ai_mode="local", mock=False)
        self.assertEqual(client.ai_mode, "local")
        self.assertEqual(client.base_url, LOCAL_LLM_BASE_URL)
        self.assertEqual(client.text_model, LOCAL_LLM_MODEL)
        self.assertIsNotNone(client.local_image_client)
        self.assertEqual(client.local_image_client.base_url, LOCAL_COMFYUI_URL)

    def test_cloud_mode_client_initialization(self):
        """When ai_mode='cloud', client points to Muse cloud endpoints."""
        client = MuseClient(ai_mode="cloud", api_key="test_muse_key", mock=False)
        self.assertEqual(client.ai_mode, "cloud")
        self.assertEqual(client.base_url, MUSE_BASE_URL)
        self.assertEqual(client.text_model, "muse-spark")

    def test_tts_unchanged_under_local_and_cloud(self):
        """Stage 2: TTS voiceover continues to use free Edge-TTS (TTS_API_URL) regardless of mode."""
        tts_client = TTSClient()
        self.assertEqual(tts_client.api_url, TTS_API_URL)
        self.assertIn("workers.dev", tts_client.api_url)

    def test_local_image_client_workflow_builder_for_styles(self):
        """Verify ComfyUI workflow DAG is properly constructed for all 7 art styles."""
        client = LocalImageClient(mock=True)
        for style_id in STYLE_LORA_PRESETS.keys():
            workflow = client.build_prompt_workflow(
                prompt="A young person buckling up seatbelt in modern vehicle",
                style_id=style_id,
                width=1024,
                height=1792,
                seed=12345
            )
            # Verify basic node presence
            self.assertIn("3", workflow, "KSampler node must exist")
            self.assertIn("4", workflow, "CheckpointLoaderSimple node must exist")
            self.assertIn("5", workflow, "EmptyLatentImage node must exist")
            self.assertIn("6", workflow, "CLIPTextEncode positive node must exist")
            self.assertIn("7", workflow, "CLIPTextEncode negative node must exist")
            self.assertIn("8", workflow, "VAEDecode node must exist")
            self.assertIn("9", workflow, "SaveImage node must exist")
            self.assertIn("10", workflow, "LoraLoader node must exist")

            # Check dimensions
            self.assertEqual(workflow["5"]["inputs"]["width"], 1024)
            self.assertEqual(workflow["5"]["inputs"]["height"], 1792)

            # Check LoRA linkage
            lora_preset = client.get_style_lora_preset(style_id)
            self.assertEqual(workflow["10"]["inputs"]["lora_name"], lora_preset["lora_name"])
            self.assertIn(lora_preset["trigger"], workflow["6"]["inputs"]["text"])

    @patch("src.local_image_client.requests.get")
    def test_local_image_client_is_available_detection(self, mock_get):
        """Test ComfyUI availability detection."""
        client = LocalImageClient(mock=False)

        # Server online
        mock_get.return_value.status_code = 200
        self.assertTrue(client.is_available())

        # Server offline
        mock_get.side_effect = Exception("Connection refused")
        self.assertFalse(client.is_available())

    def test_muse_client_generate_image_local_to_cloud_fallback(self):
        """When in local mode and ComfyUI is unavailable, automatically fallback to cloud or mock without crashing."""
        client = MuseClient(ai_mode="local", mock=False)
        # Mock ComfyUI as unavailable
        client.local_image_client.is_available = MagicMock(return_value=False)
        # Mock cloud images generator
        client.client.images.generate = MagicMock()
        client._save_image_from_response = MagicMock(return_value=os.path.join(self.test_dir, "scene_01.png"))

        out_path = os.path.join(self.test_dir, "scene_01.png")
        result = client.generate_image("A futuristic city", out_path, style_id="25_ghibli")
        self.assertEqual(result, out_path)
        client.client.images.generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
