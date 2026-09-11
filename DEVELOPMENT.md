# Development

## Repository layout

- `src/`: application Python modules and shared OCR/translation evaluation helpers.
- `tests/`: Python regression tests.
- `tools/`: development-only benchmarks, verification and runtime-bundle utilities.
- `packaging/arch/`: Arch Linux package recipe and launcher.
- Root QML files and `panel/`: Omarchy plugin and translation overlay.
- `qml-tests/`, `qml-credential-tests/`: isolated QML test fixtures.

The plugin manifest stays at the repository root. Python helpers live in `src/`;
runtime assets, `models/`, `runtime/`, and `runtime-manifest.json` remain relative
to the repository or installed application root.

## Run tests

Use an environment with the application dependencies installed:

```sh
PYTHONPATH=src:tools python -m unittest discover -s tests -v
```

Some QML integration tests require Omarchy shared controls or an isolated Sway
session. Skipped tests do not establish real-desktop compatibility.

Run development utilities as modules from the repository root, for example:

```sh
python -m tools.benchmark_runtime_size --help
python -m tools.runtime_bundle --help
```

`src/benchmark.py` and `src/stage_*.py` contain helpers imported by the
application as well as evaluation entry points; they are not disposable scripts.
No existing experimental scripts were deleted during the directory migration.

The AUR recipe pins a published source commit. Updating that pin and its checksum
is a separate release step; local source changes do not update the published package.
