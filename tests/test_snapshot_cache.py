import tempfile
import os
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from PIL import Image


class SnapshotCacheTests(unittest.TestCase):
    def test_native_runtime_manifest_change_invalidates_cache(self):
        import snapshot_cache
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'screen.png'
            Image.new('RGB', (8, 8)).save(source)
            manifest = root / 'runtime-manifest.json'
            manifest.write_text('{"build": "one"}')
            with patch.object(snapshot_cache, 'ROOT', root):
                old = snapshot_cache.fingerprint(source, False)
                manifest.write_text('{"build": "two"}')
                self.assertNotEqual(old, snapshot_cache.fingerprint(source, False))

    def test_slim_dependency_change_invalidates_cache(self):
        import snapshot_cache
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'screen.png'
            Image.new('RGB', (8, 8)).save(source)
            (root / 'requirements-ocr.txt').write_text('original')
            slim = root / 'requirements-slim.txt'
            slim.write_text('headless-version-1')
            with patch.object(snapshot_cache, 'ROOT', root):
                old = snapshot_cache.fingerprint(source, False)
                slim.write_text('headless-version-2')
                self.assertNotEqual(old, snapshot_cache.fingerprint(source, False))

    def test_exact_hit_and_setting_and_pixel_misses(self):
        import snapshot_cache
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = root / 'session'
            session.mkdir()
            Image.new('RGB', (32, 24), 'white').save(session / 'screen.png')
            calls = []
            def compute(directory, fast=False):
                calls.append(fast)
                Image.new('RGB', (32, 24), 'blue').save(directory / 'translated.png')
                return dict(translatedScreen=True, lines=[], status='Translated')
            def run(fast=False):
                return snapshot_cache.prepare(session, fast, compute, runtime=root)
            self.assertFalse(run()['cache_hit'])
            (session / 'translated.png').unlink()
            self.assertTrue(run()['cache_hit'])
            self.assertTrue((session / 'translated.png').exists())
            self.assertEqual(len(calls), 1)
            self.assertFalse(run(True)['cache_hit'])
            image = Image.open(session / 'screen.png').convert('RGB')
            image.putpixel((0, 0), (0, 0, 0))
            image.save(session / 'screen.png')
            self.assertFalse(run(True)['cache_hit'])
            self.assertEqual(len(calls), 3)
            archive = root / 'screen-lens-snapshot-cache' / (snapshot_cache.fingerprint(session / 'screen.png',True) + '.zip')
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
            self.assertEqual(archive.parent.stat().st_mode & 0o777, 0o700)
            stale = time.time() - snapshot_cache.MAX_AGE - 1
            os.utime(archive, (stale, stale))
            self.assertFalse(run(True)['cache_hit'])
            archive.write_bytes(b'broken zip')
            self.assertFalse(run(True)['cache_hit'])
            self.assertEqual(len(calls), 5)

    def test_failed_results_are_not_cached(self):
        import snapshot_cache
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new('RGB', (8, 8)).save(root / 'screen.png')
            calls = []
            def compute(directory, fast=False):
                calls.append(1)
                return dict(translatedScreen=False)
            for _ in range(2):
                self.assertFalse(snapshot_cache.prepare(root, False, compute, runtime=root)['cache_hit'])
            self.assertEqual(len(calls), 2)

    def test_returning_to_previous_screen_skips_translation(self):
        import snapshot_cache
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            calls=[]
            def compute(directory,fast=False):
                calls.append(1)
                Image.open(directory/'screen.png').save(directory/'translated.png')
                return dict(translatedScreen=True,status='Translated')
            def run(color):
                Image.new('RGB',(32,24),color).save(root/'screen.png')
                return snapshot_cache.prepare(root,True,compute,runtime=root)
            self.assertFalse(run('white')['cache_hit'])
            self.assertFalse(run('black')['cache_hit'])
            result=run('white')
            self.assertTrue(result['cache_hit'])
            self.assertIn('キャッシュ',result['status'])
            self.assertEqual(len(calls),2)
            summary=json.loads((root/'screen-lens-snapshot-cache/last-access.json').read_text())
            self.assertEqual(summary['reason'],'exact match')

    def test_capacity_and_corrupt_entry_recovery(self):
        import snapshot_cache
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def compute(directory,fast=False):
                Image.open(directory/'screen.png').save(directory/'translated.png')
                return dict(translatedScreen=True,status='Translated')
            def run():
                return snapshot_cache.prepare(root,True,compute,runtime=root)
            for n in range(snapshot_cache.MAX_ENTRIES+2):
                Image.new('RGB',(8,8),(n,0,0)).save(root/'screen.png')
                self.assertFalse(run()['cache_hit'])
            folder=root/'screen-lens-snapshot-cache'
            self.assertEqual(len(list(folder.glob('*.zip'))),snapshot_cache.MAX_ENTRIES)
            cache=folder/(snapshot_cache.fingerprint(root/'screen.png',True)+'.zip')
            cache.write_bytes(b'broken')
            self.assertEqual(run()['cache_reason'],'corrupt entry')
            self.assertTrue(run()['cache_hit'])
