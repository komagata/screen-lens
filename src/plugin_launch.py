"""Fixed plugin-to-runtime bridge. No shell evaluation or credential arguments."""
import os
from pathlib import Path
import subprocess
import sys
from translation_settings import validate_target


def command(target, home=None, source='en', engine=None, system_launcher=Path('/usr/bin/screen-lens')):
    validate_target(target)
    validate_target(source)
    if engine is not None and engine not in ('openai', 'local'): raise ValueError('Unsupported engine')
    launcher = (home or Path.home()) / '.local/bin/screen-lens'
    if system_launcher.is_file() and os.access(system_launcher, os.X_OK):
        launcher = system_launcher
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise FileNotFoundError('Screen Lens runtime is not installed')
    return [str(launcher), '--lt', '--lt-fast', '--source', source, '--target', target] + (
        ['--provider', engine] if engine is not None else [])


def runtime_available(home=None, system_launcher=Path('/usr/bin/screen-lens')):
    """Check the same executable paths as launch, without starting the engine."""
    try:
        command('ja', home, system_launcher=system_launcher)
        return True
    except OSError:
        return False


def main():
    if sys.argv[1:] == ['--check']:
        return 0 if runtime_available() else 1
    try:
        if len(sys.argv) not in (2, 3, 4): raise ValueError('Expected target, optional source and engine')
        argv = command(sys.argv[1], source=sys.argv[2] if len(sys.argv) >= 3 else 'en',
                       engine=sys.argv[3] if len(sys.argv) == 4 else None)
        os.execv(argv[0], argv)
    except (OSError, ValueError):
        subprocess.run(['/usr/bin/notify-send', 'Screen Lens',
                        'Cannot start translation. Check the Screen Lens runtime installation.'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        return 1


if __name__ == '__main__': sys.exit(main())
