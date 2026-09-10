"""One exact-pixel LT result, private to the login session. No fuzzy matching."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parent
MAX_AGE = 15 * 60


def fingerprint(source, fast):
    digest = hashlib.sha256(b'screen-lens-exact-v1')
    digest.update(str(bool(fast)).encode())
    # Invalidate after any pipeline, prompt, renderer or dependency declaration change.
    for path in sorted(ROOT.glob('*.py')) + [ROOT / 'requirements-ocr.txt']:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    with Image.open(source) as image:
        pixels = image.convert('RGBA')
        digest.update(str(pixels.size).encode())
        digest.update(pixels.tobytes())
    return digest.hexdigest()


def prepare(directory, fast, compute, *, runtime=None):
    cache = None
    key = None
    try:
        base = runtime or os.environ.get('XDG_RUNTIME_DIR')
        if base:
            folder = Path(base) / 'screen-lens-snapshot-cache'
            folder.mkdir(mode=0o700, exist_ok=True)
            info = folder.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise OSError('Unsafe cache directory')
            cache = folder / 'last.zip'
            key = fingerprint(directory / 'screen.png', fast)
            if cache.exists():
                info = cache.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise OSError('Unsafe cache file')
                if not 0 <= time.time() - info.st_mtime <= MAX_AGE:
                    cache.unlink()
                else:
                    with zipfile.ZipFile(cache) as saved:
                        meta = json.loads(saved.read('metadata.json'))
                        if meta['key'] == key:
                            content = saved.read('translated.png')
                            with Image.open(io.BytesIO(content)) as image:
                                image.verify()
                            result = meta['result']
                            if result.get('translatedScreen') is True:
                                (directory / 'translated.png').write_bytes(content)
                                return dict(result, cache_hit=True)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        # A broken or inaccessible cache must never prevent translation.
        cache = None
    result = compute(directory, fast=fast)
    if cache is not None and result.get('translatedScreen') is True and directory.is_dir():
        temporary = None
        try:
            content = (directory / 'translated.png').read_bytes()
            with tempfile.NamedTemporaryFile(dir=cache.parent, delete=False) as stream:
                temporary = Path(stream.name)  # mode 0600
                with zipfile.ZipFile(stream, 'w') as saved:
                    saved.writestr('metadata.json', json.dumps(dict(key=key, result=result)))
                    saved.writestr('translated.png', content)
            if directory.is_dir():
                temporary.replace(cache)
        except OSError:
            pass
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return dict(result, cache_hit=False)
