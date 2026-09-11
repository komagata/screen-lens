"""Activate the private, ABI-specific runtime in a packaged installation."""
import json
import os
from pathlib import Path
import sys


def ocr_profile(root, requested):
    manifest = Path(root) / 'runtime-manifest.json'
    if not manifest.exists():
        return requested or 'v5'
    supported = json.loads(manifest.read_text())['profile']
    if requested is not None and requested != supported:
        raise ValueError(f'This compact runtime only supports OCR profile {supported}')
    return supported


def activate(root):
    root = Path(root).resolve()
    manifest = root / 'runtime-manifest.json'
    if not manifest.exists():
        return False
    metadata = json.loads(manifest.read_text())
    if metadata['python'] != list(sys.version_info[:2]):
        raise RuntimeError('Python version does not match this Screen Lens bundle; rebuild the runtime')
    runtime = root / 'runtime'
    if not runtime.is_dir():
        raise RuntimeError('Screen Lens private runtime is missing; reinstall the bundle')
    sys.path.insert(0, str(runtime))
    # Worker processes must use the same private libraries, not the old venv.
    os.environ['PYTHONPATH'] = str(runtime)
    sys.dont_write_bytecode = True
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    return True
