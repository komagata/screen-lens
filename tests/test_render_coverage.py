import unittest
from PIL import Image
from source_font import match_source_fonts
from snapshot import render


class RenderCoverageTests(unittest.TestCase):
    def test_long_translation_can_shrink_without_disappearing(self):
        image = Image.new('RGB', (900, 80), 'white')
        rows = [dict(id='0', text='At least one light and one dark done properly',
                     x=10, y=10, width=830, height=31)]
        groups = match_source_fonts(rows, [dict(rows[0], height=20)])
        _, report = render(image, groups, {'0': 'ライトとダークを最低1つずつ適切に完成させる（リポジトリ構成、README、デスクトップのプレビュー、'}, renderer='pango')
        self.assertTrue(report[0]['shown'], report)
        self.assertGreaterEqual(report[0]['font_size'], 12)

    def test_fallback_does_not_force_tiny_or_overflowing_text(self):
        image = Image.new('RGB', (200, 80), 'white')
        rows = [dict(id='0', text='Heading', x=10, y=10, width=80, height=24)]
        groups = match_source_fonts(rows, rows)
        _, report = render(image, groups, {'0': '長すぎる文章です。' * 30}, renderer='pango')
        self.assertFalse(report[0]['shown'])
        self.assertEqual(report[0]['reason'], 'does not fit')
