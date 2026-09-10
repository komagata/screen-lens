"""Two-frame, process-local cache for local OCR only."""
from collections import OrderedDict
from copy import deepcopy
import hashlib


class OcrFrameCache:
    def __init__(self):
        self._entries=OrderedDict()

    def recognize(self,image,configuration,recognize):
        # Callers supply an immutable tuple identifying all local OCR settings.
        # Keep digests and OCR rows, never screenshots or cloud responses on disk.
        key=(image.mode,image.size,hashlib.sha256(image.tobytes()).digest(),configuration)
        if key in self._entries:
            self._entries.move_to_end(key)
            return deepcopy(self._entries[key])
        rows=recognize(image)
        self._entries[key]=deepcopy(rows)
        while len(self._entries)>2:
            self._entries.popitem(last=False)
        return rows
