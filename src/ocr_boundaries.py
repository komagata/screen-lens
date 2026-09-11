"""Opt-in OCR input separation on uniform backgrounds; never changes display geometry."""
import math
import numpy as np


def input_boxes(image,rows):
    boxes=[]
    for row in rows:
        x,y,w,h=(row[k] for k in ('x','y','width','height'))
        if (not all(math.isfinite(v) for v in (x,y,w,h)) or w<=0 or h<=0
                or x>=image.width or y>=image.height or x+w<=0 or y+h<=0):
            raise ValueError('Invalid OCR input region')
        pad=0 if row.get('ocr_segmentation')=='ui-partition' else 3
        boxes.append((max(0,math.floor(x-pad)),max(0,math.floor(y-3)),
                      min(image.width,math.ceil(x+w+pad)),min(image.height,math.ceil(y+h+3))))
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate OCR IDs')
    return {r['id']:clip(image,b,b,boxes,skip_close_centers=False) or b for r,b in zip(rows,boxes)}


def clip(image, source, display, neighbors, *, skip_close_centers=True):
    left,top,right,bottom=display
    pixels=np.asarray(image.convert('RGB')).astype(np.int16)
    for other in neighbors:
        l,t,r,b=other
        if min(source[2],r)<=max(source[0],l):continue
        center=(source[1]+source[3])/2
        other_center=(t+b)/2
        if center==other_center:continue
        if skip_close_centers and abs(center-other_center)<=.5*min(source[3]-source[1],b-t):continue
        start=max(source[1],t);end=min(source[3],b)
        if start>=end:continue
        x0=max(0,min(source[0],l));x1=min(image.width,max(source[2],r))
        y0=max(0,min(source[1],t));y1=min(image.height,max(source[3],b))
        region=pixels[y0:y1,x0:x1]
        border=np.concatenate((region[0],region[-1],region[:,0],region[:,-1]))
        bg=np.median(border,axis=0)
        blank=[y for y in range(max(0,start),min(image.height,end))
               if min(center,other_center)<y<max(center,other_center)
               # Even low-contrast ink is not empty background. This strict
               # rule deliberately abstains on texture and compression noise.
               and np.all(pixels[y,x0:x1]==bg)]
        if not blank:return None
        boundary=min(blank,key=lambda y:abs(y-(start+end-1)/2))
        if other_center>center:bottom=min(bottom,boundary)
        else:top=max(top,boundary+1)
    return (left,top,right,bottom) if bottom>top else None
