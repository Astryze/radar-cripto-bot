"""Basic safety and ComfyUI workflow contract tests. No remote/GPU needed."""
import unittest
from mediaflow_unhas.reference_collector import validate_url
from mediaflow_unhas.reference_transform import build_graph

GRAPH = {
    "1": {"class_type":"LoadImage","inputs":{"image":"{{REFERENCE_IMAGE}}"}},
    "2": {"class_type":"CLIPTextEncode","inputs":{"text":"{{PROMPT}}"}},
    "3": {"class_type":"KSampler","inputs":{"seed":"{{SEED}}"}},
}

class TestReferenceMode(unittest.TestCase):
    def test_urls_allowed(self):
        for url in ("https://www.pinterest.com/pin/12345/",
                    "https://www.douyin.com/video/123",
                    "https://www.tiktok.com/@creator/video/123"):
            self.assertEqual(validate_url(url), url)
    def test_private_urls_rejected(self):
        for url in ("http://localhost/", "https://127.0.0.1/internal",
                    "https://pinterest.com.evil.example/pin/1",
                    "https://example.net", "https://user:password@www.douyin.com/"):
            with self.assertRaises(ValueError):
                validate_url(url)
    def test_placeholders(self):
        obj = build_graph(GRAPH, "premium red manicure", 123, "my-photo.jpg")
        self.assertEqual(obj["1"]["inputs"]["image"], "my-photo.jpg")
        self.assertEqual(obj["2"]["inputs"]["text"], "premium red manicure")
        self.assertEqual(obj["3"]["inputs"]["seed"], 123)
        self.assertEqual(GRAPH["1"]["inputs"]["image"], "{{REFERENCE_IMAGE}}")
    def test_graph_without_reference_loader_rejected(self):
        bad = {"1": {"class_type":"OtherNode","inputs":{"image":"{{REFERENCE_IMAGE}}",
                       "text":"{{PROMPT}}", "seed":"{{SEED}}"}}}
        with self.assertRaises(ValueError):
            build_graph(bad, "manicure", 1, "x.jpg")
    def test_missing_seed_rejected(self):
        with self.assertRaises(ValueError):
            build_graph({"1": GRAPH["1"], "2": GRAPH["2"]}, "manicure", 1, "x.jpg")
