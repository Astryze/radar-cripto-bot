import unittest
from mediaflow_unhas.quality import evaluate

class QualitySelectionTests(unittest.TestCase):
    def test_red_nails_pass(self):
        self.assertTrue(evaluate("vermelhas_elegantes", "Red manicure nails.jpg", {})[0])
    def test_unrelated_red_photo_rejected(self):
        self.assertFalse(evaluate("vermelhas_elegantes", "Red sunset.jpg", {})[0])
    def test_wrong_nail_color_rejected(self):
        self.assertFalse(evaluate("vermelhas_elegantes", "Blue manicure nails.jpg", {})[0])
    def test_pedicure_rejected(self):
        self.assertFalse(evaluate("vermelhas_elegantes", "Red toenails pedicure.jpg", {})[0])
    def test_nail_polish_bottle_rejected(self):
        self.assertFalse(evaluate("vermelhas_elegantes", "Red nail polish bottle.jpg", {})[0])
    def test_non_photograph_rejected(self):
        self.assertFalse(evaluate("vermelhas_elegantes", "Vector red nail illustration.jpg", {})[0])
    def test_french_selection(self):
        self.assertTrue(evaluate("francesinha_delicada", "French manicure.jpg", {})[0])
        self.assertFalse(evaluate("francesinha_delicada", "Red manicure.jpg", {})[0])
if __name__=="__main__":
    unittest.main()
