"""Greedy experimental space allocation; original OCR overlap is not repaired."""
import math


def reserve(original, candidates):
    if original.keys()!=candidates.keys():
        raise ValueError('Region IDs differ')
    for key,box in candidates.items():
        old=original[key]
        for rect in (old,box):
            if len(rect)!=4 or not all(math.isfinite(v) for v in rect) or rect[2]<=rect[0] or rect[3]<=rect[1]:
                raise ValueError('Invalid rectangle')
        if not (box[0]<=old[0] and box[1]<=old[1] and box[2]>=old[2] and box[3]>=old[3]):
            raise ValueError('Candidate must contain original')

    def overlaps(a,b):
        return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])

    selected={}
    for key,box in candidates.items():
        reserved=[other for other_id,other in original.items() if other_id!=key]
        reserved.extend(selected.values())
        selected[key]=original[key] if any(overlaps(box,other) for other in reserved) else box
    return selected
