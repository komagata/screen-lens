"""Owned, logged model runtime for fit/offload experiments; not an app backend."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from local_translation import request


def command(config, sock, gpu_layers='auto', margin=1024):
    if gpu_layers not in ('auto', '99', '0') or margin < 0: raise ValueError('Invalid fit policy')
    argv = [config['server'], '-m', config['model'], '--host', str(sock), '--no-webui', '--offline',
            '-t', '4', '-tb', '4', '-np', '1', '-c', '8192', '--device', 'none' if gpu_layers == '0' else 'Vulkan0',
            '-ngl', gpu_layers, '--fit', 'on', '--fit-target', str(margin), '-lv', '4', '--reasoning', 'off']
    if config.get('projector'):
        tokens = str(config.get('image_tokens', 1024))
        argv += ['--mmproj', config['projector'], '--image-min-tokens', tokens, '--image-max-tokens', tokens]
    if gpu_layers == '0': argv += ['--no-mmproj-offload', '--no-op-offload']
    if config.get('compatible_gemma'): argv += ['--no-jinja', '--chat-template', 'gemma']
    return argv


@contextmanager
def server(config, logfile, gpu_layers='auto', margin=1024):
    with tempfile.TemporaryDirectory(prefix='sl-fit-', dir=os.environ.get('XDG_RUNTIME_DIR')) as tmp:
        sock = Path(tmp)/'model.sock'
        argv = command(config, sock, gpu_layers, margin)
        env = {k: v for k, v in os.environ.items() if k not in ('OPENAI_API_KEY', 'OPENAI_API_TOKEN')}
        with open(logfile, 'w') as log:
            process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).with_name('local_translation.py')),
                                        '--serve', str(os.getpid()), *argv], env=env, stdout=log, stderr=log)
            try:
                started = time.monotonic()
                while True:
                    if process.poll() is not None: raise RuntimeError('Model startup failed: '+str(logfile))
                    try:
                        if sock.exists() and request(sock, 'health', timeout=1).get('status') == 'ok': break
                    except (subprocess.SubprocessError, ValueError): pass
                    if time.monotonic()-started > 45: raise TimeoutError('Model startup')
                    time.sleep(.1)
                yield sock
            finally:
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
