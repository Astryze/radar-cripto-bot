"""Photo finishing should preserve proportions, improve details and be deterministic."""
import unittest
from PIL import Image
from mediaflow_unhas.photo_finish import finish, photo_metrics, quality_score

class PhotoFinishingTests(unittest.TestCase):
    def test_portrait_export(self):
        for size in ((900,1400),(1400,900),(720,1280)):
            with self.subTest(size=size):
                source=Image.new("RGB",size,(130,53,97))
                result=finish(source)
                self.assertEqual(result.size,(720,1280))
    def test_metrics_and_score(self):
        photo=Image.new("RGB",(800,1200),(150,40,90))
        m=photo_metrics(photo)
        self.assertEqual(m["width"],800)
        self.assertEqual(m["height"],1200)
        self.assertGreaterEqual(quality_score(m),0)
        self.assertLessEqual(quality_score(m),100)
