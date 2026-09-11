"""Experimental display policy, not a general code classifier or OCR validator."""
import re
from datetime import date


def numeric_signature(text):
    """Compare signed numbers/common units; normalize valid English month dates."""
    months='January February March April May June July August September October November December'.split()
    pattern=r'\b('+'|'.join(months)+r')\s+(\d{1,2}),\s*(\d{4})\b'
    def canonical(match):
        month=next(i for i,name in enumerate(months,1) if name.lower()==match[1].lower())
        try:
            value=date(int(match[3]),month,int(match[2]))
        except ValueError:
            return match[0]
        return value.isoformat()
    normalized=re.sub(pattern,canonical,text,flags=re.IGNORECASE)
    # Preserve common UI quantity units without treating following prose as a
    # unit. This is a bounded guard, not a general physical-units parser.
    units = r'(?:[kKMGTPE]?i?[Bb]|[munµ]?s|seconds?|minutes?|hours?|[kMG]?Hz|[mk]?[VAW]|°?[CF])\b'
    return re.findall(r'([+\-−]?\d+(?:[.,]\d+)*)(?:\s*(%|‰|' + units + r'))?', normalized)


def negation_signature(text):
    """Bounded English cue check, not semantic equivalence or scope analysis."""
    cues = re.findall(r"\b(?:not|no|never|without|cannot)\b|n['’]t\b", text.lower())
    return ['not' if cue in ('cannot', "n't", 'n’t') else cue for cue in cues]


def visual_reading(row,candidate):
    source=row['text']
    literal=r'[_\\/`$|{}=]|(?:^|\s)--?\w'
    reason=None
    if not candidate.strip():
        reason='empty visual reading'
    elif len(source.strip().splitlines())==1 and len(candidate.strip().splitlines())>1:
        reason='unexpected multiple lines'
    elif re.search(literal,source) or re.search(literal,candidate):
        reason='literal-like syntax'
    elif re.findall(r'@[A-Za-z0-9_]+',source)!=re.findall(r'@[A-Za-z0-9_]+',candidate):
        reason='mention disagreement'
    elif numeric_signature(source)!=numeric_signature(candidate):
        reason='numeric disagreement'
    elif negation_signature(source)!=negation_signature(candidate):
        reason='negation disagreement'
    result=dict(row,ocr_original=source,ocr_candidate=candidate)
    if reason:
        result.update(ocr_preserve=True,ocr_preserve_reason=reason)
    else:
        result.update(text=candidate,ocr_reading='vision')
        words=row.get('ocr_words',[])
        compact=lambda value: re.sub(r'\s','',value)
        # Align only an exact suffix at word boundaries. Leave omitted pixels
        # untouched; this does not classify them as icons or prove the reading.
        if words and compact(''.join(w[0] for w in words))==compact(source):
            matches=[i for i in range(1,len(words))
                     if compact(''.join(w[0] for w in words[i:]))==compact(candidate)]
            if len(matches)==1:
                points=[p for w in words[matches[0]:] for p in w[2]]
                omitted=[p for w in words[:matches[0]] for p in w[2]]
                # CTC word positions can fall inside glyphs. A small margin
                # must not extend into the estimated omitted prefix.
                left=max(row['x'],max(p[0] for p in omitted),min(p[0] for p in points)-3)
                right=min(row['x']+row['width'],max(p[0] for p in points)+3)
                # Overlapping word boxes do not establish a safe prefix boundary.
                if max(p[0] for p in omitted)<=min(p[0] for p in points) and row['x']<left<right:
                    result.update(x=left,width=right-left,
                                  ocr_original_box=[row[k] for k in ('x','y','width','height')],
                                  ocr_geometry='exact-word-suffix')
    return result
