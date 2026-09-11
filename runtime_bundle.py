"""Package the fixed CPU v5/v6 runtime without modifying its source environment."""
import argparse
from pathlib import Path
import shutil

SHARED_BASE = {'requests', 'urllib3', 'idna', 'charset_normalizer', 'certifi',
               'yaml', '_yaml', 'pyyaml', 'packaging'}


def copy_runtime(source, target, shared='none'):
    if shared not in ('none', 'base', 'numpy', 'extra'):
        raise ValueError('Unknown shared runtime profile')
    packages = set() if shared == 'none' else SHARED_BASE.copy()
    if shared == 'extra':
        packages.update({'numpy', 'cv2', 'opencv_python', 'opencv_python_headless'})
    elif shared == 'numpy':
        packages.add('numpy')
    source, target = Path(source).resolve(), Path(target).resolve()
    if target == source or source in target.parents:
        raise ValueError('Destination must be outside the source runtime')

    def excluded(directory, names):
        relative = Path(directory).relative_to(source)
        skip = {'tests', '__pycache__'}.intersection(names)
        if relative == Path('.'):
            for name in names:
                if (name in packages or
                    any(name.lower().startswith(p + '-') and name.endswith('.dist-info') for p in packages) or
                    ('cv2' in packages and name.startswith('cv2.') and name.endswith('.so'))):
                    skip.add(name)
        if relative == Path('onnxruntime'):
            # This bundle runs fixed OCR models; it does not develop/convert models.
            skip.update({'transformers', 'quantization', 'tools'}.intersection(names))
        if relative == Path('rapidocr/models'):
            skip.update({'PP-OCRv6_det_small.onnx'}.intersection(names))
        if relative == Path('onnxruntime/capi'):
            skip.update({'libonnxruntime.so.1.29.0'}.intersection(names))
        return skip

    shutil.copytree(source, target, ignore=excluded)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('--shared', choices=['none', 'base', 'numpy', 'extra'], default='none')
    args = parser.parse_args()
    copy_runtime(args.source, args.target, args.shared)
