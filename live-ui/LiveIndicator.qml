import QtQuick
import QtQuick.Controls

ToolButton {
    id: control
    property var translationState: ({})
    property bool busy: !!translationState.busy
    property bool failed: false
    signal closeRequested()
    width: 44; height: 44
    focusPolicy: Qt.NoFocus
    hoverEnabled: true
    Accessible.name: failed ? "Translation failed. Click to turn off and retry."
                           : "Continuous translation. Click to turn off."
    ToolTip.visible: hovered
    ToolTip.delay: 500
    ToolTip.text: Accessible.name
    onClicked: closeRequested()
    background: Rectangle {
        radius: 14
        color: control.hovered ? "#334155" : "#1e293b"
        border.color: "#64748b"
    }
    contentItem: Text {
        text: control.failed ? "!" : "⟳"
        textFormat: Text.PlainText
        font.family: "DejaVu Sans"
        font.pixelSize: 26
        color: control.failed ? "#fbbf24" : "#f1f5f9"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        RotationAnimator on rotation {
            objectName: "translationSpinner"
            from: 0; to: 360; duration: 1600
            loops: Animation.Infinite
            running: control.busy && !control.failed
            paused: !control.visible
        }
    }
}
