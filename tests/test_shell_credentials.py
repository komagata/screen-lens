"""No desktop keyring, user interaction or API calls in these tests."""
import io
import subprocess
import unittest
from unittest.mock import patch


class ShellDialogTests(unittest.TestCase):
    def run_dialog(self, statuses):
        import credential_dialog as dialog
        calls = []
        def ipc(*args):
            calls.append(args)
            if args[0] == 'summon':
                return 'ok'
            if args[2] == 'status':
                return next(statuses)
            return 'ok'
        with patch.object(dialog, 'ipc', side_effect=ipc), patch.object(dialog.time, 'sleep'):
            result = dialog.prompt()
        return result, calls

    def test_saved_is_status_only_and_closes_matching_request(self):
        result, calls = self.run_dialog(iter(['unknown', 'pending', 'saving', 'saved']))
        self.assertEqual(result, 'saved')
        self.assertEqual(calls[-1][2], 'cancel')
        self.assertEqual(calls[1][3], calls[-1][3])

    def test_cancel_and_save_failure_are_not_success(self):
        for status in ('cancelled', 'failed'):
            self.assertEqual(self.run_dialog(iter([status]))[0], status)

    def test_missing_plugin_fails_without_waiting(self):
        import credential_dialog as dialog
        with patch.object(dialog, 'ipc', return_value='unknown'), patch.object(dialog.time, 'sleep') as sleep:
            self.assertEqual(dialog.prompt(), 'unavailable')
            sleep.assert_not_called()

    def test_timeout_cancels_the_request(self):
        import credential_dialog as dialog
        with patch.object(dialog, 'ipc', return_value='ok') as ipc, patch.object(dialog.time, 'monotonic', side_effect=[0, 301]):
            self.assertEqual(dialog.prompt(), 'timeout')
        self.assertEqual(ipc.call_args.args[2], 'cancel')


class StoreTests(unittest.TestCase):
    def test_secret_only_on_stdin_and_outputs_discarded(self):
        import credential_store as store
        secret = 'synthetic-not-a-real-key'
        with patch.object(store.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(store.save(io.BytesIO((secret + '\n').encode())), 0)
        args, kwargs = run.call_args
        self.assertEqual(args[0][0], '/usr/bin/secret-tool')
        self.assertNotIn(secret, ' '.join(args[0]))
        self.assertEqual(kwargs['input'], secret.encode() + b'\n')
        self.assertEqual(kwargs['stdout'], subprocess.DEVNULL)
        self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)

    def test_invalid_key_never_reaches_keyring(self):
        import credential_store as store
        for data in (b'', b'x' * 4097, b'key with spaces', b'key\x00', b'\xff'):
            with patch.object(store.subprocess, 'run') as run:
                self.assertNotEqual(store.save(io.BytesIO(data)), 0)
                run.assert_not_called()

    def test_store_failure(self):
        import credential_store as store
        with patch.object(store.subprocess, 'run', side_effect=subprocess.TimeoutExpired('secret-tool', 60)):
            self.assertNotEqual(store.save(io.BytesIO(b'synthetic')), 0)
