import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

ShellRoot {
    id: root
    property string directory: Quickshell.env("SCREEN_LENS_DIR")
    property var state: ({lines: [], status: "Loading…"})
    property alias original: snapshot.original
    Connections {
        target: Hyprland
        function onRawEvent(event) { snapshot.desktopChanged(event.name); }
    }
    FileView {
        id: data
        path: root.directory + "/state.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: root.state = JSON.parse(text())
    }
    Process {
        id: worker
        command: [Quickshell.env("SCREEN_LENS_PYTHON"), Qt.resolvedUrl("lens.py").toString().replace("file://", ""),
                  "--prepare", root.directory, "--endpoint", Quickshell.env("SCREEN_LENS_ENDPOINT"),
                  "--model", Quickshell.env("SCREEN_LENS_MODEL"), "--provider", Quickshell.env("SCREEN_LENS_PROVIDER"),
                  "--ocr", Quickshell.env("SCREEN_LENS_OCR") || "rapidocr"]
                 .concat(Quickshell.env("SCREEN_LENS_DEMO") === "1" ? ["--demo"] : [])
                 .concat(Quickshell.env("SCREEN_LENS_VISION") === "1" ? ["--vision"] : [])
                 .concat(Quickshell.env("SCREEN_LENS_PROSE") === "1" ? ["--prose"] : [])
                 .concat(Quickshell.env("SCREEN_LENS_LT") === "1" ? ["--lt"] : [])
                 .concat(Quickshell.env("SCREEN_LENS_LT_FAST") === "1" ? ["--lt-fast"] : [])
        running: true
        onExited: data.reload()
    }
    IpcHandler {
        target: "lens"
        function close(): void { Qt.quit(); }
    }
    Timer {
        interval: Math.max(1, Number(Quickshell.env("SCREEN_LENS_TIMEOUT")) || 120) * 1000
        running: true
        onTriggered: Qt.quit()
    }
    PanelWindow {
        id: panel
        screen: Quickshell.screens.find(s => s.name === root.state.monitor) || Quickshell.screens[0]
        anchors { top: true; bottom: true; left: true; right: true }
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "screen-lens"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
        color: "#171b24"
        SnapshotView {
            id: snapshot
            anchors.fill: parent
            originalSource: "file://" + root.directory + "/screen.png"
            translatedSource: "file://" + root.directory + "/translated.png"
            translatedScreen: root.state.translatedScreen === true
            onCloseRequested: Qt.quit()
            // Texture readiness is a measurement marker, not compositor presentation.
            onImageReady: translated => console.log("SCREEN_LENS_IMAGE_READY " + JSON.stringify({
                translated: translated, time_ms: Date.now()
            }))
        }
        Item {
            anchors.fill: parent
            Repeater {
                model: root.original ? [] : root.state.lines
                Rectangle {
                    required property var modelData
                    readonly property real sx: panel.width / Math.max(1, snapshot.sourceSize.width)
                    readonly property real sy: panel.height / Math.max(1, snapshot.sourceSize.height)
                    x: modelData.x * sx - 2
                    y: modelData.y * sy - 2
                    width: modelData.width * sx + 4
                    height: modelData.height * sy + 4
                    color: "#171b24"
                    Text {
                        anchors.fill: parent
                        anchors.margins: 1
                        text: modelData.translated
                        textFormat: Text.PlainText
                        color: "#f2f4f8"
                        font.family: "Noto Sans CJK JP"
                        font.pixelSize: Math.max(8, parent.height - 2)
                        minimumPixelSize: 6
                        fontSizeMode: Text.Fit
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }
            }
            OverlayControls {
                anchors { right: parent.right; bottom: parent.bottom; margins: 12 }
                busy: root.state.translatedScreen === undefined
                failed: (root.state.status || "").startsWith("Translation failed")
                original: root.original
                statusText: root.state.status || "Loading…"
                onOriginalRequested: root.original = !root.original
                onCloseRequested: Qt.quit()
            }
        }
    }
}
