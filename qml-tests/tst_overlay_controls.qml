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
        function test_single_button_closes() {
            controls.busy = false;
            verify(findChild(controls, "originalButton") === null);
            mouseClick(findChild(controls, "translationButton"));
            compare(closeSpy.count, 1);
        }
        function test_busy_can_cancel() {
            controls.busy = true;
            mouseClick(findChild(controls, "translationButton"));
            compare(closeSpy.count, 1);
        }
        function test_compact_and_accessible() {
            compare(controls.width, controls.height);
            verify(controls.width <= 48);
            verify(findChild(controls, "translationButton").Accessible.name.includes("Cancel"));
        }
        function test_icon_rotates_only_while_busy() {
            const icon = findChild(controls, "translationIcon");
            const spin = findChild(controls, "translationRotation");
            verify(icon !== null && spin !== null);
            tryCompare(icon, "status", Image.Ready);
            compare(spin.running, true);
            controls.busy = false;
            compare(spin.running, false);
            compare(icon.rotation, 0);
            controls.failed = true;
            compare(spin.running, false);
        }
    }
}
