"""Experimental small-text neighborhood selection; no network or image capture."""
import math
from discovery_merge import valid_box


def plan_tiles(rows, image_size, image=None):
    """Return 256px cells with 32px halo containing at least two small OCR seeds.

    This is not exhaustive: areas with no small OCR seeds remain undiscovered.
    Tiles may overlap; callers must budget requests and deduplicate discoveries.
    With image supplied, foreground height can also supply seeds inside tall
    boxes, and tiles expand to include each seed. This is opt-in and can select
    texture or decoration; it does not validate recognition results.
    """
    if len(image_size) != 2 or any(type(v) is not int or v <= 0 for v in image_size):
        raise ValueError('Image dimensions must be positive integers')
    if image is not None and image.size!=tuple(image_size):
        raise ValueError('Image dimensions do not match')
    seeds = []
    for index, row in enumerate(rows):
        text, confidence = row.get('text'), row.get('confidence')
        if not valid_box(row,image_size):continue
        small=4 <= row['height'] <= 16
        if not small and image is not None:
            import numpy as np
            box=(math.floor(row['x']),math.floor(row['y']),
                 math.ceil(row['x']+row['width']),math.ceil(row['y']+row['height']))
            pixels=np.asarray(image.crop(box).convert('RGB')).astype(np.int16)
            bg=np.median(pixels.reshape(-1,3),axis=0)
            occupied=np.flatnonzero(np.any(np.max(np.abs(pixels-bg),axis=2)>30,axis=1))
            # Selection hint only: background texture or decorations can also
            # create foreground. Never use this to trim or accept OCR text.
            small=bool(len(occupied) and 4<=occupied[-1]-occupied[0]+1<=16)
        if (small
                and isinstance(text, str) and len(text.strip()) >= 3
                and type(confidence) in (int, float) and math.isfinite(confidence)
                and confidence >= .5):
            seeds.append((index, row['x']+row['width']/2, row['y']+row['height']/2))
    width, height = image_size
    result = []
    for y in range(0, height, 256):
        for x in range(0, width, 256):
            box = [max(0,x-32), max(0,y-32), min(width,x+288), min(height,y+288)]
            members = [i for i,cx,cy in seeds if box[0] <= cx < box[2] and box[1] <= cy < box[3]]
            if len(members) >= 2:
                if image is not None:
                    box=[max(0,min(box[0],*(math.floor(rows[i]['x'])-8 for i in members))),
                         max(0,min(box[1],*(math.floor(rows[i]['y'])-8 for i in members))),
                         min(width,max(box[2],*(math.ceil(rows[i]['x']+rows[i]['width'])+8 for i in members))),
                         min(height,max(box[3],*(math.ceil(rows[i]['y']+rows[i]['height'])+8 for i in members)))]
                result.append(dict(box=box, scale=4, seeds=members))
    return result
