"""Experimental split proposals with independent reading agreement; no rendering."""
import math
from discovery_merge import valid_box, overlaps


def partition_rows(rows, proposals, vision_texts, image_size):
    """Materialize checked splits for an explicitly opted-in experiment.

    Retain parents as preserved evidence and paint only the atomic child boxes.
    Callers must keep the original image for all gaps between those boxes.
    """
    plans=select_partitions([r for r in rows if not r.get('ocr_preserve')],
                            proposals,vision_texts,image_size)
    by_parent={p['source']['id']:p for p in plans}
    used={r['id'] for r in rows}
    result=[]
    for row in rows:
        plan=by_parent.get(row['id'])
        if plan is None:
            result.append(dict(row));continue
        result.append(dict(row,ocr_preserve=True))
        for index,child in enumerate(plan['children']):
            identity=f"{row['id']}/discovery/{index}"
            while identity in used:identity+='~'
            used.add(identity)
            result.append(dict(id=identity,text=child['text'],
                **{k:child[k] for k in ('x','y','width','height')},
                confidence=child['recognition_confidence'],ocr_parent_id=row['id'],
                ocr_parent_text=row['text'],ocr_atomic=True,
                ocr_segmentation='corroborated-discovery'))
    return result,plans


def select_partitions(rows, proposals, vision_texts, image_size):
    """Keep source evidence; unclaimed gaps must remain visible, not erased.

    Agreement is not a correctness guarantee. These are audit proposals only,
    not a replacement OCR stream. Confidence comes from the local recognizer.
    """
    result=[]
    for source in rows:
        if not valid_box(source,image_size):continue
        children=[]
        for part in proposals:
            confidence=part.get('recognition_confidence')
            text=part.get('text')
            if (source['id'] not in part.get('parents',[]) or not valid_box(part,image_size)
                    or not isinstance(text,str) or not text.strip()
                    or text!=vision_texts.get(part['id'])
                    or type(confidence) not in (int,float) or not math.isfinite(confidence)
                    or not .9<=confidence<=1):continue
            if (part['x']<source['x'] or part['y']<source['y']
                    or part['x']+part['width']>source['x']+source['width']
                    or part['y']+part['height']>source['y']+source['height']):continue
            children.append(dict(part))
        children.sort(key=lambda part:part['x'])
        if len(children)<2 or any(overlaps(a,b) for i,a in enumerate(children) for b in children[i+1:]):continue
        result.append(dict(source=dict(source),children=children,
                           status='corroborated-proposal',gaps='preserve-original'))
    return result
