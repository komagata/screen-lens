"""Estimate Japanese pixel sizes from original OCR lines, before space allocation."""
import statistics
import numpy as np


def source_ink_height(image, row):
    """Measure visible glyphs in an OCR line on a reasonably uniform surface."""
    x,y,w,h=(round(row[k]) for k in ('x','y','width','height'))
    if w<2 or h<2 or x<0 or y<0 or x+w>image.width or y+h>image.height:
        return float(row['height'])
    pixels=np.asarray(image.crop((x,y,x+w,y+h)).convert('RGB')).astype(float)
    border=np.concatenate((pixels[0],pixels[-1],pixels[:,0],pixels[:,-1]))
    bg=np.median(border,axis=0)
    if np.mean(np.max(np.abs(border-bg),axis=1)>30)>.2:
        return float(h)
    ink=np.max(np.abs(pixels-bg),axis=2)>40
    active=np.flatnonzero(ink.sum(axis=1)>=max(1,round(w*.005)))
    if len(active)<2 or ink.mean()>.6:
        return float(h)
    measured=int(active[-1]-active[0]+1)
    return float(measured) if measured>=h*.25 else float(h)


def match_source_fonts(groups, rows, image=None):
    by_id = {row['id']: row for row in rows}
    result = []
    for group in groups:
        lines = [by_id[i] for i in group.get('members', [group['id']]) if i in by_id]
        heights = [(source_ink_height(image,line) if image is not None else float(line['height']))
                   for line in lines if line['height'] > 0]
        # Use line heights, never the height of a multi-line paragraph or an
        # expanded display box. OCR coordinates are already in processing pixels.
        target = max(7, min(128, round(statistics.median(heights) if heights else group['height'])))
        result.append(dict(group, source_ink_height=target, minimum_font_size=max(7, round(target * .75)),
                           maximum_font_size=target))
    return result
