"""Experimental local union rereading for overlapping fragments on one line."""
import math
import re
from discovery_merge import valid_box


def reread_overlaps(image,rows,read_line):
    """One pass over disjoint pairs; conserve text except up to 3 shared characters.

    Whitespace is ignored for agreement only. Original readings stay in the
    audit. A confident conflicting rereading preserves both source regions.
    Geometric/reading agreement is not a general correctness guarantee.
    """
    used=set();replacements={};audit=[];identities={r['id'] for r in rows}
    for i,a in enumerate(rows):
        if i in used or not valid_box(a,image.size) or a.get('ocr_preserve'):continue
        for j,b in enumerate(rows):
            if j==i or j in used or not valid_box(b,image.size) or b.get('ocr_preserve'):continue
            if not a['x']<b['x']<a['x']+a['width']<b['x']+b['width']:continue
            overlap=a['x']+a['width']-b['x']
            vertical=min(a['y']+a['height'],b['y']+b['height'])-max(a['y'],b['y'])
            if (overlap>.35*min(a['width'],b['width']) or vertical<.8*min(a['height'],b['height'])
                    or min(a['height'],b['height'])<.7*max(a['height'],b['height'])):continue
            top=min(a['y'],b['y']);bottom=max(a['y']+a['height'],b['y']+b['height'])
            box=dict(x=a['x'],y=top,width=b['x']+b['width']-a['x'],height=bottom-top)
            text,confidence=read_line(image,box)
            left,right=(re.sub(r'\s','',r['text']) for r in (a,b))
            variants={left+right}
            variants.update(left+right[n:] for n in range(1,min(3,len(left),len(right))+1)
                            if left[-n:]==right[:n])
            reliable=(isinstance(text,str) and bool(text.strip())
                      and type(confidence) in (int,float) and math.isfinite(confidence) and .9<=confidence<=1)
            accepted=reliable and re.sub(r'\s','',text) in variants
            audit.append(dict(sources=[dict(a),dict(b)],reading=text,confidence=confidence,accepted=accepted))
            if reliable and not accepted:
                # A partial glyph can look like a real letter, even at high
                # confidence. Keep pixels rather than deciding which OCR won.
                for index,row in ((i,a),(j,b)):
                    replacements[index]=dict(row,ocr_preserve=True,
                                            ocr_preserve_reason='overlap reading disagreement')
                used.update((i,j));break
            if not accepted:continue
            identity=f"{a['id']}/overlap/{b['id']}"
            while identity in identities:identity+='~'
            identities.add(identity)
            replacements[i]=dict(box,id=identity,text=text,confidence=confidence,
                                 ocr_segmentation='overlap-reread',ocr_source_ids=[a['id'],b['id']])
            used.update((i,j));break
    return [replacements[i] if i in replacements else dict(row) for i,row in enumerate(rows)
            if i not in used or i in replacements],audit
