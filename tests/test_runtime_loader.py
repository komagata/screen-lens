import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RuntimeLoaderTests(unittest.TestCase):
    def test_bundle_profile_cannot_trigger_extra_model_downloads(self):
        import runtime_loader
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(callable(getattr(runtime_loader, 'ocr_profile', None)))
            self.assertEqual(runtime_loader.ocr_profile(root, None), 'v5')
            (root / 'runtime-manifest.json').write_text('{"profile": "v5-v6"}')
            self.assertEqual(runtime_loader.ocr_profile(root, None), 'v5-v6')
            self.assertEqual(runtime_loader.ocr_profile(root, 'v5-v6'), 'v5-v6')
            with self.assertRaisesRegex(ValueError, 'only supports'):
                runtime_loader.ocr_profile(root, 'v6')

    def run_loader(self, root):
        code = ('import json,os,sys; from runtime_loader import activate; '
                'enabled=activate(sys.argv[1]); '
                'print(json.dumps([enabled,sys.path[0],os.environ.get("PYTHONPATH"),'
                'sys.dont_write_bytecode,os.environ.get("PYTHONDONTWRITEBYTECODE")]))')
        return subprocess.run([sys.executable, '-c', code, str(root)],
                              capture_output=True, text=True)

    def test_source_checkout_does_not_activate_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_loader(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)[0])

    def test_bundle_activates_for_parent_and_child_without_bytecode_growth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'runtime').mkdir()
            (root / 'runtime-manifest.json').write_text(
                json.dumps({'python': list(sys.version_info[:2])}))
            result = self.run_loader(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout),
                             [True, str(root / 'runtime'), str(root / 'runtime'), True, '1'])

    def test_incompatible_python_fails_instead_of_using_system_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'runtime').mkdir()
            (root / 'runtime-manifest.json').write_text('{"python": [0, 0]}')
            result = self.run_loader(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Python version', result.stderr)


if __name__ == '__main__':
    unittest.main()
