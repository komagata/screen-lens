import importlib.util
from pathlib import Path
import tempfile
import unittest


class PluginLaunchTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('plugin_launch'), 'Plugin launcher is not implemented')
        import plugin_launch
        return plugin_launch

    def test_reject_invalid_target_before_launch(self):
        module = self.module()
        with self.assertRaises(ValueError): module.command('ar', Path('/not-installed'))

    def test_uses_fixed_user_launcher_and_argv(self):
        module = self.module()
        with tempfile.TemporaryDirectory(prefix='screen lens ') as tmp:
            home = Path(tmp)
            launcher = home / '.local/bin/screen-lens'
            launcher.parent.mkdir(parents=True)
            launcher.touch(); launcher.chmod(0o700)
            self.assertEqual(module.command('fr', home),
                [str(launcher), '--lt', '--lt-fast', '--source', 'en', '--target', 'fr'])
            self.assertEqual(module.command('en', home, source='ja'),
                [str(launcher), '--lt', '--lt-fast', '--source', 'ja', '--target', 'en'])

    def test_missing_runtime_is_explicit(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError): module.command('ja', Path(tmp))

    def test_explicit_local_engine_is_not_cloud(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); launcher = home / '.local/bin/screen-lens'
            launcher.parent.mkdir(parents=True); launcher.touch(); launcher.chmod(0o700)
            result = module.command('ja', home, engine='local')
            self.assertEqual(result[-2:], ['--provider', 'local'])
            with self.assertRaises(ValueError): module.command('ja', home, engine='bad')
