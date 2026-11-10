import unittest
from mediaflow_unhas.openverse_source import supported_url, permitted_license, SEARCHES

class OpenverseSafetyTests(unittest.TestCase):
    def test_nail_themes_covered(self):
        self.assertEqual(len(SEARCHES), 30)
        self.assertIn("red manicure nails", SEARCHES["vermelhas_elegantes"])
    def test_safe_cdn(self):
        self.assertTrue(supported_url("https://live.staticflickr.com/123/image.jpg"))
        self.assertTrue(supported_url("https://upload.wikimedia.org/wikipedia/commons/a/a1/test.jpg"))
    def test_unsafe_urls_rejected(self):
        self.assertFalse(supported_url("http://localhost:8080/internal"))
        self.assertFalse(supported_url("https://localhost/photo"))
        self.assertFalse(supported_url("https://evilwikimedia.org/photo"))
        self.assertFalse(supported_url("https://example.com/image.jpg"))
        self.assertFalse(supported_url("http://live.staticflickr.com/123/image.jpg"))
    def test_licenses(self):
        base={"foreign_landing_url":"https://flickr.com/photos/test","creator":"Nail Photographer"}
        self.assertTrue(permitted_license({**base,"license":"by"}))
        self.assertTrue(permitted_license({**base,"license":"by-sa"}))
        self.assertTrue(permitted_license({**base,"license":"cc0"}))
        self.assertFalse(permitted_license({**base,"license":"by-nc"}))
        self.assertFalse(permitted_license({**base,"license":"by-nd"}))
        self.assertFalse(permitted_license({"license":"by","creator":"x"}))
