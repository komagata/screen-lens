import QtQuick
import QtTest

Item {
    width: 800
    height: 500
    TestCase {
        name: "SnapshotControls"
        when: windowShown
        property var view
        SignalSpy { id: closed; signalName: "closeRequested" }
        function init() {
            const component = Qt.createComponent("../SnapshotView.qml");
            compare(component.status, Component.Ready, component.errorString());
            view = createTemporaryObject(component, parent, {
                width: 800, height: 500,
                originalSource: Qt.resolvedUrl("../demo.svg"),
                translatedSource: Qt.resolvedUrl("../demo-comparison.svg"),
                translatedScreen: true
            });
            verify(view !== null);
            view.forceActiveFocus();
            closed.target = view;
            closed.clear();
        }
        function test_space_toggles_original_and_translation() {
            compare(view.source, view.translatedSource);
            keyClick(Qt.Key_Space);
            compare(view.original, true);
            compare(view.source, view.originalSource);
            keyClick(Qt.Key_Space);
            compare(view.source, view.translatedSource);
        }
        function test_pending_translation_shows_original() {
            view.translatedScreen = false;
            compare(view.source, view.originalSource);
            keyClick(Qt.Key_Space);
            compare(view.source, view.originalSource);
        }
        function test_escape_requests_close() {
            keyClick(Qt.Key_Escape);
            compare(closed.count, 1);
        }
        function test_shortcut_requests_close() {
            keyClick(Qt.Key_J, Qt.ControlModifier | Qt.MetaModifier);
            compare(closed.count, 1);
        }
        function test_click_requests_close() {
            mouseClick(view, 20, 20);
            compare(closed.count, 1);
        }
        function test_scroll_requests_close() {
            mouseWheel(view, 100, 100, 0, -120);
            compare(closed.count, 1);
        }
        function test_navigation_requests_close_data() {
            return [{tag: "page-down", key: Qt.Key_PageDown},
                    {tag: "down", key: Qt.Key_Down},
                    {tag: "home", key: Qt.Key_Home},
                    {tag: "enter", key: Qt.Key_Return},
                    {tag: "typing", key: Qt.Key_A}];
        }
        function test_navigation_requests_close(data) {
            keyClick(data.key);
            compare(closed.count, 1);
        }
        function test_desktop_changes_close() {
            verify(typeof view.desktopChanged === "function");
            view.desktopChanged("activewindowv2");
            compare(closed.count, 1);
            view.desktopChanged("workspacev2");
            compare(closed.count, 2);
            view.desktopChanged("openlayer");
            compare(closed.count, 2); // The snapshot's own layer must not dismiss it.
        }
    }
}
