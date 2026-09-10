import QtQuick

Item {
    id: view
    property url originalSource
    property url translatedSource
    property bool translatedScreen: false
    property bool original: false
    readonly property alias source: picture.source
    readonly property alias sourceSize: picture.sourceSize
    signal closeRequested()
    signal imageReady(bool translated)
    function desktopChanged(name) {
        // Event metadata only: no background screenshots or cloud requests.
        if (["activewindowv2", "workspacev2", "movewindowv2", "openwindow",
             "closewindow", "monitorremoved", "monitoraddedv2", "fullscreen"].indexOf(name) !== -1)
            closeRequested();
    }
    focus: true
    Image {
        id: picture
        anchors.fill: parent
        source: view.translatedScreen && !view.original ? view.translatedSource : view.originalSource
        fillMode: Image.Stretch
        onStatusChanged: {
            if (status === Image.Ready)
                view.imageReady(view.translatedScreen && !view.original)
        }
    }
    Keys.onEscapePressed: closeRequested()
    Keys.onSpacePressed: original = !original
    Keys.onPressed: event => {
        // Modifier presses alone must not dismiss while the launch chord is held.
        if ([Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta,
             Qt.Key_AltGr].indexOf(event.key) !== -1)
            return;
        // Consume the first action: never replay it against a stale screenshot.
        event.accepted = true;
        closeRequested();
    }
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onClicked: view.closeRequested()
        onWheel: wheel => {
            wheel.accepted = true;
            view.closeRequested();
        }
    }
}
