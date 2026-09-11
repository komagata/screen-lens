"""TranslateGemma text/image interface probe on public saved fixtures; no cloud."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from benchmark_runtime import server
from local_translation import configuration, request


def text_body(text):
    return dict(messages=[dict(role='user', content=text, source_lang_code='en', target_lang_code='ja')],
                chat_template_kwargs=dict(source_lang_code='en', target_lang_code='ja'),
                temperature=0, seed=42, max_tokens=2048, cache_prompt=False)


def native_prompt(text=None):
    # Same instructions as the checksum-verified model's embedded template;
    # Gemma role markers are supplied by llama.cpp's built-in gemma template.
    prefix = ('You are a professional English (en) to Japanese (ja) translator. Your goal is to accurately convey the meaning and '
              'nuances of the original English text while adhering to Japanese grammar, '
              'vocabulary, and cultural sensitivities.\n')
    if text is not None:
        return prefix + ('Produce only the Japanese translation, without any additional explanations or '
                         'commentary. Please translate the following English text into Japanese:\n\n\n') + text
    return prefix + ('Please translate the English text in the provided image into Japanese. '
                     'Produce only the Japanese translation, without any additional explanations, '
                     'alternatives or commentary. Focus only on the text, do not output where the text is located, '
                     'surrounding objects or any other explanation about the picture. Ignore symbols, pictogram, and '
                     'arrows!\n\n\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-directory', type=Path, required=True)
    p.add_argument('--fixtures', type=Path, required=True)
    p.add_argument('--real-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--compatible-template', action='store_true')
    args = p.parse_args()
    os.umask(0o077)
    args.output.mkdir(parents=True, exist_ok=False)
    config = configuration()
    config['image_tokens'] = 256
    config['compatible_gemma'] = args.compatible_template
    for key, filename, expected in [
        ('model', 'model.gguf', '81200d03e843d2ec1ece6eeafe7d13cb6e5211e1fcd336ade55790b683a08330'),
        ('projector', 'mmproj.gguf', '482f68be8823dfdfb3561c22cdd1c0f617d0d5e6efe9c323cc6428a4331dba01')]:
        path = args.model_directory/filename
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected: raise ValueError('Model checksum mismatch')
        config[key] = str(path.resolve())
    report = dict(scope='Interface and quality probe. No OCR/display integration or desktop timing.', runs=[])
    report['compatible_template'] = args.compatible_template
    def save():
        (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    cases = [('text-herbs', text_body('Bring 3 herbs to the healer. Do not sell them.')),
             ('text-warning', text_body('Do not unplug the drive until the backup finishes.')),
             ('text-json', text_body(json.dumps({'a': 'Save changes', 'b': 'Bring 3 herbs to the healer. Do not sell them.'})))]
    for name in ('shop', 'file', 'editor', 'real'):
        path = (Path(json.loads(args.real_report.read_text())['source']) if name == 'real'
                else args.fixtures/(name+'.png'))
        data = text_body('')
        data['messages'][0]['content'] = [dict(type='image_url', source_lang_code='en', target_lang_code='ja',
            image_url=dict(url='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()))]
        cases.append(('image-'+name, data))
    if args.compatible_template:
        for name, body in cases:
            content = body['messages'][0]['content']
            body['messages'][0]['content'] = (native_prompt(content) if isinstance(content, str) else
                [dict(type='text', text=native_prompt()), *content])
    start = time.monotonic()
    try:
        with server(config, args.output/'server.log', 'auto', 1024) as sock:
            report['startup_seconds'] = time.monotonic()-start
            props = request(sock, 'props')
            (args.output/'props.json').write_text(json.dumps(props, ensure_ascii=False, indent=2))
            for name, body in cases:
                begin = time.monotonic()
                row = dict(case=name)
                try:
                    # Persist the actual rendered template, when supported, before inference.
                    row['template'] = request(sock, 'apply-template', body)
                except (subprocess.SubprocessError, ValueError) as error:
                    row['template_error'] = str(error)
                try:
                    row['response'] = request(sock, 'v1/chat/completions', body)
                except (subprocess.SubprocessError, ValueError) as error:
                    row.update(error=type(error).__name__, detail=getattr(error, 'stderr', '') or str(error))
                row['seconds'] = time.monotonic()-begin
                report['runs'].append(row); save()
                print(name, round(row['seconds'], 2), row.get('error', 'response'), flush=True)
    except (RuntimeError, TimeoutError, subprocess.SubprocessError) as error:
        report.update(error=type(error).__name__, detail=str(error))
    report['total_seconds'] = time.monotonic()-start
    save()


if __name__ == '__main__': main()
