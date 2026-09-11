import json
import os
from pathlib import Path
import sys

Path(os.environ['SCREEN_LENS_FAKE_LAUNCH_RESULT']).write_text(json.dumps(sys.argv[1:]))
