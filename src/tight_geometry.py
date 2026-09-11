"""Optional geometry-only selection between two local OCR passes."""
import math
import numpy as np


def select(image,baseline,tight):
    for row in list(baseline)+list(tight):
        values=[row[k] for k in ('x','y','width','height')]
        if not all(type(v) in (int,float) and math.isfinite(v) and v==int(v) for v in values):
            raise ValueError('Expected integer pixel geometry')
        x,y,w,h=values
        if min(x,y)<0 or min(w,h)<=0 or x+w>image.width or y+h>image.height:
            raise ValueError('Geometry outside image')
    def intersects(a,b):
        return (min(a['x']+a['width'],b['x']+b['width'])>max(a['x'],b['x'])
            and min(a['y']+a['height'],b['y']+b['height'])>max(a['y'],b['y']))
    selected=[];audit=[]
    for row in baseline:
        matches=[r for r in tight if r['text']==row['text'] and intersects(r,row)]
        candidate=matches[0] if len(matches)==1 else None
        if candidate is not None:
            reverse=[r for r in baseline if r['text']==candidate['text'] and intersects(r,candidate)]
            if len(reverse)!=1:candidate=None
        if candidate is not None and any(r.get(k) for r in (row,candidate)
            for k in ('ocr_preserve','ocr_uncertain','ocr_atomic')):candidate=None
        selected.append(dict(row,**{k:candidate[k] for k in ('x','y','width','height')}) if candidate else dict(row))
        audit.append(dict(id=row['id'],candidate=candidate is not None,reverted=False))
    pixels=np.asarray(image.convert('RGB'))
    while True:
        covered=np.zeros(pixels.shape[:2],bool)
        for row in selected:
            x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
            covered[y:y+h,x:x+w]=True
        revert=[]
        for i,row in enumerate(baseline):
            if selected[i]==row:continue
            x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
            area=pixels[y:y+h,x:x+w];bg=np.median(area.reshape(-1,3),axis=0)
            if np.any(np.any(area!=bg,axis=2)&~covered[y:y+h,x:x+w]):revert.append(i)
        if not revert:break
        for i in revert:selected[i]=dict(baseline[i]);audit[i]['reverted']=True
    return selected,audit
