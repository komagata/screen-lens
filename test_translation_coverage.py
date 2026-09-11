import os
import unittest
from unittest.mock import patch

from paragraphs import paragraphs
from translation_settings import source_candidate


class TranslationCoverageTests(unittest.TestCase):
    def rows(self, text, **extra):
        return [dict(id='0', text=text, x=0, y=0, width=240, height=24,
                     confidence=1, **extra)]

    @patch.dict(os.environ, {'SCREEN_LENS_SOURCE': 'en'})
    def test_mixed_text_keeps_english_candidate(self):
        for text in ('Save changes（変更を保存）', '日本語 / English', '日本語の説明: Connection failed'):
            with self.subTest(text=text):
                self.assertTrue(source_candidate(text))
                self.assertEqual(len(paragraphs(self.rows(text))), 1)
        self.assertFalse(source_candidate('変更を保存'))

    @patch.dict(os.environ, {'SCREEN_LENS_SOURCE': 'en'})
    def test_dialog_action_ellipsis_is_not_clipped_prose(self):
        for text in ('Open…', 'Save as...', 'Export…', 'Find...'):
            with self.subTest(text=text):
                self.assertEqual(len(paragraphs(self.rows(text))), 1)
        for text in ('The server failed because…', 'Open the file and then…'):
            self.assertEqual(paragraphs(self.rows(text)), [])

    @patch.dict(os.environ, {'SCREEN_LENS_SOURCE': 'en'})
    def test_uncertain_and_protected_rows_still_preserved(self):
        self.assertEqual(paragraphs(self.rows('Open…', ocr_uncertain=True)), [])
        self.assertEqual(paragraphs(self.rows('Save changes', ocr_preserve=True)), [])
        self.assertEqual(paragraphs(self.rows('https://example.com')), [])
