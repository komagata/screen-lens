"""User-session entry point for the Arch package; never run from pacman hooks."""
import os
from pathlib import Path
import subprocess
import sys

PLUGIN_ID = 'komagata.screen-lens'


def link_panel(panel, target):
    if target.is_symlink() and target.readlink() == panel:
        return False
    if target.exists() or target.is_symlink():
        raise FileExistsError('An existing Screen Lens plugin must be removed before enabling the packaged panel')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(panel, target_is_directory=True)
    return True


def main():
    root = Path(__file__).resolve().parent
    args = sys.argv[1:]
    if args == ['--setup-panel']:
        target = Path.home() / '.config/omarchy/plugins' / PLUGIN_ID
        created = link_panel(root, target)
        try:
            subprocess.run(['/usr/bin/omarchy-shell', 'shell', 'rescanPlugins'], check=True, timeout=10)
            subprocess.run(['/usr/bin/omarchy', 'plugin', 'enable', PLUGIN_ID], check=True, timeout=20)
        except Exception:
            if created and target.is_symlink() and target.readlink() == root:
                target.unlink()
            raise
        return
    os.execv('/usr/bin/python', ['/usr/bin/python', '-B', str(root / 'lens.py'),
                               *(args or ['--lt', '--lt-fast'])])


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.SubprocessError) as error:
        print(f'Screen Lens setup failed: {error}', file=sys.stderr)
        sys.exit(1)
