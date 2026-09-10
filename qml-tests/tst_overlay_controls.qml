import QtQuick
import QtTest

Item {
    width: 480
    height: 160
    TestCase {
        name: "OverlayControls"
        when: windowShown
        property var controls
        SignalSpy { id: closeSpy; signalName: "closeRequested" }
        SignalSpy { id: originalSpy; signalName: "originalRequested" }
        function init() {
            const component = Qt.createComponent("../OverlayControls.qml");
            compare(component.status, Component.Ready, component.errorString());
            controls = createTemporaryObject(component, parent, { x: 20, y: 20 });
            verify(controls !== null);
            closeSpy.target = controls;
            originalSpy.target = controls;
            closeSpy.clear(); originalSpy.clear();
        }
        function test_close_and_original() {
            controls.busy = false;
            mouseClick(findChild(controls, "originalButton"));
            compare(originalSpy.count, 1);
            mouseClick(findChild(controls, "closeButton"));
            compare(closeSpy.count, 1);
        }
        function test_busy_prevents_original_toggle() {
            controls.busy = true;
            verify(!findChild(controls, "originalButton").enabled);
            verify(findChild(controls, "closeButton").enabled);
        }
        function test_compact_and_accessible() {
            verify(controls.width <= 160);
            compare(findChild(controls, "closeButton").Accessible.name, "Close translation (Esc)");
            compare(findChild(controls, "originalButton").Accessible.name, "Show original (Space)");
        }
        function test_busy_indicator_contrasts_with_dark_panel() {
            const indicator = findChild(controls, "busyIndicator");
            verify(indicator !== null);
            compare(indicator.palette.dark.toString(), "#f1f5f9");
            compare(indicator.palette.text.toString(), "#f1f5f9");
        }
    }
}
