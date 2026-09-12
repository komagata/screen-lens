import QtQuick
import Quickshell
import "panel"

ShellRoot {
  id: root
  property int calls: 0
  property string selected: ""
  property string selectedSource: ""
  property int checks: 0
  function itemNamed(item, name) {
    if (item.objectName === name) return item
    for (var i = 0; i < item.children.length; i++) {
      var result = itemNamed(item.children[i], name)
      if (result) return result
    }
    return null
  }
  FloatingWindow {
    visible: true
    implicitWidth: 420
    implicitHeight: form.implicitHeight + 40
    color: "#151515"
    TextEdit { id: clipboardProbe; visible: false; textFormat: TextEdit.PlainText }
    LanguagePairForm {
      id: form
      anchors.fill: parent
      anchors.margins: 20
      onTranslateRequested: function(code, sourceCode) { root.calls++; root.selected = code; root.selectedSource = sourceCode }
      onCheckRequested: root.checks++
    }
  }
  Timer {
    interval: 250; running: true
    onTriggered: {
      try {
        if (form.target !== (Quickshell.env("SCREEN_LENS_EXPECT_TARGET") || "en") || form.source !== "en" || form.languages.length !== 5) throw Error("defaults")
        if (!form.sourceSelector || !form.targetSelector) throw Error("missing compact selectors")
        if (form.engine !== undefined) throw Error("engine selector must be removed")
        if (form.disclosure.indexOf("OpenAI") === -1) throw Error("cloud disclosure")
        if (form.sourceSelector.popupOpen || form.targetSelector.popupOpen) throw Error("choices must start collapsed")
        form.sourceSelector.changed("ja")
        form.targetSelector.changed("fr")
        if (form.source !== "ja" || form.target !== "fr") throw Error("dropdown selection")
        form.target = "fr"; form.source = "ja"
        if (form.engineState !== "checking") throw Error("must check before translating")
        if (root.itemNamed(form, "checkEngineAgain").enabled) throw Error("duplicate check")
        form.submit()
        if (root.calls !== 0) throw Error("translated before check")
        form.engineState = "missing"
        form.submit()
        if (root.calls !== 0) throw Error("translated without engine")
        if (form.installCommand !== "yay -S screen-lens-bin") throw Error("install command")
        if (!root.itemNamed(form, "setupRequired").visible || root.itemNamed(form, "translateButton").visible) throw Error("setup visibility")
        root.itemNamed(form, "copyInstallCommand").clicked()
        if (!form.commandCopied) throw Error("copy feedback")
        clipboardProbe.paste()
        if (clipboardProbe.text !== form.installCommand) throw Error("clipboard content")
        root.itemNamed(form, "checkEngineAgain").clicked()
        if (root.checks !== 1) throw Error("retry signal")
        form.engineState = "ready"
        if (root.itemNamed(form, "setupRequired").visible || !root.itemNamed(form, "apiKeySettings").visible) throw Error("ready visibility")
        form.submit()
        if (root.calls !== 1 || root.selected !== "fr" || root.selectedSource !== "ja") throw Error("selection")
        form.busy = true; form.submit()
        if (root.calls !== 1) throw Error("duplicate")
        form.busy = false; form.target = "ar"; form.submit()
        if (root.calls !== 1) throw Error("unsupported")
        form.target = "ja"; form.source = "ar"; form.submit()
        if (root.calls !== 1) throw Error("invalid source")
        form.source = "ja"; form.submit()
        if (root.calls !== 1) throw Error("same languages")
        form.source = "en"
        var path = Quickshell.env("SCREEN_LENS_TRANSLATION_IMAGE")
        if (Quickshell.env("SCREEN_LENS_SETUP_IMAGE")) {
          path = Quickshell.env("SCREEN_LENS_SETUP_IMAGE")
          form.engineState = "missing"
          form.commandCopied = false
        }
        if (path) form.grabToImage(function(result) {
          result.saveToFile(path); console.log("SCREEN_LENS_TRANSLATION_PASS"); Qt.quit()
        })
        else { console.log("SCREEN_LENS_TRANSLATION_PASS"); Qt.quit() }
      } catch (error) {
        console.log("SCREEN_LENS_TRANSLATION_FAIL " + error); Qt.quit()
      }
    }
  }
}
