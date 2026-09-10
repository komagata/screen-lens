import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property bool busy: true
    property bool failed: false
    property bool original: false
    property string statusText: "Recognizing and translating…"
    signal closeRequested()
    signal originalRequested()
    width: 144
    height: 48
    radius: 24
    color: "#ee181c24"
    border.color: "#454c59"
    border.width: 1

    component IconButton: ToolButton {
        id: button
        property string glyph
        property string hint
        width: 40
        height: 40
        hoverEnabled: true
        Accessible.name: hint
        ToolTip.visible: hovered
        ToolTip.delay: 300
        ToolTip.text: hint
        background: Rectangle {
            radius: 20
            color: button.down ? "#49566b" : button.hovered ? "#303947" : "transparent"
        }
        contentItem: Text {
            text: button.glyph
            textFormat: Text.PlainText
            color: button.enabled ? "#f1f5f9" : "#657080"
            font.family: "Noto Sans"
            font.pixelSize: 25
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    Row {
        anchors.centerIn: parent
        spacing: 4
        IconButton {
            objectName: "statusButton"
            glyph: root.busy ? "" : root.failed ? "!" : "▣"
            hint: root.busy ? root.statusText : "Snapshot — " + root.statusText
            BusyIndicator {
                objectName: "busyIndicator"
                palette.dark: "#f1f5f9"
                palette.text: "#f1f5f9"
                anchors.centerIn: parent
                width: 28
                height: 28
                running: root.busy
                visible: running
            }
        }
        IconButton {
            objectName: "originalButton"
            glyph: "⇄"
            hint: root.original ? "Show translation (Space)" : "Show original (Space)"
            enabled: !root.busy && !root.failed
            onClicked: root.originalRequested()
        }
        IconButton {
            objectName: "closeButton"
            glyph: "×"
            hint: "Close translation (Esc)"
            onClicked: root.closeRequested()
        }
    }
}
