import unittest
from PIL import Image
from balanced_space import budgets


class BalancedCoverageTests(unittest.TestCase):
    def test_header_padding_overlap_does_not_block_space_below_body(self):
        body = dict(id='body', x=20, y=40, width=180, height=28)
        header = dict(id='header', x=20, y=20, width=100, height=22)
        limit = budgets(Image.new('RGB', (300, 150), 'white'), [body], [header])[0]
        self.assertEqual(limit['y'], body['y'])
        self.assertGreater(limit['height'], body['height'])

    def test_footer_padding_overlap_does_not_block_space_above_body(self):
        body = dict(id='body', x=20, y=40, width=180, height=28)
        footer = dict(id='footer', x=20, y=66, width=100, height=22)
        limit = budgets(Image.new('RGB', (300, 150), 'white'), [body], [footer])[0]
        self.assertLess(limit['y'], body['y'])
        self.assertEqual(limit['y'] + limit['height'], body['y'] + body['height'])

    def test_internal_obstacle_still_blocks_expansion(self):
        body = dict(id='body', x=20, y=40, width=180, height=28)
        obstacle = dict(id='other', x=20, y=45, width=100, height=10)
        self.assertEqual(budgets(Image.new('RGB', (300, 150), 'white'),
                                 [body], [obstacle]), [body])
