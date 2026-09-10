"""Experimental wrapped-prose grouping, not a general social-feed parser."""
import re


def paragraphs(rows,separators=(),image=None,allow_indent=False):
    groups=[]
    history=[]
    for row in sorted(rows,key=lambda r:(r['y'],r['x'])):
        previous, previous_group=next(((r,g) for r,g in reversed(history)
            if min(r['x']+r['width'],row['x']+row['width'])>max(r['x'],row['x'])),(None,None))
        text=row['text'].strip()
        # Preserve author headers, but keep mentions inside prose with the
        # sentence they belong to (otherwise a wrapped tail is mistranslated).
        handle_header=re.search(r'@[A-Za-z0-9_]+\s*(?:[·•].*)?$',text)
        above_handle=any(re.match(r'^@[A-Za-z0-9_]+',r['text'].strip())
            and abs(r['x']-row['x'])<=row['height']*.5
            and row['height']*.5<=r['y']-row['y']<=row['height']*1.6 for r in rows)
        # OCR can split a name and timestamped handle into overlapping boxes.
        # Restrict this cue to adjacent metadata, not a bare inline mention.
        beside_handle=any(re.match(r'^@[A-Za-z0-9_]+\s*[·•]\s*\S+',r['text'].strip())
            and r['x']>row['x']
            and -row['height']<=r['x']-row['x']-row['width']<=2*row['height']
            and abs((r['y']+r['height']/2)-(row['y']+row['height']/2))<=.3*min(r['height'],row['height'])
            for r in rows)
        if (row.get('ocr_preserve',False) or row.get('ocr_uncertain',False)
                or (row.get('confidence',1)<.9 and not row.get('ocr_corroborated',False)
                    and row.get('ocr_reading')!='vision') or not re.search('[A-Za-z]{2}',text)
                or re.search(r'[\u3040-\u30ff\u3400-\u9fff]',text) or above_handle or beside_handle
                or handle_header or re.fullmatch(r'https?://\S+',text)):
            history.append((row,None))
            continue
        h=row['height']
        aligned=previous is not None and abs(row['x']-previous['x'])<=.5*h
        if allow_indent and previous is not None and image is not None:
            shared_width=min(row['x']+row['width'],previous['x']+previous['width'])-max(row['x'],previous['x'])
            # Permit a modest first-line/hanging indent only with substantial
            # column overlap; pixel whitespace/contrast checks below still apply.
            aligned=aligned or (abs(row['x']-previous['x'])<=max(h,previous['height'])
                                and shared_width>=.9*min(row['width'],previous['width']))
        join=(previous_group is not None and not row.get('ocr_atomic')
              and not re.match(r'^[•●▪‣]\s*',text)
              and not previous.get('ocr_atomic') and aligned
              # A timestamped chat header is not a wrapped body line. Keep
              # both rows eligible: a real sentence ending in a time is safe.
              and not re.search(r'\d{1,2}:\d{2}\s*(?:[ap]m)?\s*$',previous['text'],re.I)
              and not re.search(r'(?:\.{2,}|…)\s*$',previous['text'])
              and .65<=h/max(1,previous['height'])<=1.5
              and -.25*h<=row['y']-previous['y']-previous['height']<=.45*h)
        if join and separators:
            from layout_lines import separates
            join=not separates(previous,row,separators)
        if join and image is not None:
            from layout_lines import contrast_break,whitespace_break
            join=not contrast_break(image,previous,row) and not whitespace_break(image,previous,row)
        if join:
            group=previous_group
            right=max(group['x']+group['width'],row['x']+row['width'])
            group['x']=min(group['x'],row['x'])
            group['width']=right-group['x']
            group['height']=row['y']+h-group['y']
            group['text']+=' '+text
            group['members'].append(row['id'])
        else:
            group=dict(row,members=[row['id']])
            groups.append(group)
        history.append((row,group))
    # A clipped excerpt is not a complete sentence. Keep its original pixels
    # until a translation path can reliably preserve the missing continuation.
    # Only a trailing ellipsis is held back: internal pauses/omissions do not
    # imply that the end of the visible sentence is missing. This still cannot
    # distinguish a clipped title from a complete menu label such as Open….
    return [g for g in groups if not re.search(r'(?:\.{2,}|…)\s*$',g['text'])]
