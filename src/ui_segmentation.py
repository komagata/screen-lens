"""Experimental gap proposals corroborated by UI regions; no model loading.

Returns absolute x cut coordinates, not new OCR text or confidence values.
Thresholds are development heuristics, not a general UI structure parser.
"""
import numpy as np
import re
import math


def recognize_ui_partitions(image,rows,detection,engine):
    """Explicit local experiment: UI boxes propose crops, never trusted replacements."""
    from stage_ocr import line_crop
    proposals=[]
    for index,(box,confidence) in enumerate(zip(detection['boxes'],detection['scores'])):
        l,t,r,b=box
        parents=[row['id'] for row in rows if
            .5*row['height']<=b-t<=2*row['height'] and
            row['y']<=(t+b)/2<=row['y']+row['height'] and
            l>=row['x']-3 and r<=row['x']+row['width']+3 and r-l<.95*row['width']]
        if not parents:continue
        part=dict(x=l,y=t,width=r-l,height=b-t)
        value=engine(line_crop(image,part),use_det=False,use_rec=True,use_cls=False)
        proposals.append(dict(part,id=index,parents=parents,detector_confidence=confidence,
            text=value.txts[0] if value.txts else '',
            recognition_confidence=float(value.scores[0]) if value.scores is not None else 0))
    def read_line(image,part):
        value=engine(line_crop(image,part),use_det=False,use_rec=True,use_cls=False)
        return value.txts[0] if value.txts else ''
    result,audit=partition_proposals(image,rows,proposals,read_line)
    return result,audit,proposals


def partition_proposals(image,rows,proposals,read_line):
    """Experimental full-parent partition; reader errors propagate, disagreement preserves."""
    result=[];audit=[];used={r['id'] for r in rows}
    if len(used)!=len(rows):raise ValueError('Duplicate OCR IDs')
    for row in rows:
        selected=sorted([p for p in proposals if row['id'] in p['parents']
            and math.isfinite(p['recognition_confidence']) and p['recognition_confidence']>=.5
            and math.isfinite(p['x']) and math.isfinite(p['width']) and p['width']>0
            and row['x']<=p['x'] and p['x']+p['width']<=row['x']+row['width']],key=lambda p:p['x'])
        if len(selected)<2 or any(a['x']+a['width']>b['x'] for a,b in zip(selected,selected[1:])):
            result.append(dict(row));continue
        x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
        pixels=np.asarray(image.convert('RGB').crop((x,y,x+w,y+h))).astype(float)
        background=np.median(pixels.reshape(-1,3),axis=0)
        ink=(np.max(np.abs(pixels-background),axis=2)>30).any(axis=0)
        cuts=[]
        for a,b in zip(selected,selected[1:]):
            left=a['x']+a['width'];right=b['x'];middle=(left+right)/2
            empty=[c for c in range(math.ceil(left),math.floor(right)+1)
                   if 0<=c-x<len(ink) and not ink[c-x]]
            if not empty:break
            cuts.append(min(empty,key=lambda c:(abs(c-middle),c)))
        if len(cuts)!=len(selected)-1:
            result.append(dict(row));continue
        edges=[row['x']]+cuts+[row['x']+row['width']]
        parts=[dict(row,x=left,width=right-left,ocr_segmentation='ui-partition') for left,right in zip(edges,edges[1:])]
        readings=[read_line(image,part) for part in parts]
        accepted=split_reading_matches(row['text'],readings)
        audit.append(dict(source=dict(row),cuts=cuts,readings=readings,accepted=accepted))
        if not accepted:
            result.append(dict(row));continue
        for i,(part,text) in enumerate(zip(parts,readings)):
            identity=f"{row['id']}/part/{i}"
            while identity in used:identity+='~'
            used.add(identity)
            part.pop('ocr_words',None)
            part.update(id=identity,text=text,ocr_parent_id=row['id'],ocr_parent_text=row['text'],
                        ocr_segmentation='ui-partition')
            result.append(part)
    return result,audit


def split_reading_matches(source,readings):
    """Conserve non-whitespace characters; agreement does not prove correctness."""
    return bool(readings) and all(s.strip() for s in readings) and (
        re.sub(r'\s','',source)==re.sub(r'\s','',''.join(readings)))


def segment_rows(image,rows,detection):
    """Split raw OCR rows and retain an audit; never silently discard a parent."""
    from ocr_corroboration import recognize_line
    result=[];audit=[];used={r['id'] for r in rows}
    if len(used)!=len(rows):raise ValueError('Duplicate OCR IDs')
    for row in rows:
        cuts=supported_cuts(image,row,detection)
        if not cuts:
            result.append(dict(row));continue
        edges=[row['x']]+cuts+[row['x']+row['width']]
        parts=[dict(row,x=left,width=right-left) for left,right in zip(edges,edges[1:])]
        readings=[recognize_line(image,part) for part in parts]
        accepted=split_reading_matches(row['text'],readings)
        audit.append(dict(source=dict(row),cuts=cuts,readings=readings,accepted=accepted))
        if not accepted:
            result.append(dict(row));continue
        for index,(part,text) in enumerate(zip(parts,readings)):
            identity=f"{row['id']}/ui/{index}"
            while identity in used:identity+='~'
            used.add(identity)
            part.update(id=identity,text=text,ocr_parent_id=row['id'],ocr_segmentation='ui-supported')
            result.append(part)
    return result,audit


def supported_cuts(image,row,detection):
    x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
    if x<0 or y<0 or w<=0 or h<=0 or x+w>image.width or y+h>image.height:
        raise ValueError('OCR region outside image')
    a=np.asarray(image.convert('RGB').crop((x,y,x+w,y+h))).astype(float)
    bg=np.median(np.concatenate([a[0],a[-1],a[:,0],a[:,-1]]),axis=0)
    ink=(np.max(abs(a-bg),axis=2)>30).any(axis=0)
    occupied=np.flatnonzero(ink)
    if not len(occupied):return []
    gaps=[];start=None
    for i in range(int(occupied[0]),int(occupied[-1])+1):
        if not ink[i] and start is None:start=i
        if ink[i] and start is not None:
            if i-start>=h*.8:gaps.append((start,i))
            start=None
    if not gaps:return []
    cuts=[(a+b)//2 for a,b in gaps]
    edges=[0]+cuts+[w]
    used=set()
    for left,right in zip(edges,edges[1:]):
        xs=np.flatnonzero(ink[left:right])+left+x
        if not len(xs):return []
        candidates=[]
        for index,(box,confidence) in enumerate(zip(detection['boxes'],detection['scores'])):
            l,t,r,b=box
            if (confidence>=.25 and t<=y+h/2<=b and b-t<=3*h
                    and l<=xs[0]+2 and r>=xs[-1]-2
                    and r-l<=1.6*(xs[-1]-xs[0]+1)):
                candidates.append((r-l,index))
        if not candidates:return []
        index=min(candidates)[1]
        if index in used:return []
        used.add(index)
    return [x+c for c in cuts]
