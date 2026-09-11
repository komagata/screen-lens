"""Small, shared translation preferences; contains no credentials."""
import json
import os
from pathlib import Path
import tempfile
import stat
import re

LANGUAGES = {'ja': 'Japanese', 'en': 'English', 'zh-CN': 'Simplified Chinese',
             'es': 'Spanish', 'fr': 'French'}


def default_target():
    value = next((os.environ[key] for key in ('LC_ALL', 'LC_MESSAGES', 'LANG')
                  if os.environ.get(key)), 'C')
    parts = value.split('.')[0].split('@')[0].lower().replace('_', '-').split('-')
    if parts[0] in ('ja', 'en', 'es', 'fr'):
        return parts[0]
    if parts[0] == 'zh' and not any(p in parts for p in ('hant', 'tw', 'hk', 'mo')):
        return 'zh-CN'
    return 'en'


def validate_target(value):
    if not isinstance(value, str) or value not in LANGUAGES:
        raise ValueError('Unsupported translation language')
    return value


def settings_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'screen-lens/settings.json'


def read_json(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > limit:
            raise ValueError('Unsafe or oversized settings file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit: raise ValueError('Settings grew beyond the limit')
        return json.loads(data)
    finally:
        os.close(fd)


def load(path=None):
    if path is None:
        shell = settings_path().parent.parent / 'omarchy/shell.json'
        try:
            config = read_json(shell, 1048576)
            for entries in config['bar']['layout'].values():
                for entry in entries:
                    if isinstance(entry, dict) and entry.get('id') == 'komagata.screen-lens':
                        return {'source': validate_target(entry.get('sourceLanguage', entry.get('source', 'en'))),
                                'target': validate_target(entry.get('target') or default_target())}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
    path = Path(path) if path is not None else settings_path()
    try:
        value = read_json(path, 4096)
        return {'source': validate_target(value.get('source', 'en')), 'target': validate_target(value['target'])}
    except (OSError, ValueError, KeyError, TypeError):
        return {'source': 'en', 'target': default_target()}


def save(value, path=None):
    data = {'source': validate_target(value.get('source', 'en')), 'target': validate_target(value['target'])}
    path = Path(path) if path is not None else settings_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream)
        temporary.replace(path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    return data


def target():
    if 'SCREEN_LENS_TARGET' in os.environ:
        return validate_target(os.environ['SCREEN_LENS_TARGET'])
    return load()['target']


def provider():
    if 'SCREEN_LENS_PROVIDER' in os.environ:
        value = os.environ['SCREEN_LENS_PROVIDER']
        if value not in ('local', 'openai', 'ollama'): raise ValueError('Unsupported provider')
        return value
    try:
        config = read_json(settings_path().parent.parent / 'omarchy/shell.json', 1048576)
        for entries in config['bar']['layout'].values():
            for entry in entries:
                if isinstance(entry, dict) and entry.get('id') == 'komagata.screen-lens':
                    value = entry.get('translationEngine', 'openai')
                    if value not in ('local', 'openai'): raise ValueError('Unsupported provider')
                    return value
    except (OSError, KeyError, TypeError, AttributeError):
        pass
    return 'openai'


def source():
    if 'SCREEN_LENS_SOURCE' in os.environ:
        return validate_target(os.environ['SCREEN_LENS_SOURCE'])
    return load()['source']


def source_candidate(text):
    """Script eligibility only; the translator must distinguish same-script languages."""
    code = source()
    if code in ('ja', 'zh-CN'):
        pattern = r'[\u3040-\u30ff\u3400-\u9fff]' if code == 'ja' else r'[\u3400-\u9fff]'
        return bool(re.search(pattern, text))
    # A mixed-script line can still contain source-language UI or prose.
    # This is candidate selection, not language identification; the translator
    # is already instructed to preserve other languages and identifiers.
    return bool(re.search(r'[A-Za-zÀ-ÖØ-öø-ÿ]{2}', text))


def font(code):
    validate_target(code)
    return {'ja': 'Noto Sans CJK JP', 'zh-CN': 'Noto Sans CJK SC'}.get(code, 'Noto Sans')
