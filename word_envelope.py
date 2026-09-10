"""Experimental word-margin geometry; callers must independently reread candidates."""
import math
import numpy as np
from discovery_merge import valid_box


def refine(image,rows,read_line):
    result=[];audit=[]
    for row in rows:
        candidate=propose(image,row)
        if candidate is None:
            result.append(row)
            continue
        value,confidence=read_line(image,candidate)
        accepted=(value==row['text'] and type(confidence) in (int,float)
                  and math.isfinite(confidence) and .9<=confidence<=1)
        audit.append(dict(original=row,candidate=candidate,reading=value,
                          confidence=confidence,accepted=accepted))
        result.append(candidate if accepted else row)
    return result,audit


def propose(image,row):
    if not valid_box(row,image.size) or row.get('ocr_preserve'):
        return None
    words=row.get('ocr_words')
    if not isinstance(words,(list,tuple)) or not words:
        return None
    points=[];texts=[]
    for word in words:
        if not isinstance(word,(list,tuple)) or len(word)!=3 or not isinstance(word[0],str):
            return None
        quad=word[2]
        if not isinstance(quad,(list,tuple)) or len(quad)!=4:
            return None
        for point in quad:
            if (not isinstance(point,(list,tuple)) or len(point)!=2
                or not all(type(v) in (int,float) and math.isfinite(v) for v in point)):
                return None
            x,y=point
            if not (row['x']<=x<=row['x']+row['width'] and row['y']<=y<=row['y']+row['height']):
                return None
        points.extend(quad);texts.append(word[0])
    if ''.join(texts)!=row['text'].replace(' ',''):
        return None
    x,y=math.ceil(row['x']),math.ceil(row['y'])
    right,bottom=math.floor(row['x']+row['width']),math.floor(row['y']+row['height'])
    left=max(x,math.floor(min(p[0] for p in points))-2)
    end=min(right,math.ceil(max(p[0] for p in points))+2)
    if end<=left or bottom<=y or (left==x and end==right):
        return None
    area=np.asarray(image.convert('RGB').crop((x,y,right,bottom))).astype(np.int16)
    bg=np.median(area.reshape(-1,3),axis=0)
    # Require both columns around a new boundary to be background. This is a
    # geometric risk check, not evidence that everything outside is an icon.
    for side,boundary in (('left',left),('right',end)):
        if x<boundary<right:
            strip=area[:,boundary-x-1:boundary-x+1]
            if np.any(np.max(np.abs(strip-bg),axis=2)>30):
                if side=='left':left=x
                else:end=right
    if left==x and end==right:
        return None
    return dict(row,x=left,y=y,width=end-left,height=bottom-y)
