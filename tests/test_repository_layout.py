from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayoutTests(unittest.TestCase):
    def test_python_files_have_a_home(self):
        self.assertEqual(list(ROOT.glob('*.py')), [])
        for path in ('src/lens.py', 'tools/benchmark_hybrid.py', 'tests/test_lens.py'):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_launcher_targets_source_directory(self):
        self.assertIn('/src/lens.py', (ROOT / 'screen-lens').read_text())

    def test_qml_helpers_exist(self):
        for qml, helper in (
            ('shell.qml', 'src/lens.py'),
            ('CredentialPanel.qml', 'src/credential_store.py'),
            ('panel/LanguagePairWidget.qml', '../src/plugin_launch.py'),
        ):
            path = ROOT / qml
            self.assertIn(helper, path.read_text())
            self.assertTrue((path.parent / helper).is_file())

    def test_cache_fingerprints_application_sources(self):
        import snapshot_cache
        self.assertEqual(snapshot_cache.ROOT, ROOT)
        self.assertIn("(ROOT / 'src').glob('*.py')",
                      (ROOT / 'src/snapshot_cache.py').read_text())
