"""CPU-only Hy-MT2 benchmark on authored public samples; no desktop or API key."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

MODEL_SHA256 = 'dc5f44fcf1fa496ee7ad725982c0c8c553a4de00259b53af84c4b89fb0c06699'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.model.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != MODEL_SHA256:
            raise ValueError('Model checksum mismatch')
    os.umask(0o077)
    args.output.mkdir(parents=True, exist_ok=False)
    from translation_settings import LANGUAGES
    samples = ['Save changes', 'Do not delete this file. Retry in 30 seconds.',
               'The application works offline. Your messages are not sent to a server.']
    with tempfile.TemporaryDirectory(prefix='sl-hymt2-') as tmp, (args.output/'server.log').open('w') as log:
        sock = str(Path(tmp) / 'server.sock')
        before = time.monotonic()
        process = subprocess.Popen([str(args.server), '-m', str(args.model), '--host', sock,
            '--no-webui', '-np', '1', '-c', '2048', '-ngl', '0', '-t', '4', '-tb', '4', '-lv', '3'],
            stdout=log, stderr=log)
        def request(route, body=None):
            command = ['/usr/bin/curl', '-q', '-fsS', '--max-time', '45', '--unix-socket', sock,
                       'http://localhost/' + route]
            if body is not None: command += ['-H', 'Content-Type: application/json', '--data-binary', '@-']
            response = subprocess.run(command, input=json.dumps(body) if body else None,
                                      capture_output=True, text=True, timeout=50, check=True)
            return json.loads(response.stdout)
        try:
            while True:
                if process.poll() is not None: raise RuntimeError('Local server exited; see server.log')
                try:
                    if Path(sock).exists(): request('health'); break
                except subprocess.CalledProcessError: pass
                if time.monotonic()-before > 90: raise TimeoutError('Server startup')
                time.sleep(.1)
            report = dict(model='Hy-MT2-1.8B-Q4_K_M', threads=4, gpu_layers=0,
                          startup_seconds=time.monotonic()-before,
                          scope='Translation only, public samples; excludes OCR, image context and display', results=[])
            print(json.dumps({k:v for k,v in report.items() if k!='results'}), flush=True)
            for code, language in LANGUAGES.items():
                for source in samples:
                    prompt = ('<｜hy_User｜>Translate the following text into ' + language +
                              '. Note that you should only output the translated result without any additional explanation:\n' +
                              source + '<｜hy_Assistant｜>')
                    started = time.monotonic()
                    data = request('completion', dict(prompt=prompt, n_predict=192, temperature=0,
                                                     cache_prompt=False, seed=42))
                    row = dict(target=code, source=source, translation=data['content'],
                               seconds=time.monotonic()-started, timings=data.get('timings'),
                               truncated=data.get('truncated'), stop_type=data.get('stop_type'))
                    report['results'].append(row)
                    (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
                    print(json.dumps(row, ensure_ascii=False), flush=True)
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()


if __name__ == '__main__': main()
