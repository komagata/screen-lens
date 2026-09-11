"""Local synthetic OCR comparison for packaging changes; no desktop or network API."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from PIL import Image, ImageDraw, ImageFont
from ocr_backends import make_rapid, recognize_rapid, DEFAULT_UI_PROFILE
from snapshot import render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = time.monotonic()
    engine = make_rapid(DEFAULT_UI_PROFILE)
    report = {'init_seconds': time.monotonic() - started, 'cases': []}
    texts = ['Settings', 'Save changes', 'Open', 'Do not delete the backup.',
             'https://example.com/page?id=123', 'git status --short',
             'The meeting starts at 10:30. You do not need to install another application.',
             'Your changes have not been uploaded. Save a local copy before closing this window.',
             'Connected / 接続済み', 'Permission denied']
    for name, size, dark in [('light', 26, False), ('dark', 22, True), ('small', 14, False)]:
        image = Image.new('RGB', (1500, 850), '#171b24' if dark else 'white')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc', size)
        for index, text in enumerate(texts):
            draw.text((40, 30 + index * 70), text, font=font, fill='white' if dark else 'black')
        path = args.output / (name + '.png')
        image.save(path)
        times = []
        for _ in range(3):
            before = time.monotonic()
            rows = recognize_rapid(path, engine)
            times.append(time.monotonic() - before)
        encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()
        translated, audit = render(image, rows, {r['id']: '設定の変更' for r in rows}, renderer='pango')
        translated.save(args.output / (name + '-rendered.png'))
        report['cases'].append(dict(name=name, rows=rows, sha256=hashlib.sha256(encoded).hexdigest(),
                                    seconds=times, median_seconds=statistics.median(times),
                                    rendered=sum(r['shown'] for r in audit)))
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({**report, 'cases': [{k:v for k,v in row.items() if k != 'rows'} for row in report['cases']]}, indent=2))


if __name__ == '__main__':
    main()
