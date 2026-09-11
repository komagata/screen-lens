"""Conservative split of overlapping OCR boxes, requiring exact local rereading."""
import math
import numpy as np


def normalize(image,rows,read_line):
    _validate(image,rows)
    result=[];audit=[]
    for row in rows:
        x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
        overlaps=any(other['id']!=row['id']
            and min(x+w,other['x']+other['width'])>max(x,other['x'])
            and min(y+h,other['y']+other['height'])>max(y,other['y']) for other in rows)
        protected=any(row.get(k) for k in ('ocr_preserve','ocr_uncertain','ocr_atomic'))
        top,bottom=0,h
        if overlaps and not protected:
            area=np.asarray(image.convert('RGB').crop((x,y,x+w,y+h)))
            bg=np.median(area.reshape(-1,3),axis=0)
            ink=np.any(area!=bg,axis=2);occupied=np.flatnonzero(ink.any(axis=1))
            if len(occupied) and np.mean(~ink)>=.5:
                top=max(0,int(occupied[0])-1);bottom=min(h,int(occupied[-1])+2)
            assert not ink[:top].any() and not ink[bottom:].any()
        result.append(dict(row,y=y+top,height=bottom-top))
        audit.append(dict(id=row['id'],removed_top=top,removed_bottom=h-bottom))
    result,seams=separate(image,result,read_line)
    return result,dict(trimming=audit,seams=seams)


def _validate(image,rows):
    ids=[row['id'] for row in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate OCR IDs')
    for row in rows:
        values=[row[k] for k in ('x','y','width','height')]
        if not all(type(v) in (int,float) and math.isfinite(v) and v==int(v) for v in values):
            raise ValueError('Expected finite integer pixel geometry')
        x,y,w,h=values
        if x<0 or y<0 or min(w,h)<=0 or x+w>image.width or y+h>image.height:
            raise ValueError('Invalid OCR geometry')


def separate(image,rows,read_line):
    _validate(image,rows)
    result=[dict(row) for row in rows];audit=[]
    for ai in range(len(result)):
        for bi in range(len(result)):
            a,b=result[ai],result[bi]
            if any(r.get(flag) for r in (a,b) for flag in ('ocr_preserve','ocr_uncertain','ocr_atomic')):continue
            if a['y']>=b['y']:continue
            bottom=int(a['y']+a['height']);top=int(b['y'])
            if bottom<=top or bottom>=b['y']+b['height']:continue
            if min(a['x']+a['width'],b['x']+b['width'])<=max(a['x'],b['x']):continue
            left=int(min(a['x'],b['x']));right=int(max(a['x']+a['width'],b['x']+b['width']))
            band=np.asarray(image.convert('RGB').crop((left,top,right,bottom)))
            bg=np.median(band.reshape(-1,3),axis=0)
            blanks=np.flatnonzero(np.all(band==bg,axis=(1,2)))
            if not len(blanks):continue
            seam=top+int(blanks[len(blanks)//2])
            aa=dict(a,height=seam-int(a['y']))
            bb=dict(b,y=seam,height=int(b['y']+b['height'])-seam)
            if min(aa['height'],bb['height'])<=0:continue
            # Inside the overlap band, every non-background pixel covered by
            # either old box must still belong to at least one retained box.
            yy,xx=np.indices(band.shape[:2]);xx+=left;yy+=top
            def covered(row):
                return ((xx>=row['x']) & (xx<row['x']+row['width'])
                        & (yy>=row['y']) & (yy<row['y']+row['height']))
            lost=(covered(a)|covered(b)) & ~(covered(aa)|covered(bb))
            if np.any(lost & np.any(band!=bg,axis=2)):
                audit.append(dict(ids=[a['id'],b['id']],seam=seam,
                                  readings=[],accepted=False,reason='uncovered foreground'))
                continue
            readings=[read_line(image,row) for row in (aa,bb)]
            accepted=all(text==row['text'] and type(score) in (int,float)
                and math.isfinite(score) and .9<=score<=1
                for row,(text,score) in zip((aa,bb),readings))
            audit.append(dict(ids=[a['id'],b['id']],seam=seam,readings=readings,accepted=accepted))
            if accepted:result[ai]=aa;result[bi]=bb
    return result,audit
