import tempfile
from pathlib import Path
import unittest
from PIL import Image
import lens


class LtInputTests(unittest.TestCase):
    def test_large_input_is_scaled_without_overwriting_original(self):
        self.assertTrue(hasattr(lens,'lt_input'))
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'screen.png'
            Image.new('RGB',(3840,2160),'white').save(source)
            result=lens.lt_input(source)
            self.assertNotEqual(result,source)
            with Image.open(result) as im:self.assertEqual(im.size,(2560,1440))
            with Image.open(source) as im:self.assertEqual(im.size,(3840,2160))

    def test_small_input_is_not_upscaled(self):
        self.assertTrue(hasattr(lens,'lt_input'))
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'screen.png'
            Image.new('RGB',(1280,720),'white').save(source)
            self.assertEqual(lens.lt_input(source),source)
