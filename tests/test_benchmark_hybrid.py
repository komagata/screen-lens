import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class RoutingTest(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('benchmark_hybrid'), 'Hybrid experiment is not implemented')
        import benchmark_hybrid
        return benchmark_hybrid

    def test_short_labels_use_visual_translation(self):
        module = self.module()
        self.assertEqual(module.route({'text': 'Open'}), 'visual')
        self.assertEqual(module.route({'text': 'Save 20%'}), 'visual')
        self.assertEqual(module.route({'text': 'This article describes the history of machine translation.'}), 'text')

    def test_single_model_mode_keeps_long_text_visual(self):
        module = self.module()
        import inspect
        self.assertIn('all_visual', inspect.signature(module.route).parameters)
        self.assertEqual(module.route({'text': 'This article describes the history of machine translation.'}, all_visual=True), 'visual')

    def test_sensitive_routing_handles_quantities_and_negation_not_references(self):
        module = self.module()
        import inspect
        self.assertIn('sensitive', inspect.signature(module.route).parameters)
        self.assertEqual(module.route({'text': 'Bring 3 herbs to the healer. Do not sell them.'}, sensitive=True), 'visual')
        self.assertEqual(module.route({'text': 'Do not disconnect this drive until the backup finishes.'}, sensitive=True), 'visual')
        self.assertEqual(module.route({'text': 'This article describes the history of machine translation.[1][2]'}, sensitive=True), 'text')

    def test_context_is_exact_nearby_text_not_distant_application(self):
        module = self.module()
        row = dict(id='t', text='A paragraph to translate.', x=50, y=100, width=400, height=30)
        near = dict(id='n', text='Article title', x=50, y=60, width=400, height=30)
        far = dict(id='f', text='Unrelated application', x=1500, y=100, width=400, height=30)
        self.assertEqual(module.nearby({'lines': [row, far, near]}, row), [near])

    def test_source_json_contains_only_translation_targets(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'text_prompt'), 'Source/background boundary is not implemented')
        row = dict(id='t', text='Translate this sentence.', x=50, y=100, width=400, height=30)
        ref = dict(id='n', text='Article title', x=50, y=60, width=400, height=30)
        prompt = module.text_prompt({'lines': [ref]}, [row])
        self.assertIn('Article title', prompt.split('### Source Data\n')[0])
        self.assertEqual(json.loads(prompt.split('### Source Data\n')[1]), {'t': row['text']})

    def test_visual_batch_size_changes_without_dropping_targets(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'batches'), 'Configurable batches are not implemented')
        rows = list(range(63))
        split = module.batches(rows, 32)
        self.assertEqual([len(b) for b in split], [32, 31])
        self.assertEqual([r for batch in split for r in batch], rows)
        with self.assertRaises(ValueError): module.batches(rows, 0)

    def test_small_model_override_rejects_unverified_weights(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'small_model'), 'Isolated small-model selection is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'model.gguf').write_bytes(b'not verified weights')
            with self.assertRaises(ValueError): module.small_model({}, Path(tmp))


if __name__ == '__main__': unittest.main()
