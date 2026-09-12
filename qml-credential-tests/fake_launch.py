import json
import os
from pathlib import Path
import sys

if sys.argv[1:] == ['--check']:
    sys.exit(0)

Path(os.environ['SCREEN_LENS_FAKE_LAUNCH_RESULT']).write_text(json.dumps(sys.argv[1:]))
