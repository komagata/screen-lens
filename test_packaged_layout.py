import unittest
from PIL import Image


class PackagedLayoutTests(unittest.TestCase):
    def test_layout_runs_without_experiments_directory(self):
        from display_space import allocate
        image = Image.new('RGB', (300, 100), 'white')
        rows = [dict(id='0', text='Settings', x=20, y=20, width=60, height=20)]
        result, audit = allocate(image, rows)
        self.assertEqual(result[0]['id'], '0')
        self.assertGreaterEqual(result[0]['width'], 60)


if __name__ == '__main__':
    unittest.main()
