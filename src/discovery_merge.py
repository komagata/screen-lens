"""Experimental selection of image-discovered additions; not a correctness verifier."""
import math
import re


def valid_box(row, size):
    values = [row.get(k) for k in ('x', 'y', 'width', 'height')]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        return False
    x, y, w, h = values
    return x >= 0 and y >= 0 and w > 0 and h > 0 and x+w <= size[0] and y+h <= size[1]


def overlaps(a, b):
    return (min(a['x']+a['width'], b['x']+b['width']) > max(a['x'], b['x'])
            and min(a['y']+a['height'], b['y']+b['height']) > max(a['y'], b['y']))


def select_additions(existing, candidates, image_size):
    """Keep disjoint prose candidates for further verification, never overwrite OCR.

    Caller supplies original-image coordinates and tile_edge from tile geometry.
    Accepted candidates still need image/geometry verification before rendering.
    Conservative literal filtering can also exclude valid prose and proper names.
    """
    if any(not valid_box(row, image_size) for row in existing):
        raise ValueError('Invalid existing OCR geometry')
    additions, audit = [], []
    for index, row in enumerate(candidates):
        text = row.get('text')
        if not valid_box(row, image_size):
            reason = 'invalid-box'
        elif row.get('tile_edge'):
            reason = 'tile-edge'
        elif (not isinstance(text, str) or not text.strip() or len(text) > 10000
              or not any(c.isalpha() for c in text)
              or re.search(r'[@/\\_`=]|\w\.\w|\.{2,}|…', text)):
            reason = 'literal-or-empty'
        elif any(overlaps(row, other) for other in existing + additions):
            reason = 'overlap'
        else:
            reason = 'added'
            additions.append(dict(text=text, **{k: row[k] for k in ('x','y','width','height')},
                                  ocr_discovery='image'))
        audit.append(dict(candidate=index, reason=reason))
    return additions, audit
