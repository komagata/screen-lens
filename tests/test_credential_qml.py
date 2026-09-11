"""Exercise the real shared controls in an isolated, offscreen Quickshell."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(Path('/usr/share/omarchy/shell/Ui/TextField.qml').exists(), 'Requires Omarchy shared controls')
class CredentialQmlTests(unittest.TestCase):
    def test_bar_panel(self):
        self.assertTrue((ROOT / 'panel/LanguagePairWidget.qml').exists(), 'Bar widget is not implemented')
        if not os.environ.get('SCREEN_LENS_TEST_SWAY'):
            self.skipTest('Set SCREEN_LENS_TEST_SWAY for bar-panel test')
        self.run_qml('bar.qml', 'BAR')

    def test_translation_form(self):
        self.assertTrue((ROOT / 'panel/LanguagePairForm.qml').exists(), 'Translation panel is not implemented')
        self.run_qml('translation.qml', 'TRANSLATION')

    def test_real_form(self):
        self.run_qml('check.qml', 'FORM')

    def test_panel_lifecycle_and_stdin(self):
        if not os.environ.get('SCREEN_LENS_TEST_SWAY'):
            self.skipTest('Set SCREEN_LENS_TEST_SWAY to a headless Sway executable')
        self.run_qml('panel.qml', 'PANEL')

    def run_qml(self, source, marker):
        with tempfile.TemporaryDirectory(prefix='screen-lens qml-') as temp:
            base = Path(temp)
            tests = base / 'tests'
            tests.mkdir()
            (tests / 'src').mkdir()
            shutil.copy2(ROOT / 'CredentialForm.qml', tests)
            shutil.copy2(ROOT / 'CredentialPanel.qml', tests)
            if (ROOT / 'panel').exists():
                shutil.copytree(ROOT / 'panel', tests / 'panel')
                shutil.copytree(ROOT / 'assets', tests / 'assets')
                shutil.copy2(ROOT / 'qml-credential-tests/fake_launch.py', tests / 'src/plugin_launch.py')
            shutil.copy2(ROOT / 'qml-credential-tests/fake_store.py', tests / 'src/credential_store.py')
            shutil.copy2(ROOT / 'qml-credential-tests' / source, tests)
            for name in ('Ui', 'Commons'):
                (tests / name).symlink_to('/usr/share/omarchy/shell/' + name, target_is_directory=True)
            env = os.environ | {'QT_QPA_PLATFORM': 'offscreen', 'QT_QPA_PLATFORMTHEME': 'generic'}
            env['SCREEN_LENS_FAKE_LAUNCH_RESULT'] = str(base / 'launch.json')
            compositor = None
            log = tempfile.TemporaryFile()
            try:
                if marker in ('PANEL', 'BAR'):
                    runtime = base / 'runtime'
                    runtime.mkdir(mode=0o700)
                    env.update(XDG_RUNTIME_DIR=str(runtime), QT_QPA_PLATFORM='wayland',
                               QT_QUICK_BACKEND='software', DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent')
                    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE', 'SWAYSOCK'):
                        env.pop(key, None)
                    sway_env = env | {'WLR_BACKENDS': 'headless', 'WLR_RENDERER': 'pixman',
                                     'WLR_LIBINPUT_NO_DEVICES': '1'}
                    sway = Path(os.environ['SCREEN_LENS_TEST_SWAY'])
                    sway_env['LD_LIBRARY_PATH'] = str(sway.parent.parent / 'lib')
                    compositor = subprocess.Popen([str(sway), '-c', str(ROOT / 'qml-credential-tests/sway.conf')],
                                                  env=sway_env, stdout=log, stderr=log)
                    deadline = time.monotonic() + 5
                    while not any(p.is_socket() for p in runtime.glob('wayland-*')):
                        if compositor.poll() is not None or time.monotonic() > deadline:
                            log.seek(0)
                            self.fail(log.read(16384).decode(errors='replace'))
                        time.sleep(0.05)
                    env['WAYLAND_DISPLAY'] = next(p.name for p in runtime.glob('wayland-*') if p.is_socket())
                result = subprocess.run(['/usr/bin/quickshell', '--no-color', '-p', str(tests / source)],
                                        env=env, capture_output=True, text=True, timeout=15)
            finally:
                if compositor is not None:
                    compositor.terminate()
                    try: compositor.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        compositor.kill(); compositor.wait()
                log.close()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f'SCREEN_LENS_{marker}_PASS', result.stdout + result.stderr)
            self.assertNotIn(f'SCREEN_LENS_{marker}_FAIL', result.stdout + result.stderr)
            if marker == 'BAR':
                import json
                self.assertEqual(json.loads((base / 'launch.json').read_text()), ['ja', 'fr', 'openai'])
