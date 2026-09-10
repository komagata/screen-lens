"""Opt-in static display allocation; OCR and translation coordinates stay intact."""
import math
import numpy as np
from right_space import extend, extend_down
from space_reservations import reserve


def allocate(image, groups, obstacles=()):
    def rectangle(row):
        values=[row[k] for k in ('x','y','width','height')]
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Invalid display geometry')
        x,y,w,h=map(int,values)
        if x<0 or y<0 or w<=0 or h<=0 or x+w>image.width or y+h>image.height:
            raise ValueError('Display geometry outside image')
        return (x,y,x+w,y+h)

    original={i:rectangle(row) for i,row in enumerate(groups)}
    reserved=dict(original)
    reserved.update({len(groups)+i:rectangle(row) for i,row in enumerate(obstacles)})
    candidates=dict(reserved);audit=[]
    # Shared read-only source for all region scans; never mutate OCR or pixels.
    area=np.asarray(image.convert('RGB')).astype(np.int16)
    for index,row in enumerate(groups):
        x,y,right,bottom=original[index]
        pixels=area[y:bottom,x:right]
        bg=np.median(pixels.reshape(-1,3),axis=0)
        box=extend(image,original[index],bg,max_extra=640 if 'maximum_font_size' in row else 160,tolerance=0,_pixels=area)
        others=[r for key,r in reserved.items() if key!=index]
        for l,t,r,b in others:
            if l>=right and min(bottom,b)>max(y,t):
                box=(x,y,min(box[2],max(right,l-2)),bottom)
        box=extend_down(image,box,bg,obstacles=others,_pixels=area)
        candidates[index]=box
        audit.append(dict(id=row['id'],old_box=list(original[index]),candidate_box=list(box)))
    selected=reserve(reserved,candidates)
    display=[]
    for index,row in enumerate(groups):
        x,y,right,bottom=selected[index]
        display.append(dict(row,x=x,y=y,width=right-x,height=bottom-y))
        audit[index].update(display_box=list(selected[index]),
                            expansion_rejected=selected[index]!=candidates[index])
    return display,audit
