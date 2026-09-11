import QtQuick
import Quickshell
import Quickshell.Io
import "."

ShellRoot {
  id: test
  property int step: 0
  property string request: "0123456789abcdef0123456789abcdef"
  property var form: null
  property int waits: 0
  CredentialPanel { id: panel }
  Process { id: escapeKey; command: ["/usr/bin/wtype", "-s", "300", "-k", "Escape"] }
  function check(condition, message) { if (!condition) throw new Error(message) }
  function find(node, name, depth) {
    if (!node || depth > 8) return null
    if (node.objectName === name) return node
    if (node.contentItem) {
      var hit = find(node.contentItem, name, depth + 1)
      if (hit) return hit
    }
    var children = node.data || node.children || []
    for (var c of children) {
      var found = find(c, name, depth + 1)
      if (found) return found
    }
    return null
  }
  function open() { panel.open(JSON.stringify({request: request})) }
  Timer {
    interval: 100; running: true; repeat: true
    onTriggered: {
      try {
        if (++test.waits > 100) throw new Error("deadline")
        if (test.step === 0) {
          panel.open("{bad json")
          check(!panel.opened, "reject invalid payload")
          panel.open("{}")
          check(panel.opened, "settings opens without a translation request")
          panel.close()
          test.open()
          check(panel.opened && panel.status(test.request) === "pending", "open")
          test.form = find(panel, "credentialForm", 0)
          check(test.form !== null, "find real form")
          test.step = 10
        } else if (test.step === 10) {
          test.step = 12
          test.form.parent.grabToImage(function(result) {
            var path = Quickshell.env("SCREEN_LENS_PANEL_IMAGE")
            if (path) result.saveToFile(path)
            test.step = 11
          })
        } else if (test.step === 11) {
          find(test.form, "apiKey", 0).text = "synthetic-test-key"
          test.form.submit()
          test.step = 1
        } else if (test.step === 1 && panel.status(test.request) !== "saving") {
          check(panel.status(test.request) === "saved" && !panel.opened, "saved and hidden")
          test.open()
          check(find(test.form, "apiKey", 0).text === "", "reopen empty")
          find(test.form, "apiKey", 0).text = "synthetic-failure"
          test.form.submit()
          test.step = 2
        } else if (test.step === 2 && panel.status(test.request) !== "saving") {
          check(panel.status(test.request) === "failed" && !panel.opened, "failure is not success")
          test.open()
          find(test.form, "apiKey", 0).text = "synthetic-slow"
          test.form.submit()
          test.step = 3
        } else if (test.step === 3) {
          panel.cancel("ffffffffffffffffffffffffffffffff")
          check(panel.opened, "wrong request cannot cancel")
          escapeKey.running = true
          test.step = 4
        } else if (test.step === 4 && !panel.opened) {
          check(!panel.opened && panel.status(test.request) === "cancelled", "no late success")
          console.log("SCREEN_LENS_PANEL_PASS")
          Qt.quit()
        }
      } catch (e) { console.error("SCREEN_LENS_PANEL_FAIL: " + e); Qt.quit() }
    }
  }
}
