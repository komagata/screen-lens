import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "panel"

ShellRoot {
  id: test
  property int phase: 0
  property int ticks: 0
  QtObject {
    id: fakeBar
    property string position: "top"
    property bool vertical: false
    property int barSize: 36
    property string fontFamily: "sans-serif"
    property color barForeground: "white"
    property color urgent: "red"
    property bool foregroundAnimationEnabled: false
    property var activePopout: null
    property var shell: fakeBar
    property var saved: ({})
    property string summoned: ""
    function summon(id, payload) { summoned = id; if (payload !== "{}") throw Error("settings payload") }
    function requestPopout(owner) { activePopout = owner }
    function releasePopout(owner) { activePopout = null }
    function hideTooltip(owner) {}
    function updateEntryInline(id, entry) { saved = entry }
  }
  PanelWindow {
    visible: true; implicitHeight: 36
    anchors { top: true; left: true; right: true }
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    LanguagePairWidget { id: widget; bar: fakeBar; settings: ({id:"komagata.screen-lens", target:"fr"}) }
  }
  Process { id: escapeKey; command: ["/usr/bin/wtype", "-s", "200", "-k", "Escape"] }
  Process { id: capture; command: ["/usr/bin/grim", Quickshell.env("SCREEN_LENS_BAR_IMAGE") || "/nonexistent/not-used.png"] }
  Timer {
    interval: 100; running: true; repeat: true
    onTriggered: {
      try {
        if (++test.ticks > 80) throw Error("deadline at phase " + test.phase + " opened=" + widget.opened)
        if (test.phase === 0) {
          widget.open()
          if (!widget.opened) throw Error("open")
          widget.selectTarget("es")
          if (fakeBar.saved.target !== "es") throw Error("persist")
          widget.selectTarget("ar")
          if (fakeBar.saved.target !== "es") throw Error("allowlist")
          widget.selectSource("fr")
          if (fakeBar.saved.sourceLanguage !== "fr" || fakeBar.saved.source !== undefined) throw Error("reserved source key")
          widget.selectLanguage("translationEngine", "local")
          if (fakeBar.saved.translationEngine !== "openai") throw Error("panel must keep Luna")
          test.phase = 10
        } else if (test.phase === 10 && test.ticks > 5) {
          if (Quickshell.env("SCREEN_LENS_BAR_IMAGE")) capture.running = true
          escapeKey.running = true
          test.phase = 1
        } else if (test.phase === 1 && !widget.opened) {
          widget.open()
          test.phase = 11
        } else if (test.phase === 11 && test.ticks > 10) {
          widget.startTranslation("ja")
          if (widget.opened) throw Error("must hide before launch")
          test.phase = 2
        } else if (test.phase === 2 && test.ticks > 15) {
          widget.open(); widget.openCredentials()
          if (widget.opened) throw Error("hide before credentials")
          test.phase = 3
        } else if (test.phase === 3 && test.ticks > 25) {
          if (fakeBar.summoned !== "komagata.screen-lens") throw Error("settings summon")
          console.log("SCREEN_LENS_BAR_PASS"); Qt.quit()
        }
      } catch (error) { console.log("SCREEN_LENS_BAR_FAIL " + error); Qt.quit() }
    }
  }
}
