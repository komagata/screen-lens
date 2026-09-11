import QtQuick
import Quickshell
import qs.Ui as Ui
import qs.Commons

Ui.BarWidget {
  id: root
  moduleName: "komagata.screen-lens"
  property bool opened: false
  property bool alive: true
  property string pendingTarget: "ja"
  property string pendingSource: "en"
  readonly property bool popoutSwitchClosing: false
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function validTarget(code) { return ["ja", "en", "zh-CN", "es", "fr"].indexOf(code) !== -1 }
  function open() {
    launchTimer.stop()
    credentialsTimer.stop()
    form.resetSelectors()
    form.busy = false
    var code = setting("target", form.defaultTarget)
    form.target = validTarget(code) ? code : form.defaultTarget
    var sourceCode = setting("sourceLanguage", "en")
    form.source = validTarget(sourceCode) ? sourceCode : "en"
    opened = true
  }
  function close() { form.resetSelectors(); opened = false }
  function closeForPopoutSwitch() { close() }
  function selectTarget(code) {
    selectLanguage("target", code)
  }
  function selectSource(code) {
    selectLanguage("sourceLanguage", code)
  }
  function selectLanguage(field, code) {
    if (["sourceLanguage", "target"].indexOf(field) === -1 || !validTarget(code)) return
    var entry = { id: root.moduleName }
    for (var key in root.settings) if (key !== "id" && key !== "source") entry[key] = root.settings[key]
    entry[field] = code
    entry.translationEngine = "openai"
    root.settings = entry
    if (root.bar && root.bar.shell) root.bar.shell.updateEntryInline(root.moduleName, entry)
  }
  function startTranslation(code, sourceCode) {
    sourceCode = sourceCode || form.source
    if (!validTarget(code) || !validTarget(sourceCode) || code === sourceCode || launchTimer.running) return
    pendingTarget = code
    pendingSource = sourceCode
    selectTarget(code)
    selectSource(sourceCode)
    form.busy = true
    close()
    launchTimer.restart()
  }
  function openCredentials() {
    launchTimer.stop()
    close()
    credentialsTimer.restart()
  }
  Component.onDestruction: { alive = false; launchTimer.stop(); credentialsTimer.stop() }

  Timer {
    id: credentialsTimer
    interval: 50; repeat: true
    onTriggered: {
      if (popup.visible || popup.backingWindowVisible) return
      stop()
      if (root.alive && root.bar && root.bar.shell)
        root.bar.shell.summon(root.moduleName, "{}")
    }
  }

  Timer {
    id: launchTimer
    interval: 50; repeat: true
    onTriggered: {
      // Wait for the shared panel's fade-out AND surface unmap before capture.
      if (popup.visible || popup.backingWindowVisible) return
      stop()
      if (root.alive) Quickshell.execDetached(["/usr/bin/python", "-B",
        decodeURIComponent(Qt.resolvedUrl("../src/plugin_launch.py").toString().replace(/^file:\/\//, "")),
        root.pendingTarget, root.pendingSource, "openai"])
    }
  }
  Ui.BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    tooltipText: ""
    iconComponent: Component {
      Image { source: Qt.resolvedUrl("../assets/languages.svg"); fillMode: Image.PreserveAspectFit; sourceSize: Qt.size(48, 48) }
    }
    onPressed: function(b) { root.opened ? root.close() : root.open() }
  }
  Ui.KeyboardPanel {
    id: popup
    anchorItem: button
    bar: root.bar
    owner: root
    open: root.opened
    focusTarget: form
    contentWidth: fittedContentWidth(380)
    contentHeight: fittedContentHeight(form.implicitHeight)
    LanguagePairForm {
      id: form
      anchors.fill: parent
      onTargetSelected: function(code) { root.selectTarget(code) }
      onSourceSelected: function(code) { root.selectSource(code) }
      onTranslateRequested: function(code, sourceCode) { root.startTranslation(code, sourceCode) }
      onCancelled: root.close()
      onCredentialsRequested: root.openCredentials()
    }
  }
}
