import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Ui as Ui
import qs.Commons

// Panel lifecycle and centered layer surface follow Omarchy's panel/OSD pattern.
Ui.Panel {
  id: root
  moduleName: "komagata.screen-lens"
  ipcTarget: moduleName
  property bool alive: true
  property string requestId: ""
  property string outcome: "cancelled"

  function open(payloadJson) {
    if (typeof payloadJson !== "string" || payloadJson.length > 8192) return
    var payload
    try { payload = JSON.parse(payloadJson) } catch (e) { return }
    if (!payload || typeof payload !== "object" || Array.isArray(payload) || store.running) return
    // A settings summon needs no waiting translation process or IPC token.
    if (payload.request === undefined) {
      if (root.opened) return
      payload.request = "settings"
    } else if (typeof payload.request !== "string" || !/^[a-f0-9]{32}$/.test(payload.request)) return
    form.reset()
    requestId = payload.request
    outcome = "pending"
    form.message = typeof payload.message === "string" ? payload.message.slice(0, 1000) : ""
    controller.show()
    expiry.restart()
    Qt.callLater(function() { if (root.alive && root.opened) form.focusInput() })
  }
  function status(request) {
    return request === requestId ? outcome : "superseded"
  }
  function cancel(request) {
    if (request === requestId) close()
  }
  function close() {
    if (outcome === "pending" || outcome === "saving") outcome = "cancelled"
    form.reset()
    store.secret = ""
    if (store.running) store.signal(15)
    controller.hide()
    expiry.stop()
  }
  Component.onDestruction: {
    alive = false
    store.secret = ""
    form.reset()
    if (store.running) store.signal(15)
  }
  Timer { id: expiry; interval: 300000; onTriggered: root.close() }
  Timer {
    id: saveDeadline
    interval: 67000
    onTriggered: {
      if (root.outcome !== "saving") return
      root.outcome = "failed"
      root.close()
    }
  }
  Process {
    id: store
    property string secret: ""
    command: ["/usr/bin/setsid", "/usr/bin/python", "-I", "-S", "-B",
              decodeURIComponent(Qt.resolvedUrl("src/credential_store.py").toString().replace(/^file:\/\//, ""))]
    clearEnvironment: true
    environment: ({
      "HOME": Quickshell.env("HOME"),
      "XDG_RUNTIME_DIR": Quickshell.env("XDG_RUNTIME_DIR"),
      "DBUS_SESSION_BUS_ADDRESS": Quickshell.env("DBUS_SESSION_BUS_ADDRESS"),
      "PATH": "/usr/bin", "LANG": "C.UTF-8"
    })
    function begin(value) {
      if (running || root.outcome !== "pending" || !root.opened) return
      secret = value
      root.outcome = "saving"
      stdinEnabled = true
      running = true
      saveDeadline.restart()
    }
    onStarted: {
      if (root.alive && root.outcome === "saving") write(secret + "\n")
      secret = ""
      stdinEnabled = false
    }
    onExited: function(code, exitStatus) {
      secret = ""
      if (!root.alive) return
      saveDeadline.stop()
      if (root.outcome !== "saving") return
      root.outcome = code === 0 && exitStatus === 0 ? "saved" : "failed"
      root.close()
    }
    // The helper emits no output. Drain without buffering or logging even if it fails.
    stdout: SplitParser { splitMarker: ""; onRead: function(chunk) {} }
    stderr: SplitParser { splitMarker: ""; onRead: function(chunk) {} }
  }
  PanelWindow {
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "screen-lens-credentials"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    Rectangle { anchors.fill: parent; color: "#66000000" }
    MouseArea { anchors.fill: parent; onClicked: root.close() }
    Ui.BorderSurface {
      id: card
      anchors.centerIn: parent
      width: Math.min(Style.space(560), parent.width - Style.space(32))
      height: form.implicitHeight + Style.space(48)
      color: Color.background
      radius: Style.cornerRadius
      borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, 1)
      MouseArea { anchors.fill: parent }
      CredentialForm {
        id: form
        objectName: "credentialForm"
        anchors.centerIn: parent
        width: parent.width - Style.space(48)
        busy: root.outcome === "saving"
        onSaveRequested: function(value) { store.begin(value) }
        onCancelled: root.close()
      }
    }
  }
}
