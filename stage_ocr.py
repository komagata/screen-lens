"""Recognition-only benchmark using oracle line boxes. No cloud calls."""
import argparse
import json
import math
from pathlib import Path
import time
from PIL import Image


def line_crop(image,row,padding=3,scale=1):
    x,y,w,h=(row[k] for k in ('x','y','width','height'))
    if (not all(math.isfinite(v) for v in (x,y,w,h,padding,scale))
            or w<=0 or h<=0 or padding<0 or scale<=0
            or x>=image.width or y>=image.height or x+w<=0 or y+h<=0):
        raise ValueError('Invalid crop')
    horizontal_padding=0 if row.get('ocr_segmentation')=='ui-partition' else padding
    box=(max(0,math.floor(x-horizontal_padding)),max(0,math.floor(y-padding)),
         min(image.width,math.ceil(x+w+horizontal_padding)),min(image.height,math.ceil(y+h+padding)))
    cropped=image.convert('RGB').crop(box)
    return cropped.resize((max(1,round(cropped.width*scale)),max(1,round(cropped.height*scale))),Image.Resampling.LANCZOS)


def main():
    import numpy as np
    from benchmark import distance
    from ocr_backends import make_rapid
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--scale',type=int,choices=[1,2],default=1)
    args=parser.parse_args()
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    manifest=json.loads(args.manifest.read_text());engine=make_rapid()
    report=dict(stage='oracle-box recognition only',scale=args.scale,cases=[])
    for case in manifest['cases']:
        rows=[]
        with Image.open(case['image']) as image:
            for row in case['lines']:
                crop=line_crop(image,row,scale=args.scale)
                started=time.monotonic()
                result=engine(np.asarray(crop)[:,:,::-1],use_det=False,use_cls=False)
                text=result.txts[0] if result.txts else ''
                rows.append(dict(id=row['id'],source=row['text'],recognized=text,
                                 errors=distance(row['text'],text),seconds=time.monotonic()-started))
        report['cases'].append(dict(id=case['id'],split=case['split'],rows=rows,
                                    exact=sum(r['source']==r['recognized'] for r in rows),total=len(rows)))
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(case['id'],report['cases'][-1]['exact'],len(rows),flush=True)


if __name__=='__main__':
    main()
