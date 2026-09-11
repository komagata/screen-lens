"""Experimental bounded vertical allocation and minimum-displacement fitting."""
import numpy as np
import json
from pathlib import Path
import subprocess


def budgets(image,base,obstacles=()):
    pixels=np.asarray(image.convert('RGB'));result=[]
    for index,row in enumerate(base):
        x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
        if min(x,y)<0 or min(w,h)<=0 or x+w>image.width or y+h>image.height:
            raise ValueError('Invalid display geometry')
        bg=np.median(pixels[y:y+h,x:x+w].reshape(-1,3),axis=0)
        extra=max(48,min(256,3*row['maximum_font_size'])) if 'maximum_font_size' in row else 16
        lower=max(1,y-extra);upper=min(image.height-1,y+h+extra)
        for other in list(base[:index])+list(base[index+1:])+list(obstacles):
            if min(x+w,other['x']+other['width'])<=max(x,other['x']):continue
            end=int(other['y']+other['height']);start=int(other['y'])
            if end<=y:lower=max(lower,(end+y+1)//2+1)
            elif start>=y+h:upper=min(upper,(start+y+h)//2-1)
            # OCR padding crossing one edge only blocks that direction, not
            # the empty space on the opposite side of this text rectangle.
            elif start<y and end<y+h:lower=y
            elif start>y and end>y+h:upper=y+h
            else:lower=y;upper=y+h
        top=y;bottom=y+h
        # Near-white/translucent surfaces can vary by a few 8-bit levels even
        # in blank space. Geometry bounds still reserve gaps around OCR regions.
        for candidate in range(y-1,lower-1,-1):
            if np.any(np.abs(pixels[candidate-1:candidate+1,max(0,x-1):min(image.width,x+w+1)]-bg)>4):break
            top=candidate
        for candidate in range(y+h,upper):
            if np.any(np.abs(pixels[candidate:candidate+2,max(0,x-1):min(image.width,x+w+1)]-bg)>4):break
            bottom=candidate+1
        result.append(dict(row,y=top,height=bottom-top))
    return result


def fit(base,budget,can_fit):
    above=int(base['y']-budget['y'])
    below=int(budget['y']+budget['height']-base['y']-base['height'])
    if min(above,below)<0 or base['x']!=budget['x'] or base['width']!=budget['width']:
        raise ValueError('Budget must contain base with same horizontal geometry')
    for added in range(above+below+1):
        for up in range(min(above,added)+1):
            if added-up<=below:
                candidate=dict(base,y=base['y']-up,height=base['height']+added)
                if can_fit(candidate):return candidate
    return dict(base)


def fit_translations(base,budget,translations,minimum=12,maximum=16):
    requests=[];owners=[];fits={}
    for index,(row,limit) in enumerate(zip(base,budget)):
        # The renderer leaves unchanged source pixels intact; no sizing is needed.
        if translations[row['id']]==row.get('text'):continue
        owners.append(index)
        requests.append(dict(text=translations[row['id']],width=int(row['width']),height=int(limit['height']),
            minimum_font_size=row.get('minimum_font_size',minimum),maximum_font_size=row.get('maximum_font_size',maximum),measure_only=True))
    # Bound each subprocess payload, but share batches across row boundaries.
    for offset in range(0,len(requests),32):
        batch=requests[offset:offset+32]
        response=subprocess.run(['/usr/bin/python',str(Path(__file__).with_name('pango_patch.py'))],
            input=json.dumps(batch),capture_output=True,text=True,check=True,timeout=10)
        results=json.loads(response.stdout)
        if len(results)!=len(batch):raise ValueError('Fit result count mismatch')
        fits.update((owner,result.get('minimum_height')) for owner,result in zip(owners[offset:offset+32],results))
    return [dict(row) if translations[row['id']]==row.get('text') else
            fit(row,limit,lambda candidate:fits[index] is not None and candidate['height']>=fits[index])
            for index,(row,limit) in enumerate(zip(base,budget))]
