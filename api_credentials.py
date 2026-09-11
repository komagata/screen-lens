"""Interactive first-run setup; secrets travel over pipes, never command arguments."""
import os
import subprocess
import credential_dialog

ATTRIBUTES = ['application', 'screen-lens', 'service', 'openai']


class CredentialError(RuntimeError):
    pass


def command(args, *, input=None, timeout=15):
    try:
        return subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args, 1, '', '')


def get_key():
    value = os.environ.get('OPENAI_API_KEY', '').strip()
    if value:
        return value
    stored = command(['/usr/bin/secret-tool', 'lookup', *ATTRIBUTES], timeout=60)
    return stored.stdout.strip() if stored.returncode == 0 else ''


def ensure_key():
    key = get_key()
    if key:
        return key
    state = credential_dialog.prompt()
    if state in ('cancelled', 'timeout', 'superseded'):
        return None
    if state == 'unavailable':
        raise CredentialError('Enable the komagata.screen-lens Omarchy plugin to configure your API key.')
    if state != 'saved':
        raise CredentialError('API key could not be saved. Unlock or configure your desktop keyring, then try again.')
    key = get_key()
    if not key:
        raise CredentialError('The saved API key could not be read from your desktop keyring.')
    return key


def credentials():
    key = get_key()
    if not key:
        raise CredentialError('No OpenAI API key. Launch Screen Lens from the desktop to configure it.')
    return key


def show_error(message):
    # Callers pass our fixed messages, never provider responses or secret values.
    if credential_dialog.prompt(message) == 'unavailable':
        command(['/usr/bin/notify-send', 'Screen Lens',
                 'Setup failed. Enable the Screen Lens plugin and check your desktop keyring.'])
