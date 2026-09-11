import QtQuick
import QtQuick.Layouts
import qs.Ui as Ui
import qs.Commons

ColumnLayout {
  id: root
  property bool busy: false
  property string message: ""
  signal saveRequested(string value)
  signal cancelled()
  spacing: Style.space(16)
  onBusyChanged: if (busy) closeButton.forceActiveFocus()

  function reset() { keyInput.text = ""; validation.text = "" }
  function focusInput() {
    if (message === "" && !busy) keyInput.forceActiveFocus()
    else closeButton.forceActiveFocus()
  }
  function submit() {
    if (busy || message !== "") return
    if (!/^[\x21-\x7e]{1,4096}$/.test(keyInput.text)) {
      validation.text = "Enter a key without spaces or line breaks."
      return
    }
    var value = keyInput.text
    reset()
    saveRequested(value)
  }

  Keys.onEscapePressed: root.cancelled()
  Text {
    text: "Screen Lens"
    textFormat: Text.PlainText
    color: Color.foreground
    font.family: Style.font.family
    font.pixelSize: Style.font.title
    font.bold: true
  }
  Text {
    Layout.fillWidth: true
    text: root.message !== "" ? root.message :
      "Enter your OpenAI API key. It will be saved in your desktop keyring.\n\nTranslation sends screen images and text to OpenAI and incurs API charges."
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    color: Color.foreground
    font.family: Style.font.family
    font.pixelSize: Style.font.body
  }
  Ui.TextField {
    id: keyInput
    objectName: "apiKey"
    Layout.fillWidth: true
    visible: root.message === ""
    enabled: !root.busy
    password: true
    maximumLength: 4096
    inputMethodHints: Qt.ImhHiddenText | Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
    placeholderText: "OpenAI API key"
    onAccepted: root.submit()
  }
  Text {
    id: validation
    Layout.fillWidth: true
    visible: text !== ""
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    color: Color.foreground
    font.family: Style.font.family
    font.pixelSize: Style.font.body
  }
  RowLayout {
    Layout.alignment: Qt.AlignRight
    spacing: Style.space(12)
    Ui.Button {
      id: closeButton
      text: root.message !== "" ? "Close" : "Cancel"
      focusable: true
      onClicked: root.cancelled()
    }
    Ui.Button {
      visible: root.message === ""
      text: root.busy ? "Saving…" : "Save"
      enabled: !root.busy
      focusable: true
      bordered: true
      onClicked: root.submit()
    }
  }
}
