import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

ShellRoot {
    id: root
    property var state: ({lines: []})
    property bool fresh: false
    property bool captureSuspended: false
    FileView {
        path: Quickshell.env("SCREEN_LENS_DIR") + "/state.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: { root.state = JSON.parse(text()); root.fresh = true; watchdog.restart(); }
    }
    Timer { id: watchdog; interval: 1500; onTriggered: root.fresh = false }
    Process {
        command: [Quickshell.env("SCREEN_LENS_LIVE_PYTHON"),
                  Quickshell.env("SCREEN_LENS_LIVE_SCRIPT"), Quickshell.env("SCREEN_LENS_DIR")]
        running: true
        onExited: { root.fresh = false; Qt.quit(); }
    }
    IpcHandler {
        target: "lens"
        function close(): void { Qt.quit(); }
        function suspendCapture(suspended: bool): string {
            root.captureSuspended = suspended;
            return suspended ? "suspended" : "resumed";
        }
    }
    Timer {
        interval: Math.max(1, Number(Quickshell.env("SCREEN_LENS_LIVE_TIMEOUT"))) * 1000
        running: Number(Quickshell.env("SCREEN_LENS_LIVE_TIMEOUT")) > 0
        onTriggered: Qt.quit()
    }
    PanelWindow {
        screen: Quickshell.screens.find(s => s.name === root.state.monitor) || Quickshell.screens[0]
        anchors { top: true; bottom: true; left: true; right: true }
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "screen-lens-live"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        mask: Region { item: indicator }
        Image {
            visible: !root.captureSuspended
            x: root.state.x || 0
            y: root.state.y || 0
            width: root.state.width || 0
            height: root.state.height || 0
            source: root.fresh && root.state.overlay ? "file://" + Quickshell.env("SCREEN_LENS_DIR") + "/" + root.state.overlay : ""
            cache: false
            fillMode: Image.Stretch
        }
        Repeater {
            model: root.fresh ? root.state.lines : []
            Rectangle {
                visible: !root.captureSuspended
                required property var modelData
                x: root.state.x + modelData.x * root.state.width / root.state.imageWidth
                y: root.state.y + modelData.y * root.state.height / root.state.imageHeight
                width: modelData.width * root.state.width / root.state.imageWidth
                height: modelData.height * root.state.height / root.state.imageHeight
                color: "#171b24"
                Text {
                    anchors.fill: parent
                    text: modelData.translated
                    textFormat: Text.PlainText
                    color: "white"
                    font.family: "Noto Sans CJK JP"
                    font.pixelSize: parent.height
                    minimumPixelSize: 6
                    fontSizeMode: Text.Fit
                    elide: Text.ElideRight
                }
            }
        }
        LiveIndicator {
            id: indicator
            visible: !root.captureSuspended
            anchors { right: parent.right; bottom: parent.bottom; margins: 10 }
            translationState: root.state
            failed: !root.fresh || !!root.state.lastError
            onCloseRequested: Qt.quit()
        }
    }
}
