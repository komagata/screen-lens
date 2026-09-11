import importlib.util
import json
from pathlib import Path
import unittest


class LensTests(unittest.TestCase):
    def core(self):
        self.assertIsNotNone(importlib.util.find_spec('lens'), 'screen lens implementation is missing')
        import lens
        return lens

    def test_ocr_groups_words_into_positioned_lines(self):
        tsv = ('level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
               '5\t1\t1\t1\t1\t1\t10\t20\t40\t20\t96\tHello\n'
               '5\t1\t1\t1\t1\t2\t60\t20\t50\t20\t95\tworld\n')
        self.assertEqual(self.core().parse_tsv(tsv), [dict(id='0', text='Hello world', x=10, y=20, width=100, height=20)])

    def test_ocr_ignores_low_confidence_and_non_english_lines(self):
        tsv = ('level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
               '5\t1\t1\t1\t1\t1\t10\t20\t40\t20\t12\tNoise\n'
               '5\t1\t1\t1\t2\t1\t10\t50\t40\t20\t96\t12345\n')
        self.assertEqual(self.core().parse_tsv(tsv), [])

    def test_large_gaps_do_not_join_separate_controls(self):
        tsv = ('level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
               '5\t1\t1\t1\t1\t1\t10\t20\t40\t20\t96\tSave\n'
               '5\t1\t1\t1\t1\t2\t400\t20\t50\t20\t95\tCancel\n')
        self.assertEqual([r['text'] for r in self.core().parse_tsv(tsv)], ['Save', 'Cancel'])

    def test_translation_requires_exact_ids_and_plain_strings(self):
        core = self.core()
        self.assertEqual(core.validate_translations({'0': '保存'}, ['0']), {'0': '保存'})
        for bad in ({}, {'1': '保存'}, {'0': 3}, {'0': ''}, {'0': 'x' * 10001}):
            with self.subTest(bad=str(bad)[:40]), self.assertRaises(ValueError):
                core.validate_translations(bad, ['0'])

    def test_only_loopback_translation_endpoint_is_allowed(self):
        core = self.core()
        for endpoint in ('http://127.0.0.1:11434', 'http://localhost:11434'):
            core.check_endpoint(endpoint)
        for endpoint in ('https://example.com', 'http://127.0.0.1.evil.test', 'file:///etc/passwd'):
            with self.assertRaises(ValueError):
                core.check_endpoint(endpoint)

    def test_demo_is_explicit_and_not_used_as_translation_fallback(self):
        core = self.core()
        self.assertEqual(core.demo_translate([{'id': '0', 'text': 'Settings'}]), {'0': '設定'})
        self.assertEqual(core.demo_translate([{'id': '0', 'text': 'Unseen sentence'}]), {})

    def test_overlay_has_safe_text_and_exit_controls(self):
        path = Path(__file__).resolve().parents[1] / 'shell.qml'
        self.assertTrue(path.exists(), 'overlay implementation is missing')
        source = path.read_text()
        self.assertIn('Text.PlainText', source)
        self.assertIn('Keys.onEscapePressed', path.with_name('SnapshotView.qml').read_text())
        self.assertIn('onCloseRequested: Qt.quit()', source)
        self.assertIn('function close()', source)
        self.assertIn('WlrLayer.Overlay', source)

    def test_exit_uses_qt_api_not_nonexistent_quickshell_quit(self):
        source = (Path(__file__).resolve().parents[1] / 'shell.qml').read_text()
        self.assertNotIn('Quickshell.quit()', source)
        self.assertIn('Qt.quit()', source)

    def test_openai_payload_uses_luna_no_storage_and_strict_ids(self):
        core = self.core()
        self.assertTrue(hasattr(core, 'openai_payload'), 'OpenAI provider is missing')
        payload = core.openai_payload({'7': 'Settings'}, 'gpt-5.6-luna')
        self.assertEqual(payload['model'], 'gpt-5.6-luna')
        self.assertFalse(payload['store'])
        self.assertNotIn('tools', payload)
        schema = payload['text']['format']['schema']
        self.assertEqual(schema['required'], ['7'])
        self.assertFalse(schema['additionalProperties'])

    def test_openai_response_rejects_incomplete_and_refusal(self):
        core = self.core()
        self.assertTrue(hasattr(core, 'read_openai_response'), 'OpenAI response parser is missing')
        result = {'status': 'completed', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': '{"0":"設定"}'}]}]}
        self.assertEqual(core.read_openai_response(result, ['0']), {'0': '設定'})
        for bad in ({'status': 'incomplete', 'output': []}, {'status': 'completed', 'output': [
                {'type': 'message', 'content': [{'type': 'refusal', 'refusal': 'No'}]}]}):
            with self.assertRaises(ValueError):
                core.read_openai_response(bad, ['0'])


if __name__ == '__main__':
    unittest.main()
