import tempfile
import unittest
from pathlib import Path
from PIL import Image

from mediaflow_unhas.horde_provider import make_payload, safe_result, generate

class Response:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload

class Session:
    def __init__(self):
        self.deleted = []
        self.submitted = None
    def post(self, url, json=None, headers=None, timeout=None):
        self.submitted = json
        return Response({"id": "demo-id"})
    def get(self, url, headers=None, timeout=None):
        if "/check/" in url:
            return Response({"done": True, "faulted": False})
        return Response({"generations": [{"img": ""}]})
    def delete(self, url, headers=None, timeout=None):
        self.deleted.append(url)
        return Response({})

class ProviderContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / "nails.jpg"
        Image.new("RGB", (800, 1200), (140, 0, 10)).save(self.source)
    def tearDown(self):
        self.tmp.cleanup()
    def test_payload_img2img(self):
        data = make_payload(self.source, "Professional manicure", 123)
        self.assertEqual(data["source_processing"], "img2img")
        self.assertTrue(data["source_image"])
        self.assertEqual(data["params"]["seed"], "123")
        self.assertFalse(data["nsfw"])
    def test_size_guard(self):
        with self.assertRaises(ValueError):
            make_payload(self.source, "manicure", 123, width=720, height=1280)
    def test_urls(self):
        self.assertTrue(safe_result("https://cdn.stablehorde.net/photos/a.webp"))
        self.assertFalse(safe_result("https://example.com/file"))
        self.assertFalse(safe_result("http://cdn.stablehorde.net/file"))
        self.assertFalse(safe_result("https://cdn.stablehorde.net.evil.org/"))
    def test_api_handshake_and_cleanup(self):
        sess = Session()
        with self.assertRaises(RuntimeError):
            generate(self.source, "red nails", 123, session=sess,
                     api_key="0000000000", timeout=10, poll=0)
        self.assertEqual(sess.submitted["source_processing"], "img2img")
        self.assertTrue(sess.deleted)
