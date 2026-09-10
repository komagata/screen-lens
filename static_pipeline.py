"""Experimental fixed-image pipeline; no desktop capture or oracle annotation.

Without --cloud only local OCR/structure run. With --cloud the selected image
and its OCR text are sent to OpenAI. Context tiles are geometric neighborhoods,
NOT detected cards. Inspect images for confidential content before opting in.
"""
import argparse
import json
import math
import re
from pathlib import Path
import time
from PIL import Image
from paragraphs import paragraphs
from ocr_backends import DEFAULT_UI_PROFILE


def context_tile(row,size):
    iw,ih=size
    x,y,w,h=(row[k] for k in ('x','y','width','height'))
    if not all(math.isfinite(v) for v in (x,y,w,h)) or w<=0 or h<=0 or x<0 or y<0 or x+w>iw or y+h>ih:
        raise ValueError('Target outside image')
    tw=min(iw,max(640,math.ceil(w)+128));th=min(ih,max(480,math.ceil(h)+256))
    left=max(0,min(iw-tw,math.floor(x+w/2-tw/2)))
    top=max(0,min(ih-th,math.floor(y+h/2-th/2)))
    return [left,top,tw,th]


def prepare(path,rows):
    from layout_lines import horizontal_lines
    with Image.open(path) as image:
        groups=paragraphs(rows,separators=horizontal_lines(image),image=image)
        for row in groups:
            row['context_box']=context_tile(row,image.size)
    return dict(image=str(Path(path).resolve()),lines=rows,groups=groups)


def translate_regions(case,mode,key):
    from stage_translation import request_translation
    translations={};usage=[]
    for row in case['groups']:
        values,cost=request_translation(dict(case,groups=[row]),mode,key)
        translations.update(values);usage.append(cost)
    return translations,usage


def recognition_candidates(rows,corroborate=False,readable=False):
    selected=[]
    for row in rows:
        if row.get('ocr_preserve'):continue
        text=row['text']
        if not (corroborate or readable or row.get('confidence',1)>=.9):continue
        if not re.search('[A-Za-z]{2}',text):continue
        # In readable mode a single Han glyph may be a misread icon. This is
        # only a rereading candidate, never a declaration that it is English.
        if re.search(r'[\u3040-\u30ff]',text):continue
        if len(re.findall(r'[\u3400-\u9fff]',text))>(1 if readable else 0):continue
        selected.append(row)
    return selected


def refine_ocr(image,rows,key,corroborate=False,readable=False,before_request=None,separate_lines=False):
    if corroborate and readable:
        raise ValueError('Choose one OCR acceptance mode')
    from stage_vision_ocr import request_recognition
    selected=recognition_candidates(rows,corroborate=corroborate,readable=readable)
    input_by_id={row['id']:row for row in rows}
    if separate_lines:
        from ocr_boundaries import input_boxes
        boxes=input_boxes(image,rows)
        input_by_id={r['id']:dict(r,ocr_input_box=boxes[r['id']]) for r in rows}
        selected=[input_by_id[r['id']] for r in selected]
    values={};usage=[];batched_ids=set()
    for offset in range(0,len(selected),20):
        if before_request is not None:
            before_request()
        batch=selected[offset:offset+20]
        recognized,cost=request_recognition(image,batch,key)
        if len(batch)>1:batched_ids.update(r['id'] for r in batch)
        values.update(recognized);usage.append(cost)
    if readable:
        from reading_policy import visual_reading
        corrected=[];retries=0
        for row in rows:
            result=visual_reading(row,values[row['id']]) if row['id'] in values else dict(row)
            if (row['id'] in batched_ids and retries<3
                    and result.get('ocr_preserve_reason') in ('numeric disagreement','mention disagreement')):
                if before_request is not None:before_request()
                options={'scale':4} if result.get('ocr_preserve_reason')=='numeric disagreement' else {}
                retry,cost=request_recognition(image,[input_by_id[row['id']]],key,**options)
                usage.append(cost);retries+=1
                result=visual_reading(row,retry[row['id']])
                result.update(ocr_first_candidate=values[row['id']],ocr_retry_count=1,
                              ocr_retry_scale=options.get('scale',2))
            if separate_lines and row['id'] in values:
                result['ocr_input_box']=input_by_id[row['id']]['ocr_input_box']
            corrected.append(result)
        return corrected,usage
    corrected=[]
    for row in rows:
        candidate=values.get(row['id'],row['text'])
        if corroborate and row['id'] in values and (candidate!=row['text'] or row.get('confidence',1)<.9):
            from ocr_corroboration import recognize_line
            if candidate.strip() and recognize_line(image,row)==candidate:
                corrected.append(dict(row,text=candidate,ocr_original=row['text'],ocr_corroborated=True))
                continue
        if candidate==row['text']:
            corrected.append(dict(row))
        elif (re.fullmatch(r'[A-Za-z0-9\s]+',candidate)
              and re.fullmatch(r'[A-Za-z0-9\s]+',row['text'])
              and re.sub(r'\s','',candidate)==re.sub(r'\s','',row['text'])):
            corrected.append(dict(row,text=candidate))
        else:
            # Neither recognizer is an oracle. Preserve the source pixels when
            # letters, numbers or punctuation disagree, including ordinary prose.
            corrected.append(dict(row,ocr_uncertain=True,ocr_candidate=candidate))
    return corrected,usage


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cloud',action='store_true')
    parser.add_argument('--renderer',choices=['pil','pango'],default='pil',help='Pango requires system Python with gi/cairo and fonts')
    parser.add_argument('--recover-display-regions',action='store_true',help='Experimental local inset/background recovery; requires --renderer pango')
    parser.add_argument('--expand-display-space',action='store_true',help='Experimental exact-background right/down space allocation; never changes OCR input')
    parser.add_argument('--separate-display-lines',action='store_true',help='Local background trimming and exact rereading of overlapping display groups; OCR source stays unchanged')
    parser.add_argument('--balanced-display-space',action='store_true',help='Share vertical gaps and fit with minimum movement; requires --expand-display-space --renderer pango')
    parser.add_argument('--concise-translation',action='store_true',help='Fidelity-first concise translation with approximate layout hints; requires --balanced-display-space')
    parser.add_argument('--match-source-font-size',action='store_true',help='Size Japanese text from original OCR line heights')
    parser.add_argument('--minimum-font-size',type=int,choices=range(7,25))
    parser.add_argument('--maximum-font-size',type=int,choices=range(7,25))
    parser.add_argument('--ocr-profile',choices=['v5','v5-v6','v6'],default=DEFAULT_UI_PROFILE)
    parser.add_argument('--ocr-threads',type=int,choices=range(1,65),default=4)
    parser.add_argument('--word-regions',action='store_true',help='Experimental word-gap segmentation and local crop rereading')
    parser.add_argument('--merge-overlaps',action='store_true',help='Experimental local rereading of overlapping same-line OCR fragments')
    parser.add_argument('--trim-word-margins',action='store_true',help='Experimental boundary-checked word margins; requires --word-regions')
    parser.add_argument('--tight-geometry',action='store_true',help='Second local OCR pass for text-agreeing, pixel-preserving geometry; no extra cloud request')
    ui_options=parser.add_mutually_exclusive_group()
    ui_options.add_argument('--ui-segmentation',action='store_true',help='Experimental isolated local UI detector; must be installed separately')
    ui_options.add_argument('--ui-partition',action='store_true',help='Experimental UI proposals with full-parent rereading; local detector must be installed')
    parser.add_argument('--vision-ocr',action='store_true',help='Experimental cloud rereading before structuring; requires --cloud')
    parser.add_argument('--visual-paragraphs',action='store_true',help='One additional image request for constrained paragraph decisions; requires --cloud')
    parser.add_argument('--discover-ocr',action='store_true',help='Experimental small-text discovery audit only; candidates are not rendered; requires --cloud')
    parser.add_argument('--partition-ocr',action='store_true',help='Experimental image/local-agreement label splitting; requires --cloud')
    parser.add_argument('--partition-budget',type=int,choices=range(5),default=1,help='Maximum additional image requests for label splitting')
    parser.add_argument('--discovery-budget',type=int,choices=range(5),default=1,help='Maximum additional discovery requests (default 1, maximum 4)')
    parser.add_argument('--corroborate-ocr',action='store_true',help='Experimental Tesseract corroboration of vision OCR; requires --vision-ocr')
    parser.add_argument('--readable-ocr',action='store_true',help='Experimental visual reading with literal/number guards; requires --vision-ocr')
    parser.add_argument('--separate-ocr-lines',action='store_true',help='Opt-in uniform-background line separation for OCR inputs only; requires --vision-ocr')
    parser.add_argument('--per-target',action='store_true',help='One request per region; slower, less target mixing')
    parser.add_argument('--translation-batches',type=int,choices=[1,2],default=1,
                        help='Opt-in two parallel translation requests; duplicates image context input')
    parser.add_argument('--mode',choices=['text','nearby','image','combined','crop','crop_full'],default='crop_full')
    args=parser.parse_args(argv)
    if args.translation_batches==2 and (not args.cloud or args.per_target):
        parser.error('--translation-batches 2 requires --cloud and excludes --per-target')
    if args.recover_display_regions:
        if args.renderer!='pango':
            parser.error('--recover-display-regions requires --renderer pango')
        if args.minimum_font_size is None:args.minimum_font_size=12
        if args.maximum_font_size is None:args.maximum_font_size=16
    if args.concise_translation and not args.balanced_display_space:
        parser.error('--concise-translation requires --balanced-display-space')
    if args.balanced_display_space:
        if not args.expand_display_space or args.renderer!='pango':
            parser.error('--balanced-display-space requires --expand-display-space --renderer pango')
        if args.minimum_font_size is None:args.minimum_font_size=12
        if args.maximum_font_size is None:args.maximum_font_size=16
    if args.visual_paragraphs and not args.cloud:
        parser.error('--visual-paragraphs requires --cloud')
    if args.minimum_font_size is not None and args.maximum_font_size is not None and args.minimum_font_size>args.maximum_font_size:
        parser.error('Minimum font size exceeds maximum')
    if args.trim_word_margins and not args.word_regions:
        parser.error('--trim-word-margins requires --word-regions')
    if args.partition_ocr and not args.cloud:
        parser.error('--partition-ocr requires --cloud')
    if args.discover_ocr and not args.cloud:
        parser.error('--discover-ocr requires --cloud')
    if args.readable_ocr and args.corroborate_ocr:
        parser.error('Choose one OCR acceptance mode')
    if args.readable_ocr and not args.vision_ocr:
        parser.error('--readable-ocr requires --vision-ocr')
    if args.separate_ocr_lines and not args.vision_ocr:
        parser.error('--separate-ocr-lines requires --vision-ocr')
    if args.vision_ocr and not args.cloud:
        parser.error('--vision-ocr requires --cloud')
    if args.corroborate_ocr and not args.vision_ocr:
        parser.error('--corroborate-ocr requires --vision-ocr')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    from ocr_backends import recognize_rapid,recognize_word_regions,make_rapid
    started=time.monotonic()
    recognize=recognize_word_regions if args.word_regions else recognize_rapid
    engine=make_rapid(args.ocr_profile,intra_threads=args.ocr_threads)
    from stage_ocr import line_crop
    def read_local(image,part):
        value=engine(line_crop(image,part),use_det=False,use_rec=True,use_cls=False)
        return (value.txts[0] if value.txts else '',
                float(value.scores[0]) if value.scores is not None and len(value.scores) else 0)
    rows=recognize(args.image,engine)
    ocr_seconds=time.monotonic()-started
    initial_rows=rows
    overlap=[]
    if args.merge_overlaps:
        from overlap_reading import reread_overlaps
        (args.output/'ocr-initial.json').write_text(json.dumps(initial_rows,ensure_ascii=False,indent=2))
        with Image.open(args.image) as image:
            rows,overlap=reread_overlaps(image,rows,read_local)
        (args.output/'overlap.json').write_text(json.dumps(overlap,ensure_ascii=False,indent=2))
    ui_detection=None;ui_audit=[];ui_proposals=[];ui_seconds=0
    if args.ui_segmentation or args.ui_partition:
        from ui_detector import detect_regions
        from ui_segmentation import segment_rows
        (args.output/'ocr-initial.json').write_text(json.dumps(initial_rows,ensure_ascii=False,indent=2))
        before=time.monotonic()
        ui_detection=detect_regions(args.image)
        with Image.open(args.image) as image:
            if args.ui_partition:
                from ui_segmentation import recognize_ui_partitions
                rows,ui_audit,ui_proposals=recognize_ui_partitions(image,rows,ui_detection,engine)
            else:
                rows,ui_audit=segment_rows(image,rows,ui_detection)
        ui_seconds=time.monotonic()-before
    recognition_usage=[]
    recognition_started=time.monotonic()
    if args.vision_ocr:
        from stage_translation import credentials
        # Preserve the unmodified detector/recognizer result even if cloud fails.
        (args.output/'ocr-initial.json').write_text(json.dumps(initial_rows,ensure_ascii=False,indent=2))
        with Image.open(args.image) as image:
            rows,recognition_usage=refine_ocr(image,rows,credentials(),corroborate=args.corroborate_ocr,readable=args.readable_ocr,separate_lines=args.separate_ocr_lines)
    recognition_seconds=time.monotonic()-recognition_started if args.vision_ocr else 0
    discovery=None
    if args.discover_ocr:
        from discovery_stage import discover,request_discovery
        from stage_translation import credentials
        # Keep the source OCR intact; discovered regions are unverified proposals.
        (args.output/'ocr-initial.json').write_text(json.dumps(initial_rows,ensure_ascii=False,indent=2))
        key=credentials() if args.discovery_budget else None
        with Image.open(args.image) as image:
            discovery=discover(image,rows,lambda crop:request_discovery(crop,key),
                               max_calls=args.discovery_budget)
        (args.output/'discovery.json').write_text(json.dumps(discovery,ensure_ascii=False,indent=2))
    partition=None
    if args.partition_ocr:
        from partition_stage import refine_partitions
        from discovery_stage import request_discovery
        from stage_translation import credentials
        (args.output/'ocr-before-partition.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        key=credentials() if args.partition_budget else None
        with Image.open(args.image) as image:
            rows,partition=refine_partitions(image,rows,lambda crop:request_discovery(crop,key),
                                            read_local,max_calls=args.partition_budget)
        (args.output/'partition.json').write_text(json.dumps(partition,ensure_ascii=False,indent=2))
    word_margin_audit=[]
    if args.trim_word_margins:
        from word_envelope import refine
        (args.output/'ocr-before-trim.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        def read_exact(image,part):
            value=engine(line_crop(image,part,padding=0),use_det=False,use_rec=True,use_cls=False)
            return (value.txts[0] if value.txts else '',
                    float(value.scores[0]) if value.scores is not None and len(value.scores) else 0)
        with Image.open(args.image) as image:
            rows,word_margin_audit=refine(image,rows,read_exact)
        (args.output/'word-margins.json').write_text(json.dumps(word_margin_audit,ensure_ascii=False,indent=2))
    tight_audit=[];tight_seconds=0
    if args.tight_geometry:
        tight_started=time.monotonic()
        from tight_geometry import select
        from live import refine_geometry
        (args.output/'ocr-before-tight.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        detector=engine.text_det.postprocess_op
        old_ratio=detector.unclip_ratio
        try:
            detector.unclip_ratio=1.2
            candidates=recognize(args.image,engine)
            with Image.open(args.image) as image:
                candidates=refine_geometry(image,candidates,engine,merge_overlaps=args.merge_overlaps,
                                           trim_word_margins=args.trim_word_margins)
                rows,tight_audit=select(image,rows,candidates)
        finally:
            detector.unclip_ratio=old_ratio
        (args.output/'tight-geometry.json').write_text(json.dumps(dict(candidates=candidates,audit=tight_audit),ensure_ascii=False,indent=2))
        tight_seconds=time.monotonic()-tight_started
    case=prepare(args.image,rows)
    structure_audit=None
    if args.visual_paragraphs:
        from visual_structure import request_structure
        from stage_translation import credentials
        (args.output/'ocr-before-structure.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        eligible={g['id'] for g in paragraphs([dict(r,ocr_atomic=True) for r in rows])}
        structure_rows=[dict(r,ocr_atomic=True) if r['id'] not in eligible else dict(r) for r in rows]
        groups,structure_audit=request_structure(args.image,structure_rows,credentials())
        groups=[g for g in groups if g['id'] in eligible]
        with Image.open(args.image) as image:
            for group in groups:group['context_box']=context_tile(group,image.size)
        case=dict(case,groups=groups)
        (args.output/'visual-structure.json').write_text(json.dumps(structure_audit,ensure_ascii=False,indent=2))
    display_groups=case['groups'];display_audit=[]
    display_line_audit=None;display_line_seconds=0
    if args.separate_display_lines:
        from vertical_seams import normalize
        line_started=time.monotonic()
        def reread_display(image,row):
            value=engine(line_crop(image,row,padding=0),use_det=False,use_rec=True,use_cls=False)
            return (value.txts[0] if value.txts else '',
                    float(value.scores[0]) if value.scores is not None and len(value.scores) else 0)
        with Image.open(args.image) as image:
            display_groups,display_line_audit=normalize(image,case['groups'],reread_display)
        display_line_seconds=time.monotonic()-line_started
        (args.output/'display-lines.json').write_text(json.dumps(display_line_audit,ensure_ascii=False,indent=2))
    if args.match_source_font_size:
        from source_font import match_source_fonts
        with Image.open(args.image) as source_image:
            display_groups=match_source_fonts(display_groups,rows,source_image)
    display_budgets=[]
    if args.expand_display_space:
        from display_space import allocate
        members={i for group in case['groups'] for i in group.get('members',[group['id']])}
        obstacles=[row for row in rows if row['id'] not in members]
        with Image.open(args.image) as image:
            vertical_base={r['id']:r for r in display_groups}
            display_groups,display_audit=allocate(image,display_groups,obstacles)
            if args.balanced_display_space:
                from balanced_space import budgets
                display_groups=[dict(r,y=vertical_base[r['id']]['y'],height=vertical_base[r['id']]['height']) for r in display_groups]
                display_budgets=budgets(image,display_groups,obstacles)
    layout_hints={}
    if args.concise_translation:
        import math
        font=args.minimum_font_size
        layout_hints={}
        for r in display_groups:
            size=r.get('maximum_font_size',font)
            layout_hints[r['id']]=max(1,int(r['width']//size))*max(1,1+int((r['height']-math.ceil(size*7/6))//math.ceil(size*1.5)))
        case=dict(case,concise=True,layout_hints=layout_hints)
    report=dict(source=case['image'],mode=args.mode,renderer=args.renderer,per_target=args.per_target,translation_batches=args.translation_batches,ocr_profile=args.ocr_profile,word_regions=args.word_regions,ocr=rows,groups=case['groups'],
                recover_display_regions=args.recover_display_regions,
                concise_translation=args.concise_translation,layout_hints=layout_hints,
                visual_paragraphs=args.visual_paragraphs,structure_audit=structure_audit,
                tight_geometry=args.tight_geometry,tight_audit=tight_audit,tight_seconds=tight_seconds,
                separate_display_lines=args.separate_display_lines,display_line_audit=display_line_audit,display_line_seconds=display_line_seconds,
                balanced_display_space=args.balanced_display_space,display_budgets=display_budgets,
                expand_display_space=args.expand_display_space,display_groups=display_groups,display_audit=display_audit,
                minimum_font_size=args.minimum_font_size,maximum_font_size=args.maximum_font_size,
                ui_segmentation=args.ui_segmentation,ui_partition=args.ui_partition,ui_proposals=ui_proposals,
                ui_detection=ui_detection,ui_audit=ui_audit,ui_seconds=ui_seconds,
                ocr_initial=initial_rows,vision_ocr=args.vision_ocr,corroborate_ocr=args.corroborate_ocr,readable_ocr=args.readable_ocr,separate_ocr_lines=args.separate_ocr_lines,recognition_usage=recognition_usage,
                vision_ocr_seconds=recognition_seconds,ocr_threads=args.ocr_threads,
                ocr_seconds=ocr_seconds,cloud=args.vision_ocr or bool(structure_audit and structure_audit['pairs']) or bool(discovery and discovery['calls']) or bool(partition and partition['calls']),
                discovery=discovery,partition=partition,overlap=overlap,merge_overlaps=args.merge_overlaps,
                trim_word_margins=args.trim_word_margins,word_margin_audit=word_margin_audit)
    report_path=args.output/'report.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if args.cloud and case['groups']:
        from stage_translation import credentials,request_translation
        from snapshot import render
        before=time.monotonic()
        translate=translate_regions if args.per_target else request_translation
        if args.translation_batches==2:
            from stage_translation import request_translation_parallel
            translate=request_translation_parallel
        translations,usage=translate(case,args.mode,credentials())
        translation_seconds=time.monotonic()-before
        if args.balanced_display_space:
            from balanced_space import fit_translations
            display_groups=fit_translations(display_groups,display_budgets,translations,args.minimum_font_size,args.maximum_font_size)
            report['display_groups']=display_groups
        font_options={key:value for key,value in dict(minimum_font_size=args.minimum_font_size,
                     maximum_font_size=args.maximum_font_size).items() if value is not None}
        with Image.open(args.image) as image:
            if args.recover_display_regions:
                from experiments.ppocr6.recovery_core import recover
                recovery_started=time.monotonic()
                def reread_recovery(image,row):
                    value=engine(line_crop(image,row,padding=0),use_det=False,use_rec=True,use_cls=False)
                    return (value.txts[0] if value.txts else '',
                            float(value.scores[0]) if value.scores is not None and len(value.scores) else 0)
                members={i for group in case['groups'] for i in group.get('members',[group['id']])}
                obstacles=[row for row in rows if row['id'] not in members]
                result,rendered,recovery_audit=recover(image,display_groups,translations,reread_recovery,
                    independent_axes=True,expand_interior=True,context_components=True,asymmetric=True,
                    obstacles=obstacles,**font_options)
                recovered={r['id']:r['box'] for r in recovery_audit if r['accepted']}
                report['display_groups_before_recovery']=display_groups
                display_groups=[dict(r,x=recovered[r['id']][0],y=recovered[r['id']][1],
                    width=recovered[r['id']][2]-recovered[r['id']][0],
                    height=recovered[r['id']][3]-recovered[r['id']][1]) if r['id'] in recovered else r for r in display_groups]
                report.update(display_groups=display_groups,display_recovery=recovery_audit,
                              display_recovery_seconds=time.monotonic()-recovery_started)
                (args.output/'display-recovery.json').write_text(json.dumps(recovery_audit,ensure_ascii=False,indent=2))
            else:
                result,rendered=render(image,display_groups,translations,renderer=args.renderer,**font_options)
        result.save(args.output/'translated.png')
        report.update(cloud=True,translations=translations,rendered=rendered,usage=usage,
                      translation_seconds=translation_seconds,total_seconds=time.monotonic()-started)
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(dict(targets=len(case['groups']),cloud=report['cloud'],
                         shown=sum(r['shown'] for r in report.get('rendered',[])))))


if __name__=='__main__':
    main()
