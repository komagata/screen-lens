from pathlib import Path
import tempfile
import unittest


class SystemPackageTests(unittest.TestCase):
    def test_system_launcher_precedes_legacy_user_launcher(self):
        from plugin_launch import command
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            system = home / 'system-screen-lens'
            system.touch(); system.chmod(0o755)
            self.assertEqual(command('ja', home, system_launcher=system)[0], str(system))

    def test_panel_link_is_idempotent(self):
        from package_entry import link_panel
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = root / 'packaged'; panel.mkdir()
            target = root / 'plugins' / 'komagata.screen-lens'
            self.assertTrue(link_panel(panel, target))
            self.assertFalse(link_panel(panel, target))
            self.assertEqual(target.resolve(), panel)

    def test_unmanaged_panel_is_not_overwritten(self):
        from package_entry import link_panel
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'existing'; target.mkdir()
            with self.assertRaises(FileExistsError):
                link_panel(Path(tmp) / 'packaged', target)
            self.assertTrue(target.is_dir())

    def test_packaged_models_are_explicit_and_missing_files_fail(self):
        from ocr_backends import packaged_models
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(packaged_models(root), {})
            (root / 'system-package').touch()
            with self.assertRaises(FileNotFoundError): packaged_models(root)
            (root / 'models').mkdir()
            for name in ('ch_PP-OCRv5_det_mobile.onnx', 'PP-OCRv6_rec_small.onnx',
                         'ch_ppocr_mobile_v2.0_cls_mobile.onnx'):
                (root / 'models' / name).touch()
            self.assertEqual(len(packaged_models(root)), 3)
