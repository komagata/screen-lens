"""Area and perimeter of an ordered four-corner OCR box, not general GIS geometry."""
import math


def polygon_measures(box):
    points = [(float(x), float(y)) for x, y in box]
    if len(points) != 4 or not all(math.isfinite(v) for p in points for v in p):
        raise ValueError('Expected four finite OCR corners')
    ring = points + points[:1]
    origin = points[0][0]
    # Translate the x origin to reduce cancellation in the shoelace sum.
    area = 0.0
    for i in range(1, 4):
        area += (ring[i][0] - origin) * (ring[i-1][1] - ring[i+1][1])
    length = 0.0
    for a, b in zip(ring, ring[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length += math.sqrt(dx * dx + dy * dy)
    return abs(area) / 2, length
