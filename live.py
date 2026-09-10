"""Window translation, optionally following focus; readable_ocr sends OCR crops."""
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
from ocr_backends import DEFAULT_UI_PROFILE

ROOT = Path(__file__).parent
UI = ROOT / 'live-ui'


class RegionStability:
    """Track exact pixel stability independently; animated tiles cannot block others."""
    def __init__(self, settle=.65, tile_size=64):
        self.settle, self.tile_size = settle, tile_size
        self.size, self.tiles = None, {}

    def observe(self, image, now):
        image = image.convert('RGB')
        if image.size != self.size:
            self.size, self.tiles = image.size, {}
        step = self.tile_size
        for y in range(0, image.height, step):
            for x in range(0, image.width, step):
                key = (x // step, y // step)
                pixels = image.crop((x,y,min(x+step,image.width),min(y+step,image.height))).tobytes()
                old = self.tiles.get(key)
                if old is None or old[0] != pixels:
                    self.tiles[key] = (pixels, now)

    def stable(self, row, now):
        changed = self.changed_at(row)
        return changed is not None and now - changed >= self.settle

    def changed_at(self, row):
        """Latest observed tile change, not an exact physical screen-change time."""
        if self.size is None:
            return None
        import math
        step = self.tile_size
        changed = None
        for box in [row] + row.get('context_boxes', []):
            x, y = math.floor(box['x']), math.floor(box['y'])
            right = math.ceil(box['x'] + box['width'])
            bottom = math.ceil(box['y'] + box['height'])
            if x < 0 or y < 0 or right > self.size[0] or bottom > self.size[1] or right <= x or bottom <= y:
                return None
            for ty in range(y//step, (bottom-1)//step+1):
                for tx in range(x//step, (right-1)//step+1):
                    tile = self.tiles.get((tx,ty))
                    if tile is None:
                        return None
                    changed = tile[1] if changed is None else max(changed, tile[1])
        return changed


class BoundedSettle:
    """Debounce expensive OCR, but never let animation starve static text."""
    def __init__(self, quiet=.65, maximum=2):
        self.quiet,self.maximum=quiet,maximum
        self.reset()

    def reset(self):
        self.frame,self.started,self.changed=None,None,None

    def ready(self, frame, now):
        if self.started is None:self.started=now
        if frame!=self.frame or self.changed is None:
            self.frame,self.changed=frame,now
        return now-self.changed>=self.quiet or now-self.started>=self.maximum


class FrameGate:
    def __init__(self, settle):
        self.settle, self.frame, self.since, self.token = settle, None, 0, 0

    def observe(self, frame, now):
        if frame != self.frame:
            self.frame, self.since = frame, now
            self.token += 1
            return True
        return False

    def ready(self, now):
        return self.frame is not None and now-self.since >= self.settle

    def accepts(self, token):
        return self.frame is not None and self.token == token


def cached_translate(rows, cache, translate):
    from translation_context import context_key
    from lens import validate_translations
    missing = list({context_key(r): r for r in rows if context_key(r) not in cache}.values())
    if missing:
        result = translate(missing)
        validate_translations(result, [r['id'] for r in missing])
        for row in missing:
            cache[context_key(row)] = result[row['id']]
    translated = {r['id']: cache[context_key(r)] for r in rows}
    while len(cache) > 2000:
        del cache[next(iter(cache))]
    return translated


def active():
    return json.loads(subprocess.check_output(['hyprctl', 'activewindow', '-j'], timeout=2))


def monitor_app_context(monitor,clients):
    """Conservative local cache namespace; never include window titles/content."""
    workspaces={monitor.get(key,{}).get('id') for key in ('activeWorkspace','specialWorkspace')}
    workspaces.discard(None)
    identities=[]
    for client in clients:
        if client.get('monitor')!=monitor['id'] or not client.get('mapped',True) or client.get('hidden'):
            continue
        if workspaces and client.get('workspace',{}).get('id') not in workspaces and not client.get('pinned'):
            continue
        identities.append((client.get('stableId') or client.get('address',''),client.get('class','')))
    return json.dumps(sorted(identities),ensure_ascii=True)


def monitor_window_bounds(monitor, clients):
    workspaces={monitor.get(k,{}).get('id') for k in ('activeWorkspace','specialWorkspace')}
    workspaces.discard(None)
    bounds=[]
    scale=monitor.get('scale',1)
    for client in clients:
        if (client.get('monitor')!=monitor['id'] or not client.get('mapped',True) or client.get('hidden')
            or (workspaces and client.get('workspace',{}).get('id') not in workspaces and not client.get('pinned'))):continue
        if not client.get('at') or not client.get('size'):continue
        x,y=((client['at'][i]-monitor.get(('x','y')[i],0))*scale for i in range(2))
        w,h=(v*scale for v in client['size'])
        left,top=max(0,x),max(0,y)
        right,bottom=min(monitor['width'],x+w),min(monitor['height'],y+h)
        if right>left and bottom>top:
            bounds.append(dict(x=left,y=top,width=right-left,height=bottom-top))
    return sorted(bounds,key=lambda b:(b['x'],b['y'],b['width'],b['height']))


def capture_monitor(monitor):
    """Fail closed if the UI cannot hide; always restore after a capture attempt.

    The compositor settling delay needs real-render acceptance, not just IPC
    success. Window mode continues to use overlay-free toplevel capture.
    """
    command = ['qs', 'ipc', '-p', str(UI), 'call', 'lens', 'suspendCapture']
    response = subprocess.run([*command, 'true'], capture_output=True, check=True, timeout=2)
    if response.stdout.strip() != b'suspended':
        raise RuntimeError('Overlay did not acknowledge capture suspension')
    try:
        # 25ms passed repeated clean-capture/restore trials on both the actual
        # Hyprland host and isolated Sway. Zero wait gave no host speed benefit.
        time.sleep(.025)
        return subprocess.run(['grim', '-l', '0', '-o', monitor, '-'],
                              capture_output=True, check=True, timeout=3).stdout
    finally:
        subprocess.run([*command, 'false'], capture_output=True, check=True, timeout=2)


def reserve_requests(used, count):
    """Reserve a complete request group without partially consuming the limit."""
    if type(count) is not int or count < 1:
        raise ValueError('Request count must be a positive integer')
    if used + count > 30:
        raise RuntimeError('Request limit reached')
    return used + count


def monitor_batches(config,target_count):
    base=config.get('translation_batches',2)
    dense=config.get('dense_translation_batches',base)
    for count in (base,dense):
        if type(count) is not int or not 1<=count<=8:
            raise ValueError('Invalid translation batch count')
    return dense if target_count>40 else base


def translate_monitor(image, rows, references, directory, *, image_format='png', batches=2, context_max_side=None, service_tier=None):
    from stage_translation import credentials, request_translation_parallel
    if image_format not in ('png','jpeg'):
        raise ValueError('Unknown context image format')
    if type(batches) is not int or not 1<=batches<=8:
        raise ValueError('Translation batches must be an integer from 1 to 8')
    if context_max_side is not None:
        if type(context_max_side) is not int or context_max_side<1:
            raise ValueError('Context maximum side must be a positive integer')
        if max(image.size)>context_max_side:
            from PIL import Image
            original_size=image.size
            ratio=context_max_side/max(original_size)
            size=tuple(max(1,round(v*ratio)) for v in original_size)
            image=image.resize(size,Image.Resampling.LANCZOS)
            sx,sy=(size[i]/original_size[i] for i in range(2))
            def scaled(row):
                return dict(row,x=row['x']*sx,y=row['y']*sy,
                            width=row['width']*sx,height=row['height']*sy)
            rows=[scaled(row) for row in rows]
            references=[scaled(row) for row in references]
    # One processing job owns this private image; never keep it as a public asset.
    with tempfile.TemporaryDirectory(prefix='request-', dir=directory) as temp:
        path = Path(temp)/('context.'+image_format)
        if image_format=='jpeg':
            image.convert('RGB').save(path,quality=85,subsampling=0)
        else:
            image.save(path)
        started=time.monotonic()
        case=dict(image=str(path),groups=rows,lines=references)
        if service_tier is not None:case['service_tier']=service_tier
        translations,usage=request_translation_parallel(case,
                                                       'combined',credentials(),**({'batches':batches} if batches!=2 else {}))
        with (directory/'translation-metrics.jsonl').open('a') as log:
            log.write(json.dumps(dict(time_ms=int(time.time()*1000),seconds=time.monotonic()-started,
                                      targets=len(rows),usage=usage))+'\n')
        return translations


def visual_context_box(row, size):
    x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
    bounds=row.get('window_bounds',dict(x=0,y=0,width=size[0],height=size[1]))
    return (max(0,int(bounds['x']),x-64), max(0,int(bounds['y']),y-64),
            min(size[0],int(bounds['x']+bounds['width']),x+w+64),
            min(size[1],int(bounds['y']+bounds['height']),y+h+64))


def translation_targets(references, prose=False, image=None, context_separators=False, window_bounds=None):
    if window_bounds:
        buckets={}
        for row in references:
            intersections=[i for i,b in enumerate(window_bounds)
                if min(row['x']+row['width'],b['x']+b['width'])>max(row['x'],b['x'])
                and min(row['y']+row['height'],b['y']+b['height'])>max(row['y'],b['y'])]
            owner=None
            if len(intersections)==1:
                b=window_bounds[intersections[0]]
                if (row['x']>=b['x'] and row['y']>=b['y']
                    and row['x']+row['width']<=b['x']+b['width']
                    and row['y']+row['height']<=b['y']+b['height']):owner=intersections[0]
            # Ambiguous/partly occluded regions get no neighbouring references.
            key=('window',owner) if owner is not None else (('ambiguous',row['id']) if intersections else ('desktop',))
            buckets.setdefault(key,[]).append(row)
        result=[]
        for key,refs in buckets.items():
            rows=translation_targets(refs,prose,image,context_separators)
            if key[0]=='window':
                rows=[dict(r,window_bounds=window_bounds[key[1]]) for r in rows]
            result.extend(rows)
        return sorted(result,key=lambda r:(r['y'],r['x']))[:80]
    from translation_context import attach_context
    if context_separators and (not prose or image is None):
        raise ValueError('Context separators require prose and a source image')
    if prose:
        from paragraphs import paragraphs
        from layout_lines import horizontal_lines
        separators=horizontal_lines(image) if image is not None else None
        rows=paragraphs(references,separators=separators,image=image)[:80]
    else:
        rows=[r for r in references if r['confidence']>=.9 and re.search('[A-Za-z]{2}',r['text'])][:80]
    contextual=attach_context(rows,references,separators=separators if context_separators else ())
    # A new or removed separator can change membership outside existing text boxes.
    # Conservatively invalidate the overlay on any pixel change in this opt-in mode.
    dependencies=[dict(x=0,y=0,width=image.width,height=image.height)] if context_separators else []
    # Keep only geometry when the worker later strips nearby reference strings.
    return [dict(row,context_boxes=[dict(x=row['x']+ref['x'],y=row['y']+ref['y'],
                 width=ref['width'],height=ref['height']) for ref in row['nearby']]+dependencies)
            for row in contextual]


def attach_display_space(image,rows,references):
    from display_space import allocate
    members={i for row in rows for i in row.get('members',[row['id']])}
    obstacles=[r for r in references if r['id'] not in members]
    display,_=allocate(image,rows,obstacles)
    result=[]
    for original,expanded in zip(rows,display):
        region={k:expanded[k] for k in ('x','y','width','height')}
        result.append(dict(original,display_region=region,
                           context_boxes=list(original.get('context_boxes',[]))+[region]))
    return result


def prose_overlay(image,rows,translations,renderer='pil'):
    from PIL import Image
    from snapshot import render
    display=[dict(row,**row.get('display_region',{})) for row in rows]
    font_options=dict(minimum_font_size=12,maximum_font_size=16) if any('display_region' in row for row in rows) else {}
    pixel_scale=rows[0].get('pixel_scale',1) if rows else 1
    rendered,report=render(image,display,translations,renderer=renderer,pixel_scale=pixel_scale,**font_options)
    shown={r['id'] for r in report if r['shown']}
    overlay=Image.new('RGBA',image.size,(0,0,0,0))
    for row in display:
        if row['id'] not in shown:
            continue
        x,y,w,h=(int(row[k]) for k in ('x','y','width','height'))
        overlay.paste(rendered.crop((x,y,x+w,y+h)),(x,y))
    return overlay


def wait_for_update(future,timeout=.25):
    # Completion wakes the loop, but the next iteration still captures and
    # validates the current screen before displaying any translated result.
    if future is None:
        time.sleep(timeout)
    else:
        concurrent.futures.wait([future],timeout=timeout)


def write_state(directory, state):
    path = directory / 'state.next'
    path.write_text(json.dumps(state, ensure_ascii=False))
    path.replace(directory / 'state.json')


def unchanged_regions(source,current,rows):
    if source.size!=current.size:
        return []
    source,current=source.convert('RGB'),current.convert('RGB')
    result=[]
    comparisons={}
    for row in rows:
        for region in [row]+row.get('context_boxes',[]):
            x,y,w,h=(int(region[k]) for k in ('x','y','width','height'))
            box=(max(0,x-2),max(0,y-2),min(source.width,x+w+2),min(source.height,y+h+2))
            if box not in comparisons:
                comparisons[box]=source.crop(box).tobytes()==current.crop(box).tobytes()
            if not comparisons[box]:
                break
        else:
            result.append(row)
    return result


def refine_geometry(image,rows,engine,merge_overlaps=False,trim_word_margins=False):
    from stage_ocr import line_crop
    def read(part,padding):
        value=engine(line_crop(image,part,padding=padding),use_det=False,use_rec=True,use_cls=False)
        return (value.txts[0] if value.txts else '',
                float(value.scores[0]) if value.scores is not None and len(value.scores) else 0)
    if merge_overlaps:
        from overlap_reading import reread_overlaps
        rows,_=reread_overlaps(image,rows,lambda image,part:read(part,3))
    if trim_word_margins:
        from word_envelope import refine
        rows,_=refine(image,rows,lambda image,part:read(part,0))
    return rows


def local_ocr(image,engine,config,cache):
    from ocr_backends import recognize_word_regions,rapid_lines
    import numpy as np
    settings=(config.get('ocr_profile',DEFAULT_UI_PROFILE),bool(config.get('word_regions')),
              bool(config.get('merge_overlaps')),bool(config.get('trim_word_margins')))
    def recognize(source):
        if settings[1]:
            rows=recognize_word_regions(source,engine)
        else:
            # Materialize BGR once: a negative-stride view makes downstream
            # OpenCV crop operations repeatedly copy the entire screenshot.
            pixels=np.ascontiguousarray(np.asarray(source)[:,:,::-1])
            output=engine(pixels,use_det=True,use_rec=True,use_cls=False)
            rows=rapid_lines(output.boxes,output.txts,output.scores)
        return refine_geometry(source,rows,engine,merge_overlaps=settings[2],trim_word_margins=settings[3])
    return cache.recognize(image,settings,recognize)


def supports_resident_ocr(config):
    return bool(config.get('resident_ocr') and config.get('monitor_mode')
        and config.get('ocr_profile')=='v6' and config.get('ocr_threads')==8
        and config.get('detector_limit')=='max' and config.get('ocr_cuda') is True
        and not any(config.get(k) for k in ('word_regions','merge_overlaps','trim_word_margins')))


def worker(directory):
    from PIL import Image
    from lens import translate_openai, demo_translate
    from ocr_backends import make_rapid
    from ocr_frame_cache import OcrFrameCache
    config = json.loads((directory/'config.json').read_text())
    gate, cache = FrameGate(.65), {}
    # Pixel stability controls new work independently of the geometry gate:
    # prose overlays can keep unchanged regions while scrolling clears others.
    pixel_gate = FrameGate(.65)
    region_gate = RegionStability(.65)
    ocr_gate = BoundedSettle()
    frame_lock = threading.Lock()
    latest_image = None
    cache_target = None
    local_cache=OcrFrameCache()
    reading_cache=OcrFrameCache()
    future, submitted, calls, next_request = None, -1, 0, 0
    submitted_calls=0
    engine = None
    resident = None
    resident_failed = False
    ocr_runtime = {}
    state = dict(lines=[], overlay='', monitor=config['monitor'], status='連続翻訳 ON · 起動中')
    previous_overlay=None
    prose_source,prose_rows=None,[]
    prepared_overlay=None
    visible_ids=None
    overlay_version=0
    processed_digest=None
    retry_unstable=False

    def initialize_engine():
        nonlocal engine, resident, resident_failed
        if resident is not None:return
        initialized_at=time.monotonic()
        if supports_resident_ocr(config) and not resident_failed:
            try:
                from ocr_client import Client
                candidate=Client();candidate.ensure_running();resident=candidate
                readiness=candidate.readiness if isinstance(candidate.readiness,dict) else {}
                ocr_runtime.update(mode='resident',initialization_seconds=time.monotonic()-initialized_at,
                                   readiness=dict(readiness))
                return
            except Exception:
                resident_failed=True
        if engine is None:
            engine = make_rapid(config.get('ocr_profile',DEFAULT_UI_PROFILE),
                                intra_threads=config.get('ocr_threads',4),
                                detector_limit=config.get('detector_limit','min'),
                                cuda=bool(config.get('ocr_cuda',False)))
            ocr_runtime.update(mode='local-fallback' if resident_failed else 'local',
                               initialization_seconds=time.monotonic()-initialized_at)

    def process(pixels, token, target, pixel_scale=1, app_context=None, timing=None, window_bounds=None):
        nonlocal engine, calls, cache_target, resident, resident_failed
        started=time.monotonic()
        # A single worker owns the translation cache. Identical labels in a
        # different application need not have the same meaning.
        if config.get('follow_active') and target != cache_target:
            cache.clear()
            cache_target = target
        initialize_engine()
        with Image.open(io.BytesIO(pixels)) as captured:
            captured_image=captured.convert('RGB')
        if resident is not None:
            try:references=resident.recognize(pixels)
            except Exception:
                resident=None;resident_failed=True
                initialize_engine()
                references=local_ocr(captured_image,engine,config,local_cache)
        else:
            references=local_ocr(captured_image,engine,config,local_cache)
        ocr_done=time.monotonic()
        def reserve_request(count=1):
            nonlocal calls
            if not gate.accepts(token):
                raise RuntimeError('Frame expired')
            calls = reserve_requests(calls,count)
        if config.get('readable_ocr'):
            from static_pipeline import refine_ocr
            from stage_translation import credentials
            from reading_cache import cached_reading
            def read_image(image, rows):
                return refine_ocr(image,rows,credentials(),readable=True,
                                  before_request=reserve_request)[0]
            references=cached_reading(captured_image,references,reading_cache,read_image)
        rows = translation_targets(references,config.get('prose',False),image=captured_image,
                                   context_separators=config.get('context_separators',False),
                                   window_bounds=window_bounds)
        deferred=False
        region_changes=[]
        if config.get('monitor_mode'):
            for row in rows:
                row['pixel_scale']=pixel_scale
                row['app_context']=app_context
                box=visual_context_box(row,captured_image.size)
                row['visual_context']=hashlib.sha256(captured_image.crop(box).tobytes()).hexdigest()
                row['context_boxes'].append(dict(x=box[0],y=box[1],width=box[2]-box[0],height=box[3]-box[1]))
            with frame_lock:
                count=len(rows)
                rows = [r for r in unchanged_regions(captured_image, latest_image, rows)
                        if region_gate.stable(r, time.monotonic())] if latest_image is not None else []
                deferred=len(rows)<count
                region_changes=[dict(x=r['x'],y=r['y'],width=r['width'],height=r['height'],
                                     observed_change_monotonic=region_gate.changed_at(r)) for r in rows]
        def request(batch):
            if config['demo']:
                return {r['id']: demo_translate(batch).get(r['id'], r['text']) for r in batch}
            if config.get('monitor_mode'):
                batches=monitor_batches(config,len(batch))
                reserve_request(min(batches,len(batch)))
                options={}
                if batches!=2:options['batches']=batches
                if 'context_image_format' in config:options['image_format']=config['context_image_format']
                if 'context_max_side' in config:options['context_max_side']=config['context_max_side']
                if config.get('translation_priority'):options['service_tier']='priority'
                return translate_monitor(captured_image,batch,references,directory,**options)
            reserve_request()
            return translate_openai(batch, 'gpt-5.6-luna', contextual=True)
        context_done=time.monotonic()
        translations = cached_translate(rows, cache, request)
        translation_done=time.monotonic()
        if config.get('expand_display_space'):
            if not config.get('prose'):raise ValueError('Display expansion requires prose')
            rows=attach_display_space(captured_image,rows,references)
        with Image.open(io.BytesIO(pixels)) as image:
            size = image.size
            overlay=prose_overlay(image,rows,translations,renderer=config.get('renderer','pil')) if config.get('prose') else None
            source=image.convert('RGB') if config.get('prose') else None
        if config.get('monitor_mode'):
            finished=time.monotonic()
            metric=dict(time_ms=int(time.time()*1000),targets=len(rows),deferred=deferred,
                        ocr_runtime=dict(ocr_runtime),
                        ocr_seconds=ocr_done-started,context_seconds=context_done-ocr_done,
                        translation_seconds=translation_done-context_done,
                        render_seconds=finished-translation_done,total_seconds=finished-started)
            metric.update(timing or {})
            metric.update(process_started_monotonic=started,finished_monotonic=finished,
                          region_changes=region_changes)
            if timing:
                metric['pre_ocr_seconds']=started-timing['capture_finished_monotonic']
            with (directory/'pipeline-metrics.jsonl').open('a') as log:
                log.write(json.dumps(metric)+'\n')
        return [dict({k:v for k,v in r.items() if k != 'nearby'}, translated=translations[r['id']]) for r in rows
                if translations[r['id']] != r['text']], size, overlay, source, deferred

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        # Same owner thread as recognition; no pixels/cloud work until settled.
        # If warmup fails, process retries initialization via the existing error path.
        pool.submit(initialize_engine)
        while True:
            now = time.monotonic()
            try:
                if config.get('monitor_mode'):
                    monitors = json.loads(subprocess.check_output(['hyprctl','monitors','-j'],timeout=2))
                    monitor = next(m for m in monitors if m['name']==config['monitor'])
                    clients=json.loads(subprocess.check_output(['hyprctl','clients','-j'],timeout=2))
                    app_context=monitor_app_context(monitor,clients)
                    window_bounds=monitor_window_bounds(monitor,clients)
                    if window_bounds:app_context=json.dumps([app_context,window_bounds],sort_keys=True)
                    scale = monitor.get('scale',1)
                    window = dict(at=[monitor['x'],monitor['y']],
                                  size=[monitor['width']/scale,monitor['height']/scale],monitor=monitor['id'])
                    target, valid = monitor['name'], True
                    capture_started=time.monotonic()
                    pixels = capture_monitor(target)
                    capture_finished=time.monotonic()
                    with Image.open(io.BytesIO(pixels)) as image:
                        with frame_lock:
                            latest_image = image.convert('RGB')
                            region_gate.observe(latest_image, time.monotonic())
                else:
                    window = active()
                    target = window.get('stableId') if config.get('follow_active') else config['target']
                    valid = bool(target) and window.get('stableId') == target and window.get('mapped') and not window.get('hidden')
                    if valid:
                        pixels = subprocess.run(['grim', '-T', target, '-'],
                                                capture_output=True, check=True, timeout=3).stdout
                        # Recheck identity/geometry after capture, before accepting this frame.
                        after = active()
                        valid = all(after.get(k) == window.get(k) for k in ('stableId', 'at', 'size', 'monitor'))
                if valid:
                    digest=hashlib.sha256(pixels+(app_context.encode() if config.get('monitor_mode') else b'')).digest()
                    pixel_gate.observe((target, digest), now)
                    signature = ((target,app_context) if config.get('monitor_mode') else target, None if config.get('prose') and not config.get('readable_ocr') else digest, tuple(window['at']), tuple(window['size']), window['monitor'])
                    if gate.observe(signature, now):
                        state['lines'] = []
                        state['overlay'] = ''
                        prose_source=None
                        visible_ids=None
                        processed_digest=None
                    monitors = json.loads(subprocess.check_output(['hyprctl', 'monitors', '-j'], timeout=2))
                    monitor = next(m for m in monitors if m['id'] == window['monitor'])
                    state.update(monitor=monitor['name'], x=window['at'][0]-monitor['x'],
                                 y=window['at'][1]-monitor['y'], width=window['size'][0], height=window['size'][1])
                    state['status'] = '連続翻訳 ON · ' + ('固定訳テスト' if config['demo'] else f'OpenAIへ文字＋近隣文脈送信 · {calls}/30回')
                    if config.get('prose'):
                        state['status'] += ' · 段落翻訳（実験）'
                    if config.get('readable_ocr'):
                        state['status'] += ' · OCR画像もOpenAIへ送信'
                    state['status'] += ' · '+config.get('ocr_profile',DEFAULT_UI_PROFILE)
                else:
                    gate.observe(None, now)
                    pixel_gate.observe(None, now)
                    state.update(lines=[], overlay='', status='連続翻訳 ON · 対象外で一時停止')
                    prose_source=None
                    visible_ids=None
                    processed_digest=None
                if future is not None and future.done():
                    try:
                        rows, size, overlay, source, deferred = future.result()
                        if deferred and calls==submitted_calls:
                            # Local-only deferral spent no request budget.
                            # Retry after normal settling, not API cooldown.
                            next_request=0
                        if gate.accepts(submitted):
                            state.pop('lastError',None)
                            retry_unstable=deferred
                            state.update(lines=rows, imageWidth=size[0], imageHeight=size[1])
                            if overlay is not None:
                                prose_source,prose_rows=source,rows
                                prepared_overlay=overlay
                                visible_ids=None
                                state['lines']=[]
                    except Exception as error:
                        state['lastError'] = type(error).__name__
                        state.update(lines=[], overlay='', status='連続翻訳 ON · 翻訳失敗／上限 · OFF→ONで再開')
                        prose_source=None
                    future = None
                if valid and config.get('prose') and prose_source is not None:
                    with Image.open(io.BytesIO(pixels)) as current:
                        unchanged=unchanged_regions(prose_source,current,prose_rows)
                    ids=tuple(r['id'] for r in unchanged)
                    if ids!=visible_ids:
                        state['overlay']=''
                        if unchanged:
                            overlay_version+=1
                            path=directory/f'overlay-{overlay_version}.png'
                            # Reuse only when every translated region and its
                            # context still match; changed subsets need a redraw.
                            visible_overlay=(prepared_overlay if len(unchanged)==len(prose_rows) else
                                prose_overlay(prose_source,unchanged,{r['id']:r['translated'] for r in unchanged},renderer=config.get('renderer','pil')))
                            visible_overlay.save(path,compress_level=1)
                            state['overlay']=path.name
                            if previous_overlay is not None:
                                previous_overlay.unlink(missing_ok=True)
                            previous_overlay=path
                        visible_ids=ids
                needs_work=(processed_digest!=digest if config.get('prose') and valid else submitted!=gate.token)
                needs_work = needs_work or (config.get('monitor_mode') and retry_unstable)
                speculative=bool(config.get('monitor_mode') and config.get('speculative_initial_ocr')
                                 and not config.get('readable_ocr') and submitted==-1)
                if config.get('monitor_mode'):
                    if future is not None or not needs_work:ocr_gate.reset()
                    settled=ocr_gate.ready(digest,now) if future is None and needs_work else False
                    stable = future is None and needs_work and (settled or speculative)
                else:
                    stable = pixel_gate.ready(now)
                if valid and (gate.ready(now) or speculative) and stable and future is None and needs_work and now >= next_request:
                    submitted = gate.token
                    submitted_calls=calls
                    processed_digest=digest
                    future = pool.submit(process, pixels, submitted, target,
                                         monitor.get('scale',1) if config.get('monitor_mode') else 1,
                                         app_context if config.get('monitor_mode') else None,
                                         dict(capture_seconds=capture_finished-capture_started,
                                              capture_finished_monotonic=capture_finished,
                                              settle_elapsed_seconds=max(0,now-ocr_gate.started))
                                         if config.get('monitor_mode') else None,
                                         window_bounds if config.get('monitor_mode') else None)
                    next_request = now + 3
                if calls >= 30:
                    state['status'] = '連続翻訳 ON · 送信上限30回 · OFF→ONで再開'
            except Exception:
                gate.observe(None, now)
                pixel_gate.observe(None, now)
                state.update(lines=[], overlay='', status='連続翻訳 ON · 取得停止')
                prose_source=None
                visible_ids=None
            state['busy'] = future is not None
            write_state(directory, state)
            wait_for_update(future)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def toggle(demo=False, timeout=0, prose=False, readable_ocr=False,ocr_profile=DEFAULT_UI_PROFILE,word_regions=False,renderer='pil',merge_overlaps=False,trim_word_margins=False,context_separators=False,expand_display_space=False,follow_active=False,monitor_mode=False,translation_priority=False):
    import fcntl
    close = subprocess.run(['qs', 'ipc', '-p', str(UI), 'call', 'lens', 'close'], capture_output=True, timeout=3)
    if close.returncode == 0:
        return
    if subprocess.run(['qs', 'ipc', '-p', str(ROOT), 'call', 'lens', 'close'], capture_output=True, timeout=3).returncode == 0:
        return
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    with (runtime/'screen-lens-live.lock').open('a') as lock:
        os.chmod(lock.name, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        window = active()
        if not window.get('stableId'):
            raise RuntimeError('Focus a normal application window first')
        monitor = next(m for m in json.loads(subprocess.check_output(['hyprctl','monitors','-j'])) if m['id'] == window['monitor'])
        with tempfile.TemporaryDirectory(prefix='screen-lens-live-', dir=runtime) as temp:
            directory = Path(temp)
            config=dict(target=window['stableId'], monitor=monitor['name'], demo=demo,prose=prose,readable_ocr=readable_ocr,ocr_profile=ocr_profile,word_regions=word_regions,renderer=renderer,merge_overlaps=merge_overlaps,trim_word_margins=trim_word_margins,context_separators=context_separators,expand_display_space=expand_display_space,follow_active=follow_active,monitor_mode=monitor_mode)
            if monitor_mode:
                config.update(ocr_threads=8,detector_limit='max',translation_batches=4,context_image_format='jpeg',context_max_side=1280,speculative_initial_ocr=True,ocr_cuda=True,resident_ocr=True)
                if translation_priority:config['translation_priority']=True
            if supports_resident_ocr(config):
                try:
                    from ocr_client import Client
                    startup_client=Client()
                    def prepare():
                        try:startup_client.ensure_running()
                        except Exception:pass  # Worker retains normal fallback handling.
                    # No screenshot or network request; the service owns its idle exit.
                    threading.Thread(target=prepare,daemon=True).start()
                except Exception:pass
            (directory/'config.json').write_text(json.dumps(config))
            write_state(directory, dict(lines=[], busy=True, monitor=monitor['name'], status='連続翻訳 ON · 起動中'))
            subprocess.run(['qs', '-p', str(UI)], check=True, env=dict(os.environ,
                SCREEN_LENS_DIR=temp, SCREEN_LENS_LIVE_TIMEOUT=str(timeout),
                SCREEN_LENS_LIVE_PYTHON=str(ROOT/'.venv/bin/python'), SCREEN_LENS_LIVE_SCRIPT=str(ROOT/'live.py')))


if __name__ == '__main__':
    import sys
    worker(Path(sys.argv[1]))
