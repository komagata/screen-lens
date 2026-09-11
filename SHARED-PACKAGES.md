# Shared Omarchy package variants

Local validation on Omarchy 4.0.2 / x86-64 / Python 3.14, 2026-09-11.
No package or credential was installed, removed, or migrated: the extra
packages were already present on this development PC.

| Variant | Application directory | Extra packages above checked base | Combined estimate |
| --- | ---: | ---: | ---: |
| Shared base (default) | 85.6 MB | 0 | 85.6 MB |
| Shared NumPy | 63.1 MB | 51.6 MB | 114.7 MB |
| Shared NumPy + OpenCV | 49.0 MB | 495.0 MB | 544.0 MB |

Application sizes are allocated, uncompressed directory sizes, rounded to
decimal MB; screenshots, caches and retained backups are excluded. Additional
package sizes use the installed pacman metadata and dependency closure minus
the checked Omarchy base closure. They are estimates for another machine, not
a measured clean-VM installation. Downloads are a different quantity. Package
versions and dependencies may change. On this PC the added package cost is zero
because all tested extra packages are already installed.

## What is shared

All variants use system Python, GTK3/GObject, Cairo/Pango, fonts and keyring.
The password dialog now uses the Omarchy Shell's shared QML controls instead
of a standalone GTK/Zenity helper. The real keyring
attributes and storage behavior are unchanged; secrets use pipes, not argv.

`python-requests` (and its HTTP dependencies), `python-yaml` and
`python-packaging` are already pulled in by base `yt-dlp`, `udiskie` and
`python-poetry-core`. Their private copies and obsolete distribution metadata
are omitted. Remaining bundled-library licenses are retained.

The NumPy variant additionally uses `python-numpy` 2.5.2-1, replacing the private
2.5.3 build. The extra variant also uses `python-opencv` 5.0.0-9. Its large
incremental dependency is VTK (about 380 MB); OpenCV itself is already in the
checked base dependency closure. This is why the smallest app is not the
smallest total installation.

To prepare an extra variant on another machine, first review:

```sh
sudo pacman -S --needed python-numpy
# Only for the smallest-application variant:
sudo pacman -S --needed python-opencv
```

These commands do not build the application bundle. Packaging uses
`runtime_bundle.py SOURCE TARGET --shared base|numpy|extra` against the prepared
compact runtime and a matching `runtime-manifest.json`. Start a complete bundle
with `./screen-lens --lt --lt-fast`, not the old Python 3.12 venv. System site
packages must be enabled (do not launch with `python -S`). No source screenshots
are included in the bundles.

## Verification

- Base and extra variants: exact OCR text/coordinates on six synthetic fixtures
  plus two saved real desktop screenshots, using unchanged OCR models.
- NumPy-only variant: six synthetic fixtures matched exactly.
- Both base and extra variants passed 48 Python tests, including font/layout.
- The earlier GTK save/cancel behavior was tested in isolated Broadway using a
  dummy key. Masked-entry screenshot was visually inspected; no real key was
  read or stored. The system PyGObject emits deprecation warnings in these tests.
- The replacement QML controls and panel were tested in isolated Quickshell
  (offscreen controls and headless Sway panel): masking, bounds, submit, reset,
  save/failure statuses, cancellation while saving, and no late success. The
  panel uses a test storage helper; actual keyring persistence is mocked in
  Python tests, not a claim of a new live credential round trip.
- No paid translation request, live-screen capture or full desktop interaction
  was performed as part of package sharing. Future system package upgrades
  should repeat these compatibility tests.

The base variant is the conservative default. Smaller variants are optional
tradeoffs for users who accept larger/shared system packages.
