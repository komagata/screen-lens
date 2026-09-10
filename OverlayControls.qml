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
    width: 44
    height: 44
    radius: 22
    color: root.failed ? "#ee5c2828" : "#ee181c24"
    border.color: root.failed ? "#ff998f" : "#454c59"
    border.width: 1

    ToolButton {
        id: button
        objectName: "translationButton"
        anchors.fill: parent
        hoverEnabled: true
        property string hint: root.failed ? root.statusText + " — Close (Esc)"
            : root.busy ? "Translating… — Cancel (Esc)"
            : (root.original ? "Original snapshot" : "Translated snapshot")
                + " — Close (Esc) · Compare (Space)"
        Accessible.name: hint
        ToolTip.visible: hovered
        ToolTip.delay: 300
        ToolTip.text: hint
        background: Rectangle {
            radius: 22
            color: button.down ? "#49566b" : button.hovered ? "#303947" : "transparent"
        }
        contentItem: Item {
            Image {
                id: icon
                objectName: "translationIcon"
                anchors.centerIn: parent
                width: 24
                height: 24
                source: Qt.resolvedUrl("assets/languages.svg")
                sourceSize.width: 48
                sourceSize.height: 48
                RotationAnimator on rotation {
                    objectName: "translationRotation"
                    from: 0
                    to: 360
                    duration: 1800
                    loops: Animation.Infinite
                    running: root.busy && !root.failed
                    onRunningChanged: { if (!running) icon.rotation = 0; }
                }
            }
        }
        onClicked: root.closeRequested()
    }
}
