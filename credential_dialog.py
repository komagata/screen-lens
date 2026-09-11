"""Status-only bridge to the Omarchy Shell panel. No credentials cross IPC."""
import json
import secrets
import subprocess
import time

PLUGIN_ID = 'komagata.screen-lens'


def ipc(*args):
    # These commands return only short status strings, never a key.
    try:
        result = subprocess.run(['/usr/bin/omarchy-shell', 'shell', *args],
                                capture_output=True, text=True, timeout=3)
        return result.stdout.strip() if result.returncode == 0 else 'unavailable'
    except (OSError, subprocess.TimeoutExpired):
        return 'unavailable'


def prompt(message=''):
    request = secrets.token_hex(16)
    payload = json.dumps({'request': request, 'message': message[:1000]})
    if ipc('summon', PLUGIN_ID, payload) != 'ok':
        return 'unavailable'
    deadline = time.monotonic() + 300
    try:
        while time.monotonic() < deadline:
            state = ipc('call', PLUGIN_ID, 'status', request)
            if state in ('saved', 'cancelled', 'failed', 'unavailable', 'superseded'):
                return state
            time.sleep(0.25)
        return 'timeout'
    finally:
        ipc('call', PLUGIN_ID, 'cancel', request)
