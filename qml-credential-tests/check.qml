import QtQuick
import Quickshell
import "."

ShellRoot {
  property int saves: 0
  property string received: ""
  FloatingWindow {
    visible: true
    implicitWidth: 560
    implicitHeight: 340
    color: "#1a1b26"
    CredentialForm {
      id: form
      anchors.centerIn: parent
      width: 512
      onSaveRequested: function(value) { saves++; received = value }
    }
  }
  function check(condition, message) { if (!condition) throw new Error(message) }
  function child(item, name) {
    if (item.objectName === name) return item
    for (var c of item.children) { var found = child(c, name); if (found) return found }
    return null
  }
  Timer {
    interval: 300; running: true
    onTriggered: {
      try {
        var field = child(form, "apiKey")
        check(field.echoMode === TextInput.Password, "password mask")
        check(field.maximumLength === 4096, "input cap")
        for (var value of ["", "a b", "a\nb", "a\u0000b", "日本語"]) {
          field.text = value
          form.submit()
          check(saves === 0, "invalid key submitted")
        }
        field.text = "synthetic-test-key"
        form.submit()
        check(saves === 1 && received === "synthetic-test-key", "save signal")
        check(field.text === "", "clear after save")
        field.text = "synthetic-test-key"
        form.reset()
        check(field.text === "", "clear on reset")
        field.text = "synthetic-test-key"
        form.busy = true
        form.submit()
        check(saves === 1, "duplicate submit")
        form.busy = false
        form.reset()
        field.text = "synthetic-test-key"
        form.grabToImage(function(result) {
          var path = Quickshell.env("SCREEN_LENS_TEST_IMAGE")
          if (path) result.saveToFile(path)
          console.log("SCREEN_LENS_FORM_PASS")
          Qt.quit()
        })
      } catch (e) { console.error("SCREEN_LENS_FORM_FAIL: " + e); Qt.quit() }
    }
  }
}
