"""Local-only authored source-language smoke test; never captures the desktop."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont
from ocr_backends import make_rapid, recognize_rapid
from paragraphs import paragraphs


def main():
    samples = {'en': 'Save changes', 'ja': '変更を保存する', 'zh-CN': '保存更改',
               'fr': 'Enregistrer les modifications', 'es': 'Guardar los cambios'}
    engine = make_rapid('v5-v6')
    font = ImageFont.truetype('/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc', 32)
    results = []
    with tempfile.TemporaryDirectory(prefix='screen-lens-source-ocr-') as tmp:
        for source, text in samples.items():
            image = Image.new('RGB', (900, 160), '#202020')
            ImageDraw.Draw(image).text((30, 40), text, font=font, fill='white')
            path = Path(tmp)/f'{source}.png'; image.save(path)
            with patch.dict(os.environ, SCREEN_LENS_SOURCE=source):
                rows = recognize_rapid(path, engine)
                groups = paragraphs(rows)
            results.append(dict(source=source, expected=text,
                readings=[r['text'] for r in rows], eligible=[r['text'] for r in groups]))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    assert all(r['eligible'] for r in results), 'A source language has no eligible OCR text'


if __name__ == '__main__': main()
