# Plugin verification — 2026-09-11

Implemented and deployed locally:

- Bar icon, shared Omarchy keyboard panel, five target-language choices and a
  one-shot Translate screen button.
- Native credential panel retained as an independent panel entry point. The
  translation popup is owned only by the bar widget, not a second panel loader.
- Inline shell settings, explicit per-invocation target, target-separated pixel
  cache and locale-specific Pango font selection.
- Existing shortcuts and default OpenAI image-context translation retained.

Verification:

- 58 selected automated tests passed, including the previous credential/runtime
  regressions, language validation, cache separation and all five Pango scripts.
- Actual Quickshell/shared-control rendering under isolated headless Sway:
  language choice, persistence call, Esc, duplicate submission and launch only
  after the popup unmaps. The launch executable is replaced with a test double;
  this is not a live cloud end-to-end test.
- Installed manifest validation passed. Running Omarchy reports the widget
  enabled, visible and allocated a 27 × 26 slot in the right bar section.
- Existing credential status IPC responds after installation. The installed
  launcher accepts all five `--target` values in its CLI schema.
- qmllint resolves the QML with a local `qs` import map; dynamic Omarchy
  QObject properties and delegate scope still produce warnings. This is not
  a warning-free lint result.
- No shell restart, keybinding change, real-key entry, private screen upload,
  commit, push or marketplace submission was performed for this change.

The production desktop popup has not been opened for this verification, to
avoid taking over the user's screen. Five-language cloud translation quality
and laptop installation remain unverified. Local translation is a separate
public-text benchmark, not yet connected to this panel.

For an existing credential-only installation, move its own entry from
`plugins[]` to `bar.layout.right[]` when upgrading; preserve other entries.
The current host's enable/put command sees the existing panel entry and does
not automatically migrate it. A new installation can use normal plugin enable.
