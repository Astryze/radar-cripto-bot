"""Offline contract tests for optional Hugging Face image-to-image provider."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from mediaflow_unhas.hf_provider import generate

class HuggingFaceProviderTests(unittest.TestCase):
    def test_missing_token_fails_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/"ref.jpg"
            Image.new("RGB",(500,500)).save(source)
            with self.assertRaisesRegex(RuntimeError, "HF_TOKEN ausente"):
                generate(source, "nail art", 42, token="")
