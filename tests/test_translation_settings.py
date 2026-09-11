import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class TranslationSettingsTests(unittest.TestCase):
    def test_shell_source_language_avoids_reserved_source_key(self):
        import translation_settings as settings
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, XDG_CONFIG_HOME=tmp):
            path = Path(tmp) / 'omarchy/shell.json'
            path.parent.mkdir()
            path.write_text(json.dumps({'bar': {'layout': {'right': [
                {'id': 'komagata.screen-lens', 'sourceLanguage': 'fr', 'target': 'ja'}
            ]}}}))
            self.assertEqual(settings.load(), {'source': 'fr', 'target': 'ja'})

    def test_source_roundtrip_and_legacy_default(self):
        import translation_settings as settings
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'settings.json'
            self.assertEqual(settings.load(path).get('source'), 'en')
            settings.save({'source': 'ja', 'target': 'fr'}, path)
            self.assertEqual(settings.load(path), {'source': 'ja', 'target': 'fr'})
            with self.assertRaises(ValueError): settings.save({'source': 'ar', 'target': 'ja'}, path)

    def test_source_in_prompt_and_cache(self):
        from stage_translation import payload
        from snapshot_cache import fingerprint
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, SCREEN_LENS_TARGET='fr'):
            path = Path(tmp)/'screen.png'; Image.new('RGB', (8,8)).save(path)
            with patch.dict(os.environ, SCREEN_LENS_SOURCE='ja'):
                instructions = payload({'groups': [], 'lines': []}, 'text')['instructions']
                self.assertIn('Japanese', instructions)
                self.assertIn('French', instructions)
                from lens import openai_payload
                from translation_context import context_payload
                for body in (openai_payload({}, 'test'), context_payload([], 'test')):
                    self.assertIn('Japanese', body['instructions'])
                    self.assertIn('French', body['instructions'])
                original = fingerprint(path, True)
            with patch.dict(os.environ, SCREEN_LENS_SOURCE='es'):
                self.assertNotEqual(original, fingerprint(path, True))

    def test_non_english_paragraphs_are_eligible(self):
        from paragraphs import paragraphs
        for code, text in [('ja', '変更を保存する'), ('zh-CN', '保存更改'), ('fr', 'Été agréable'), ('es', 'Guardar cambios')]:
            with self.subTest(code=code), patch.dict(os.environ, SCREEN_LENS_SOURCE=code):
                rows = [dict(id='0', text=text, x=0,y=0,width=200,height=24,confidence=1)]
                self.assertEqual(len(paragraphs(rows)), 1)

    def test_locale_default(self):
        settings = self.settings()
        for name, expected in [('ja_JP.UTF-8', 'ja'), ('fr_CA.UTF-8', 'fr'),
                               ('es_MX.UTF-8', 'es'), ('en_GB.UTF-8', 'en'),
                               ('zh_CN.UTF-8', 'zh-CN'), ('zh-Hans-SG', 'zh-CN'),
                               ('zh_TW.UTF-8', 'en'), ('ar_SA.UTF-8', 'en'),
                               ('C.UTF-8', 'en'), ('', 'en')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'LANG': name}, clear=True):
                self.assertEqual(settings.load(Path(tmp)/'missing')['target'], expected)

    def test_locale_precedence_and_saved_choice(self):
        settings = self.settings()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,
                {'LANG': 'ja_JP.UTF-8', 'LC_MESSAGES': 'fr_FR.UTF-8', 'LC_ALL': 'es_ES.UTF-8'}, clear=True):
            path = Path(tmp)/'settings.json'
            self.assertEqual(settings.load(path)['target'], 'es')
            os.environ['LC_ALL'] = ''
            self.assertEqual(settings.load(path)['target'], 'fr')
            settings.save({'target': 'ja'}, path)
            self.assertEqual(settings.load(path)['target'], 'ja')

    def settings(self):
        self.assertIsNotNone(importlib.util.find_spec('translation_settings'),
                             'Shared translation settings are not implemented')
        import translation_settings
        return translation_settings

    def test_five_targets_and_no_rtl(self):
        settings = self.settings()
        self.assertEqual(set(settings.LANGUAGES), {'ja', 'en', 'zh-CN', 'es', 'fr'})
        for invalid in ('ar', 'he', '', '../ja'):
            with self.assertRaises(ValueError): settings.validate_target(invalid)

    def test_save_reload_and_default(self):
        settings = self.settings()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'LC_ALL': 'ja_JP.UTF-8'}):
            path = Path(tmp) / 'settings.json'
            self.assertEqual(settings.load(path)['target'], 'ja')
            settings.save({'target': 'fr'}, path)
            self.assertEqual(settings.load(path)['target'], 'fr')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError): settings.save({'target': 'ar'}, path)
            self.assertEqual(settings.load(path)['target'], 'fr')

    def test_environment_is_validated(self):
        settings = self.settings()
        with patch.dict(os.environ, SCREEN_LENS_TARGET='zh-CN'):
            self.assertEqual(settings.target(), 'zh-CN')
        with patch.dict(os.environ, SCREEN_LENS_TARGET='ar'):
            with self.assertRaises(ValueError): settings.target()

    def test_prompt_uses_target_and_preserves_same_language(self):
        self.settings()
        from stage_translation import payload
        case = {'groups': [], 'lines': []}
        for code, name in [('ja', 'Japanese'), ('fr', 'French'), ('zh-CN', 'Simplified Chinese')]:
            with patch.dict(os.environ, SCREEN_LENS_TARGET=code):
                instructions = payload(case, 'text')['instructions']
            self.assertIn(name, instructions)
            self.assertIn('already in the target language', instructions)

    def test_target_changes_cache_key(self):
        from PIL import Image
        from snapshot_cache import fingerprint
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'screen.png'
            Image.new('RGB', (8, 8)).save(source)
            with patch.dict(os.environ, SCREEN_LENS_TARGET='ja'):
                japanese = fingerprint(source, True)
            with patch.dict(os.environ, SCREEN_LENS_TARGET='fr'):
                self.assertNotEqual(japanese, fingerprint(source, True))

    def test_renderer_uses_locale_specific_font(self):
        settings = self.settings()
        self.assertEqual(settings.font('ja'), 'Noto Sans CJK JP')
        self.assertEqual(settings.font('zh-CN'), 'Noto Sans CJK SC')
        self.assertEqual(settings.font('fr'), 'Noto Sans')

    def test_real_pango_renders_all_five_languages(self):
        import subprocess
        samples = {'ja': '変更を保存する', 'en': 'Save changes', 'zh-CN': '保存更改',
                   'es': 'Guardar los cambios', 'fr': 'Enregistrer les modifications'}
        for code, text in samples.items():
            response = subprocess.run(['/usr/bin/python', '-B', str(Path(__file__).resolve().parents[1] / 'src/pango_patch.py')],
                input=json.dumps(dict(text=text, width=600, height=80, minimum_font_size=18, maximum_font_size=18)),
                env=os.environ | {'SCREEN_LENS_TARGET': code}, capture_output=True, text=True, timeout=5, check=True)
            result = json.loads(response.stdout)
            self.assertTrue(result['shown'], (code, result))
            self.assertEqual(result['unknown_glyphs'], 0)

    def test_reads_plugin_inline_settings(self):
        settings = self.settings()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, XDG_CONFIG_HOME=tmp):
            path = Path(tmp) / 'omarchy/shell.json'
            path.parent.mkdir()
            path.write_text(json.dumps({'bar': {'layout': {'right': [
                {'id': 'komagata.screen-lens', 'target': 'es'}]}}}))
            self.assertEqual(settings.load()['target'], 'es')

    def test_settings_reject_special_files_and_oversize(self):
        settings = self.settings()
        self.assertTrue(hasattr(settings, 'read_json'), 'Descriptor-bound reader is missing')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fifo = base / 'fifo'; os.mkfifo(fifo)
            with self.assertRaises(ValueError): settings.read_json(fifo, 4096)
            huge = base / 'huge'; huge.write_bytes(b' ' * 4097)
            with self.assertRaises(ValueError): settings.read_json(huge, 4096)
            link = base / 'link'; link.symlink_to(huge)
            with self.assertRaises(OSError): settings.read_json(link, 4096)


if __name__ == '__main__': unittest.main()
