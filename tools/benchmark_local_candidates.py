"""Same authored cases, image+OCR context, compact schema; no cloud or desktop capture."""
import argparse
import json
import os
from pathlib import Path
import time
from PIL import Image, ImageDraw, ImageFont
from local_translation import MODELS, payload, request, server, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--models', type=Path, nargs='+', required=True)
    parser.add_argument('--ids', nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', choices=['none', 'Vulkan0'], default='Vulkan0')
    args = parser.parse_args()
    if len(args.models) != len(args.ids): parser.error('Each model directory needs an id')
    os.umask(0o077); args.output.mkdir(parents=True, exist_ok=False)
    os.environ.update(SCREEN_LENS_SOURCE='en', SCREEN_LENS_TARGET='ja')
    cases = [
        ('shop', 'Bookshop status - closes at 8 PM', 'Open'),
        ('file', 'Choose a document from your computer', 'Open'),
        ('discount', 'Annual subscription - pay less each year', 'Save 20%'),
        ('editor', 'Unsaved document changes', 'Save'),
        ('mention', 'Message author', 'Reply to @Adobe'),
        ('warning', 'Backup status', 'Do not unplug the drive until the backup finishes.'),
        ('rpg', 'Quest objective: Village healer', 'Bring 3 herbs to the healer. Do not sell them.'),
        ('terminal', 'Command line instructions', 'Type `demo` and press Enter. Retry after 30 seconds.'),
    ]
    font = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Regular.ttf', 25)
    report = {'scope': 'Authored cases; inference only, not desktop latency or independent quality score', 'runs': []}
    def save():
        (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    manifests = []
    for name, context, text in cases:
        image = Image.new('RGB', (1000, 300), '#161b22'); draw = ImageDraw.Draw(image)
        draw.text((30, 30), context, fill='#aaaaaa', font=font)
        draw.rounded_rectangle((20, 100, 975, 220), 6, fill='#293548')
        draw.text((35, 140), text, fill='white', font=font)
        path = args.output/(name+'.png'); image.save(path)
        group = dict(id='t0', text=text, x=35, y=140, width=900, height=32)
        manifests.append(dict(name=name, image=str(path), groups=[group], lines=[dict(id='c0', text=context, x=30, y=30, width=900, height=32)]))
    for model_id, directory in zip(args.ids, args.models):
        import hashlib
        for key, filename in [('model','model.gguf'), ('projector','mmproj.gguf')]:
            with (directory/filename).open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest() != MODELS[model_id][key]:
                    raise ValueError('Checksum mismatch: ' + model_id)
        config = dict(server=str(args.server), model=str(directory/'model.gguf'), projector=str(directory/'mmproj.gguf'),
                      model_id=model_id, device=args.device)
        started = time.monotonic()
        with server(config) as sock:
            cold = time.monotonic()-started
            for repeat in range(2):
                for case in manifests:
                    started = time.monotonic()
                    data = request(sock, 'v1/chat/completions', payload(case, case['groups']))
                    elapsed = time.monotonic()-started
                    choice = data['choices'][0]
                    raw = choice['message']['content']
                    try:
                        output, rejected = validate(case['groups'], json.loads(raw))
                    except ValueError:
                        output, rejected = {}, ['t0']
                    row = dict(model=model_id, device=args.device, repeat=repeat, case=case['name'], source=case['groups'][0]['text'],
                               seconds=elapsed, startup_seconds=cold, raw=raw, output=output, rejected=rejected,
                               finish=choice['finish_reason'], timings=data.get('timings'))
                    report['runs'].append(row); save()
                    print(json.dumps(row, ensure_ascii=False), flush=True)
    save()


if __name__ == '__main__': main()
