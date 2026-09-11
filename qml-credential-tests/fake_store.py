"""Isolated QML integration fixture: never contacts Secret Service."""
import sys
import time

value = sys.stdin.buffer.read(4098)
if value == b'synthetic-slow\n':
    time.sleep(4)
    raise SystemExit(0)
raise SystemExit(0 if value == b'synthetic-test-key\n' else 1)
