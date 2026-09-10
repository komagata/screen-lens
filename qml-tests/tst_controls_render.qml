import QtQuick
import QtTest
import ".."

Rectangle {
    id: preview
    width: 492
    height: 128
    color: "#101318"
    Row {
        x: 14; y: 40; spacing: 16
        OverlayControls { busy: true }
        OverlayControls { busy: false; statusText: "AI-translated snapshot" }
        OverlayControls { busy: false; failed: true; statusText: "Translation failed" }
    }
    TestCase {
        name: "ControlsRender"
        when: windowShown
        property bool saved: false
        function test_render_states() {
            wait(100);
            preview.grabToImage(function(result) {
                saved = result.saveToFile(Qt.resolvedUrl("../verification-controls.png").toString().replace("file://", ""));
            });
            tryCompare(this, "saved", true);
        }
    }
}
