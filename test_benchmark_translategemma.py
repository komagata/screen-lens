import importlib.util
import unittest


class TemplateTest(unittest.TestCase):
    def test_text_request_has_language_metadata_and_no_system_role(self):
        self.assertIsNotNone(importlib.util.find_spec('benchmark_translategemma'))
        from benchmark_translategemma import text_body
        data = text_body('Save changes')
        self.assertEqual([m['role'] for m in data['messages']], ['user'])
        self.assertEqual(data['messages'][0]['content'], 'Save changes')
        self.assertEqual(data['chat_template_kwargs']['source_lang_code'], 'en')
        self.assertEqual(data['chat_template_kwargs']['target_lang_code'], 'ja')

    def test_compatible_prompt_preserves_embedded_translation_instruction(self):
        import benchmark_translategemma as module
        self.assertTrue(hasattr(module, 'native_prompt'))
        prompt = module.native_prompt('Save changes')
        self.assertTrue(prompt.startswith('You are a professional English (en) to Japanese (ja) translator.'))
        self.assertTrue(prompt.endswith('Japanese:\n\n\nSave changes'))
        self.assertIn('provided image', module.native_prompt())


if __name__ == '__main__': unittest.main()
