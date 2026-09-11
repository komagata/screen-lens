"""A bounded exact-pixel LT cache, private to the login session."""
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

ROOT = Path(__file__).resolve().parent.parent
MAX_AGE = 15 * 60
MAX_ENTRIES = 8


def fingerprints(source, fast):
    from translation_settings import target, source as source_language
    settings = hashlib.sha256(b'screen-lens-exact-v2')
    settings.update(str(bool(fast)).encode())
    settings.update(target().encode())
    settings.update(b'|source:' + source_language().encode())
    provider = os.environ.get('SCREEN_LENS_PROVIDER', 'openai')
    settings.update(b'|provider:' + provider.encode())
    if provider == 'local':
        from local_translation import configuration
        settings.update(json.dumps(configuration(), sort_keys=True).encode())
    sources = sorted(p for p in (ROOT / 'src').glob('*.py') if not p.name.startswith('test_'))
    sources += sorted(ROOT.glob('requirements*.txt'))
    sources += list(ROOT.glob('runtime-manifest.json'))
    for path in sources:
        settings.update(path.name.encode())
        settings.update(path.read_bytes())
    with Image.open(source) as image:
        pixels = image.convert('RGBA')
        digest = hashlib.sha256(str(pixels.size).encode())
        digest.update(pixels.tobytes())
    config, screen = settings.hexdigest(), digest.hexdigest()
    return hashlib.sha256((config + screen).encode()).hexdigest(), config, screen


def fingerprint(source, fast):
    return fingerprints(source, fast)[0]


def private(path, directory=False):
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise OSError('Unsafe cache path')
    return info


def record(folder, hit, reason):
    # No screenshot content, recognized text, keys or credentials in diagnostics.
    try:
        with open(folder / 'last-access.json', 'w',
                  opener=lambda path, flags: os.open(path, flags | os.O_NOFOLLOW, 0o600)) as stream:
            json.dump(dict(cache_hit=hit, reason=reason, time=time.time()), stream)
    except OSError:
        pass


def prepare(directory, fast, compute, *, runtime=None):
    folder = cache = None
    key = config = screen = None
    reason = 'cache unavailable'
    try:
        base = runtime or os.environ.get('XDG_RUNTIME_DIR')
        if base:
            folder = Path(base) / 'screen-lens-snapshot-cache'
            folder.mkdir(mode=0o700, parents=True, exist_ok=True)
            private(folder, directory=True)
            key, config, screen = fingerprints(directory / 'screen.png', fast)
            cache = folder / (key + '.zip')
            entries = []
            expired = False
            for path in folder.glob('*.zip'):
                info = private(path)
                if not 0 <= time.time() - info.st_mtime <= MAX_AGE:
                    expired = True
                    path.unlink()
                else:
                    entries.append(path)
            reason = 'pixels changed' if entries else ('expired' if expired else 'empty')
            if cache.exists():
                try:
                    with zipfile.ZipFile(cache) as saved:
                        meta = json.loads(saved.read('metadata.json'))
                        if meta['key'] != key or meta['result'].get('translatedScreen') is not True:
                            raise ValueError('Invalid cache metadata')
                        content = saved.read('translated.png')
                        with Image.open(io.BytesIO(content)) as image:
                            image.verify()
                        (directory / 'translated.png').write_bytes(content)
                        record(folder, True, 'exact match')
                        result = dict(meta['result'], cache_hit=True, cache_reason='exact match')
                        result['status'] = 'キャッシュから表示 · ' + result.get('status', '')
                        return result
                except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                    reason = 'corrupt entry'
                    cache.unlink(missing_ok=True)
            elif entries:
                # Distinguish changed code/settings from changed screen pixels.
                for path in entries:
                    try:
                        with zipfile.ZipFile(path) as saved:
                            meta = json.loads(saved.read('metadata.json'))
                        if meta.get('screen') == screen and meta.get('config') != config:
                            reason = 'code or settings changed'
                            break
                    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                        continue
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        folder = cache = None
    if folder is not None:
        record(folder, False, reason)
    result = compute(directory, fast=fast)
    if cache is not None and result.get('translatedScreen') is True and directory.is_dir():
        temporary = None
        try:
            content = (directory / 'translated.png').read_bytes()
            with tempfile.NamedTemporaryFile(dir=cache.parent, delete=False) as stream:
                temporary = Path(stream.name)
                with zipfile.ZipFile(stream, 'w') as saved:
                    saved.writestr('metadata.json', json.dumps(dict(key=key, config=config, screen=screen, result=result)))
                    saved.writestr('translated.png', content)
            if directory.is_dir():
                temporary.replace(cache)
                entries = sorted(folder.glob('*.zip'), key=lambda path: path.stat().st_mtime, reverse=True)
                for path in entries[MAX_ENTRIES:]:
                    path.unlink()
        except OSError:
            pass
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return dict(result, cache_hit=False, cache_reason=reason)
