"""Local geometric suspicion of joined labels; not a semantic classifier."""
import math
import numpy as np
from discovery_merge import valid_box


def plan_partition_tiles(image,rows):
    """Rank wide multiword rows by internal blank-column width / row height.

    Development heuristic: ordinary word spaces can trigger it too. The caller
    must bound requests and corroborate proposed splits; this does not alter OCR.
    """
    image=image.convert('RGB')
    tiles=[]
    for index,row in enumerate(rows):
        text=row.get('text')
        if (not valid_box(row,image.size) or row.get('ocr_preserve')
                or not isinstance(text,str) or len(text.split())<3
                or not 17<=row['height']<=64 or row['width']<5*row['height']):continue
        x,y=math.floor(row['x']),math.floor(row['y'])
        right,bottom=math.ceil(row['x']+row['width']),math.ceil(row['y']+row['height'])
        pixels=np.asarray(image.crop((x,y,right,bottom))).astype(float)
        background=np.median(pixels.reshape(-1,3),axis=0)
        ink=(np.max(abs(pixels-background),axis=2)>30).any(axis=0)
        occupied=np.flatnonzero(ink)
        if len(occupied)<2:continue
        longest=int(np.max(np.diff(occupied)))-1
        ratio=longest/row['height']
        if ratio<.3:continue
        width=min(image.width,max(640,right-x+128))
        height=min(image.height,256)
        left=max(0,min(image.width-width,math.floor((x+right-width)/2)))
        top=max(0,min(image.height-height,math.floor((y+bottom-height)/2)))
        tiles.append(dict(box=[left,top,left+width,top+height],scale=2,
                          seeds=[index],gap_ratio=ratio))
    return sorted(tiles,key=lambda t:-t['gap_ratio'])
