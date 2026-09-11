"""Fixed keyring destination; bounded stdin, no output, no plaintext fallback."""
import os
import signal
import subprocess
import sys


def save(stream):
    data = stream.read(4098)
    key = data.removesuffix(b'\n')
    if not 1 <= len(key) <= 4096 or any(c < 33 or c > 126 for c in key):
        return 2
    try:
        result = subprocess.run(
            ['/usr/bin/secret-tool', 'store', '--label=Screen Lens OpenAI API key',
             'application', 'screen-lens', 'service', 'openai'],
            input=key + b'\n', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=60)
        return 0 if result.returncode == 0 else 1
    except (OSError, subprocess.TimeoutExpired):
        return 1


if __name__ == '__main__':
    # QML invokes us in a private session. On cancellation/deadline, terminate
    # the entire owned group, including a keyring client waiting for unlock.
    if os.getpgrp() != os.getpid():
        raise SystemExit(2)
    def stop(_signum, _frame):
        os.killpg(os.getpgrp(), signal.SIGKILL)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(65)
    raise SystemExit(save(sys.stdin.buffer))
