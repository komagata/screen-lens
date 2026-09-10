"""Horizontal separator hints; not semantic form or table recognition."""


def horizontal_lines(image):
    import cv2
    import numpy as np
    edges=cv2.Canny(np.asarray(image.convert('L')),20,60)
    mask=cv2.morphologyEx(edges,cv2.MORPH_OPEN,np.ones((1,40),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    return [cv2.boundingRect(c) for c in contours]


def separates(above,below,lines):
    left=max(above['x'],below['x'])
    right=min(above['x']+above['width'],below['x']+below['width'])
    top=above['y']+above['height']/2
    bottom=below['y']+below['height']/2
    return right>left and any(top<y+h/2<bottom
        and min(right,x+w)-max(left,x)>=.7*(right-left) for x,y,w,h in lines)


def contrast_break(image,above,below):
    """A large ink-contrast change is a grouping boundary, not a UI role label."""
    import numpy as np
    contrasts=[]
    for row in (above,below):
        x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
        if w<=0 or h<=0 or x<0 or y<0 or x+w>image.width or y+h>image.height:
            return False
        pixels=np.asarray(image.crop((x,y,x+w,y+h)).convert('RGB')).reshape(-1,3).astype(float)
        background=np.median(pixels,axis=0)
        contrasts.append(float(np.percentile(np.max(np.abs(pixels-background),axis=1),90)))
    return max(contrasts)>=30 and min(contrasts)<.7*max(contrasts)


def whitespace_break(image,above,below):
    """Reject a join with more than one ink-height of visual whitespace.

    Only infer ink on majority-exact-background crops. No semantic UI labels;
    unknown or textured crops leave the existing grouping decision unchanged.
    """
    import numpy as np
    bounds=[]
    for row in (above,below):
        x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
        if w<=0 or h<=0 or x<0 or y<0 or x+w>image.width or y+h>image.height:
            return False
        pixels=np.asarray(image.crop((x,y,x+w,y+h)).convert('RGB'))
        bg=np.median(pixels.reshape(-1,3),axis=0)
        ink=np.any(pixels!=bg,axis=2)
        if np.mean(~ink)<.5:return False
        ys=np.flatnonzero(ink.any(axis=1))
        if not len(ys):return False
        bounds.append((y+int(ys[0]),y+int(ys[-1])+1))
    a,b=bounds
    return b[0]-a[1]>max(a[1]-a[0],b[1]-b[0])
