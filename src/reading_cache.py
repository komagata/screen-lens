"""Process-local exact-input cache for visual OCR readings."""

import json


def cached_reading(image, rows, cache, read):
    configuration = ('visual-reading-v1', json.dumps(rows, sort_keys=True, ensure_ascii=False))
    return cache.recognize(image, configuration, lambda source: read(source, rows))
