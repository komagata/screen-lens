"""Opt-in screenshot experiment. OCR text only is sent to the translation API.

Writes sensitive screen data locally; never use on confidential screens.
"""
import argparse
import base64
import io
import json
import re
from pathlib import Path
import statistics
import subprocess
import time
from PIL import Image, ImageDraw, ImageFont

FONT='/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
ASCII_URL = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+", re.IGNORECASE)


def render(image,rows,translations,renderer='pil',minimum_font_size=None,maximum_font_size=None,pixel_scale=1):
    if type(pixel_scale) not in (int,float) or not .5<=pixel_scale<=4:
        raise ValueError('Invalid pixel scale')
    if renderer not in ('pil','pango'):
        raise ValueError('Unknown renderer')
    if minimum_font_size is not None and (type(minimum_font_size) is not int or not 7<=minimum_font_size<=24):
        raise ValueError('Invalid minimum font size')
    if maximum_font_size is not None and (type(maximum_font_size) is not int or not 7<=maximum_font_size<=24):
        raise ValueError('Invalid maximum font size')
    if minimum_font_size is not None and maximum_font_size is not None and minimum_font_size>maximum_font_size:
        raise ValueError('Reversed font size range')
    original=image.convert('RGB')
    result=original.copy()
    report=[];pending=[]
    fallback_sizes={}
    for row in rows:
        value=translations[row['id']]
        if value==row['text']:
            continue
        x,y=int(row['x']),int(row['y'])
        w,h=int(row['width']),int(row['height'])
        entry=dict(id=row['id'],shown=False)
        report.append(entry)
        if sorted(re.findall(r'@[A-Za-z0-9_]+',value)) != sorted(re.findall(r'@[A-Za-z0-9_]+',row['text'])):
            entry['reason']='mention changed'
            continue
        # Compare occurrences, not just membership; never repair a changed URL
        # by guessing. This conservative guard covers explicit ASCII HTTP(S).
        if sorted(ASCII_URL.findall(value)) != sorted(ASCII_URL.findall(row['text'])):
            entry['reason']='URL changed'
            continue
        if x<0 or y<0 or w<=0 or h<=0 or x+w>image.width or y+h>image.height:
            entry['reason']='edge of image'
            continue
        border=[original.getpixel((a,b)) for a in range(max(0,x-1),min(image.width,x+w+1))
                for b in (y-1,y+h) if 0<=b<image.height]
        border.extend(original.getpixel((a,b)) for b in range(y,y+h)
                      for a in (x-1,x+w) if 0<=a<image.width)
        if not border:
            entry['reason']='no surrounding border'
            continue
        bg=tuple(int(statistics.median(p[c] for p in border)) for c in range(3))
        if sum(max(abs(p[c]-bg[c]) for c in range(3))>30 for p in border)>len(border)*.1:
            entry['reason']='nonuniform border'
            continue
        colors=original.crop((x,y,x+w,y+h)).getcolors(w*h)
        dominant_count,dominant=max(colors,key=lambda item:item[0])
        if dominant_count>w*h/2 and dominant!=bg:
            entry.update(reason='background mismatch',interior_background=list(dominant),background=list(bg))
            continue
        row_minimum=row.get('minimum_font_size',minimum_font_size)
        row_maximum=row.get('maximum_font_size',maximum_font_size)
        if renderer=='pango':
            request=dict(text=value,width=w,height=h,
                         pixel_scale=pixel_scale,
                         foreground=[15,20,25] if sum(bg)>384 else [231,233,234])
            if row_minimum is not None:request['minimum_font_size']=row_minimum
            if row_maximum is not None:request['maximum_font_size']=row_maximum
            if row.get('source_ink_height') and row_minimum is not None:
                fallback_sizes[row['id']]=min(row_minimum,max(12,round(row['source_ink_height']*.7)))
            pending.append((entry,x,y,w,h,bg,request))
            continue
        fitted=None
        minimum_size=round((row_minimum if row_minimum is not None else (7 if h/pixel_scale<=16 else 12))*pixel_scale)
        for size in range(min(round((row_maximum if row_maximum is not None else 24)*pixel_scale),h),minimum_size-1,-1):
            font=ImageFont.truetype(FONT,size)
            lines=['']
            for char in value:
                if char=='\n':
                    lines.append('')
                    continue
                if font.getlength(lines[-1]+char)>w and lines[-1]:
                    lines.append('')
                lines[-1]+=char
            # Clip compositing to the exact OCR box, never draw over adjacent UI.
            line_height=size+3
            ink_bottom=max((i*line_height+font.getbbox(line,anchor='lt')[3]
                            for i,line in enumerate(lines)),default=0)
            if ink_bottom<=h and all(font.getlength(line)<=w for line in lines):
                fitted=(font,lines,line_height,size)
                break
        if fitted is None:
            entry['reason']='does not fit'
            continue
        font,lines,line_height,size=fitted
        patch=Image.new('RGB',(w,h),bg)
        paint=ImageDraw.Draw(patch)
        fg='#0f1419' if sum(bg)>384 else '#e7e9ea'
        for i,line in enumerate(lines):
            paint.text((0,i*line_height),line,font=font,fill=fg,anchor='lt')
        result.paste(patch,(x,y))
        entry.update(shown=True,font_size=size,background=list(bg))
    def render_batch(batch):
        response=subprocess.run(['/usr/bin/python',str(Path(__file__).with_name('pango_patch.py'))],
            input=json.dumps([item[-1] for item in batch]),
            capture_output=True,text=True,check=True,timeout=10)
        rendered_batch=json.loads(response.stdout)
        if not isinstance(rendered_batch,list) or len(rendered_batch)!=len(batch):
            raise ValueError('Pango result count mismatch')
        return rendered_batch
    batches=[pending[offset:offset+32] for offset in range(0,len(pending),32)]
    if len(batches)>1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            rendered_batches=list(pool.map(render_batch,batches))
    else:
        rendered_batches=[render_batch(batch) for batch in batches]
    for batch,rendered_batch in zip(batches,rendered_batches):
        # Try normal source-matched sizing first. Only failed fits may shrink,
        # in the exact same box; no extra translation request or UI overlap.
        retries=[];retry_indices=[]
        for index,(item,rendered) in enumerate(zip(batch,rendered_batch)):
            floor=fallback_sizes.get(item[0]['id'])
            if rendered.get('reason')=='does not fit' and floor is not None and floor<item[-1]['minimum_font_size']:
                retries.append((*item[:-1],dict(item[-1],minimum_font_size=floor)))
                retry_indices.append(index)
        if retries:
            for index,retried in zip(retry_indices,render_batch(retries)):
                if retried.get('shown'):
                    retried['fit_fallback']=True
                    rendered_batch[index]=retried
        for (entry,x,y,w,h,bg,_),rendered in zip(batch,rendered_batch):
            png=rendered.pop('png',None)
            entry.update(rendered,renderer='pango',background=list(bg))
            if not rendered['shown']:continue
            with Image.open(io.BytesIO(base64.b64decode(png))) as tile:
                if tile.size!=(w,h):raise ValueError('Unexpected Pango tile size')
                patch=Image.new('RGB',(w,h),bg)
                tile=tile.convert('RGBA')
                patch.paste(tile,(0,0),tile)
                result.paste(patch,(x,y))
    return result,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from ocr_backends import recognize_rapid
    from paragraphs import paragraphs
    from lens import translate_openai
    from translation_context import attach_context
    started=time.monotonic()
    rows=recognize_rapid(args.image)
    targets=paragraphs(rows)
    # References are the grouped units, so a paragraph is not repeated as fragments.
    contextual=attach_context(targets,targets)
    translations=translate_openai(contextual,'gpt-5.6-luna',contextual=True)
    translated_at=time.monotonic()
    with Image.open(args.image) as image:
        result,rendered=render(image,targets,translations)
    args.output.mkdir(mode=0o700,parents=True,exist_ok=True)
    result.save(args.output/'translated.png')
    report=dict(source=str(args.image),ocr_translation_seconds=translated_at-started,
                total_seconds=time.monotonic()-started,ocr=rows,groups=targets,
                translations=translations,rendered=rendered)
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(dict(targets=len(targets),shown=sum(r['shown'] for r in rendered),
                         unchanged=sum(translations[r['id']]==r['text'] for r in targets),
                         abstained=sum(not r['shown'] for r in rendered),
                         seconds=report['total_seconds'])))


if __name__=='__main__':
    main()
