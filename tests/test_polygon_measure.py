import math
import unittest
import polygon_measure


class PolygonMeasureTests(unittest.TestCase):
    def measure(self, points):
        self.assertTrue(callable(getattr(polygon_measure, 'polygon_measures', None)),
                        'OCR box measurements are not implemented')
        return polygon_measure.polygon_measures(points)

    def test_rectangle_and_reverse(self):
        points = [(0, 0), (3, 0), (3, 4), (0, 4)]
        self.assertEqual(self.measure(points), (12, 14))
        self.assertEqual(self.measure(points[::-1]), (12, 14))

    def test_rotated_and_translated_box(self):
        self.assertEqual(self.measure([(100, 101), (101, 100), (102, 101), (101, 102)]),
                         (2, 4 * math.sqrt(2)))

    def test_zero_area(self):
        self.assertEqual(self.measure([(1, 2)] * 4), (0, 0))

    def test_reference_rounding(self):
        box = [[1529.0643310546875, -1060.8265380859375],
               [1186.4005126953125, -903.4170532226562],
               [1166.4591064453125, -946.8274536132812],
               [1509.1229248046875, -1104.2369384765625]]
        self.assertEqual(self.measure(box), (18014.140039622784, 849.721462508989))

    def test_invalid_shape_and_nonfinite(self):
        for box in ([], [(0, 0)] * 3, [(float('nan'), 0)] * 4,
                    [(float('inf'), 0)] * 4):
            with self.assertRaises(ValueError):
                self.measure(box)
