"""Reproducible synthetic screen benchmark; --vision sends these synthetic crops only."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def distance(a, b):
    previous = list(range(len(b)+1))
    for i, char in enumerate(a, 1):
        current = [i]
        for j, other in enumerate(b, 1):
            current.append(min(current[-1]+1, previous[j]+1, previous[j-1]+(char != other)))
        previous = current
    return previous[-1]


def score(truth, found):
    pairs = []
    for i, a in enumerate(truth):
        for j, b in enumerate(found):
            w = max(0, min(a['x']+a['width'], b['x']+b['width'])-max(a['x'], b['x']))
            h = max(0, min(a['y']+a['height'], b['y']+b['height'])-max(a['y'], b['y']))
            union = a['width']*a['height']+b['width']*b['height']-w*h
            if union and w*h/union >= .25:
                pairs.append((w*h/union, i, j))
    matched, used = {}, set()
    for _, i, j in sorted(pairs, reverse=True):
        if i not in matched and j not in used:
            matched[i] = found[j]['text']
            used.add(j)
    errors = sum(distance(a['text'], matched.get(i, '')) for i, a in enumerate(truth))
    return dict(total=len(truth), detected=len(matched),
                exact=sum(a['text'] == matched.get(i) for i, a in enumerate(truth)),
                extra=len(found)-len(used), cer=round(errors/max(1, sum(len(a['text']) for a in truth)), 4))


def fixtures(out):
    from PIL import Image, ImageDraw, ImageFont
    font_path = '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
    texts = ['Settings', 'Save changes', 'Cancel', 'Network connection',
             'Retry in 30 seconds', 'Permission denied', 'Open pull request',
             'Please check your configuration.', 'git status --short',
             '/home/user/my-project/config.json', 'Error: connection timed out',
             '日本語の設定']
    result = []
    for name, size, bg, fg in [('dark', 22, '#171b24', '#eef1f7'),
                               ('light', 22, '#ffffff', '#222222'),
                               ('small', 12, '#20232b', '#b6bbc7')]:
        im = Image.new('RGB', (1400, 900), bg)
        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype(font_path, size)
        truth = []
        for index, text in enumerate(texts):
            x, y = 45 + (index//6)*670, 55 + (index%6)*115
            if text in ('Save changes', 'Cancel'):
                draw.rounded_rectangle((x-12, y-8, x+180, y+size+18), radius=6, fill='#426bb0')
            draw.text((x, y), text, font=font, fill=fg)
            l, t, r, b = draw.textbbox((x, y), text, font=font)
            truth.append(dict(text=text, x=l, y=t, width=r-l, height=b-t))
        path = out / (name+'.png')
        im.save(path)
        result.append((path, truth))
    return result


def main():
    from lens import parse_tsv, recognize_screen
    from ocr_backends import make_rapid, recognize_rapid, verify_with_luna
    parser = argparse.ArgumentParser()
    parser.add_argument('--vision', action='store_true')
    args = parser.parse_args()
    out = Path(__file__).parent / 'benchmark-results'
    out.mkdir(exist_ok=True)
    started = time.monotonic()
    engine = make_rapid()
    report = dict(rapid_init_seconds=round(time.monotonic()-started, 3), screens=[])
    for path, truth in fixtures(out):
        screen = dict(image=path.name, truth=truth, methods={})
        methods = {
            'tesseract_single': lambda: parse_tsv(subprocess.run(
                ['tesseract', str(path), 'stdout', '-l', 'eng', '--psm', '11', 'tsv'],
                capture_output=True, text=True, check=True, timeout=30).stdout),
            'tesseract_multiscale': lambda: recognize_screen(path),
            'rapidocr_v5': lambda: recognize_rapid(path, engine),
        }
        for name, fn in methods.items():
            start = time.monotonic()
            rows = fn()
            screen['methods'][name] = dict(seconds=round(time.monotonic()-start, 3),
                all=score(truth, rows), english=score(truth[:-1], rows), rows=rows)
        if args.vision:
            rows = screen['methods']['rapidocr_v5']['rows']
            start = time.monotonic()
            verified = verify_with_luna(path, rows)
            corrected = [dict(r, text=verified[r['id']]['source'], translated=verified[r['id']]['translated'])
                         for r in rows if verified[r['id']]['source']]
            screen['methods']['rapidocr_luna'] = dict(
                seconds=round(time.monotonic()-start+screen['methods']['rapidocr_v5']['seconds'], 3),
                all=score(truth, corrected), english=score(truth[:-1], corrected), rows=corrected)
        report['screens'].append(screen)
        (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(path.name, {k: {f: v[f] for f in ('seconds', 'all', 'english')} for k,v in screen['methods'].items()}, flush=True)


if __name__ == '__main__':
    main()
