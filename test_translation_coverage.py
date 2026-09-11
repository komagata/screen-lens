import os
import unittest
from unittest.mock import patch

from paragraphs import paragraphs
from translation_settings import source_candidate


class TranslationCoverageTests(unittest.TestCase):
    @patch.dict(os.environ, {'SCREEN_LENS_SOURCE': 'en'})
    def test_body_above_quoted_mention_is_not_author_metadata(self):
        rows = [dict(id='body', text='if not, your /home/ has some issues',
                     x=100, y=100, width=340, height=28),
                dict(id='quote', text='@someone try logging in again',
                     x=104, y=144, width=400, height=20)]
        self.assertIn('body', [r['id'] for r in paragraphs(rows)])

    @patch.dict(os.environ, {'SCREEN_LENS_SOURCE': 'en'})
    def test_author_above_bare_handle_still_preserved(self):
        rows = [dict(id='name', text='Example Person', x=100, y=100,
                     width=180, height=28),
                dict(id='handle', text='@example · 2h', x=104, y=144,
                     width=150, height=20)]
        self.assertEqual(paragraphs(rows), [])

    @patch.dict(os.environ, {'SCREEN_LENS_SOURCE': 'en'})
    def test_wrapped_prose_with_overlapping_ocr_padding_stays_together(self):
        rows = [dict(id='a', text='A new collection inspired by iconic designs',
                     x=368, y=473, width=779, height=31),
                dict(id='b', text='from the game universe and crafted by artists.',
                     x=369, y=496, width=486, height=29)]
        self.assertEqual([r['members'] for r in paragraphs(rows)], [['a', 'b']])

    @patch.dict(os.environ, {'SCREEN_LENS_SOURCE': 'en'})
    def test_strongly_overlapping_rows_do_not_merge(self):
        rows = [dict(id='a', text='First label', x=100, y=100, width=200, height=30),
                dict(id='b', text='Second label', x=100, y=115, width=200, height=30)]
        self.assertEqual(len(paragraphs(rows)), 2)

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
