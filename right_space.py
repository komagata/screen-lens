"""Experimental right-side uniform-pixel budget, not semantic layout detection."""
import numpy as np
import math


def extend_down(image, box, background, max_extra=16, obstacles=(), _pixels=None):
    """Only exact-background rows, retaining a gap before reserved rectangles."""
    left,top,right,bottom=box
    limit=min(image.height-1,bottom+max_extra)
    for x,y,r,b in obstacles:
        if min(right,r)>max(left,x) and b>bottom:
            limit=min(limit,max(bottom,math.floor(y)-2))
    area=np.asarray(image.convert('RGB')) if _pixels is None else _pixels
    end=bottom
    for y in range(bottom,limit+1):
        strip=area[y,max(0,left-1):min(image.width,right+1)]
        if np.any(strip!=np.asarray(background)):
            return (left,top,right,max(bottom,y-1))
        end=y
    return (left,top,right,end)


def extend(image, box, background, max_extra=160, tolerance=15, _pixels=None):
    left,top,right,bottom=box
    limit=min(image.width-1,right+max_extra)
    area=np.asarray(image.convert('RGB')).astype(np.int16) if _pixels is None else _pixels
    bg=np.asarray(background)
    end=right
    for x in range(right,limit+1):
        column=area[max(0,top-1):min(image.height,bottom+1),x]
        if np.any(np.abs(column-bg)>tolerance):
            end=max(right,x-1)
            break
        end=x
    return (left,top,end,bottom)
