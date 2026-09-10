import tempfile
import os
import time
import unittest
from pathlib import Path
from PIL import Image


class SnapshotCacheTests(unittest.TestCase):
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
            archive = root / 'screen-lens-snapshot-cache' / 'last.zip'
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
