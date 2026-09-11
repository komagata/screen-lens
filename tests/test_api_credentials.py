import os
import subprocess
import unittest
from unittest.mock import patch


class CredentialsTests(unittest.TestCase):
    def test_prompt_persists_and_second_launch_does_not_prompt(self):
        import api_credentials as auth
        saved = {}
        prompts = []
        key = 'synthetic-test-credential'
        def run(args, **kwargs):
            self.assertNotIn(key, ' '.join(args))
            self.assertNotEqual(args[0], 'gopass', 'gopass must never be required or invoked')
            code, output = 1, ''
            if args[:2] == ['/usr/bin/secret-tool', 'lookup'] and saved:
                code, output = 0, saved['key']
            return subprocess.CompletedProcess(args, code, output, '')
        def prompt():
            prompts.append(1)
            saved['key'] = key
            return 'saved'
        with patch.dict(os.environ, {}, clear=True), patch.object(auth.subprocess, 'run', side_effect=run), patch('credential_dialog.prompt', side_effect=prompt):
            self.assertEqual(auth.ensure_key(), key)
            self.assertEqual(auth.ensure_key(), key)
        self.assertEqual(len(prompts), 1)

    def test_cancel_does_not_save(self):
        import api_credentials as auth
        with patch.dict(os.environ, {}, clear=True), patch('credential_dialog.prompt', return_value='cancelled'), patch.object(auth.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', '')) as run:
            self.assertIsNone(auth.ensure_key())
            self.assertFalse(any(c.args[0][:2] == ['secret-tool', 'store'] for c in run.call_args_list))

    def test_environment_key_needs_no_external_command(self):
        import api_credentials as auth
        with patch.dict(os.environ, OPENAI_API_KEY='synthetic-env-key'), patch.object(auth.subprocess, 'run') as run:
            self.assertEqual(auth.ensure_key(), 'synthetic-env-key')
            run.assert_not_called()

    def test_save_failure_is_not_reported_as_success(self):
        import api_credentials as auth
        with patch.dict(os.environ, {}, clear=True), patch('credential_dialog.prompt', return_value='failed'), patch.object(auth, 'get_key', return_value=''):
            with self.assertRaises(auth.CredentialError):
                auth.ensure_key()
