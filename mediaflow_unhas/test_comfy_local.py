# ruff: noqa
import sys
import types
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
stub = types.ModuleType("run")
stub.THEMES = {"vermelhas_elegantes": "red manicure"}
stub.render = lambda *args: None
sys.modules["run"] = stub
from comfy_local import prepare_workflow, validate_server

class ComfyLocalTests(unittest.TestCase):
    def test_replace_text_and_seed(self):
        graph = {"1": {"inputs": {"text": "{{PROMPT}}"}}, "2": {"inputs": {"seed": "{{SEED}}"}}}
        result = prepare_workflow(graph, "red nails", 123)
        self.assertEqual(result["1"]["inputs"]["text"], "red nails")
        self.assertEqual(result["2"]["inputs"]["seed"], 123)
        self.assertEqual(graph["2"]["inputs"]["seed"], "{{SEED}}")

    def test_missing_placeholder(self):
        with self.assertRaises(ValueError):
            prepare_workflow({"1": {"inputs": {"text": "fixed"}}}, "hello", 1)

    def test_local_host_only(self):
        self.assertEqual(validate_server("http://127.0.0.1:8188/"), "http://127.0.0.1:8188")
        for url in ("https://example.com", "http://192.168.1.1:8188", "file:///tmp/test"):
            with self.assertRaises(ValueError):
                validate_server(url)

if __name__ == "__main__":
    unittest.main()
