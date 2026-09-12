import QtQuick
import QtQuick.Layouts
import Quickshell
import "Locale.js" as Locale
import qs.Ui as Ui
import qs.Commons

ColumnLayout {
  id: root
  property string source: "en"
  readonly property string defaultTarget: Locale.target(Quickshell.env("LC_ALL"), Quickshell.env("LC_MESSAGES"), Quickshell.env("LANG"))
  property string target: defaultTarget
  property bool busy: false
  property string engineState: "checking"
  readonly property string installCommand: "yay -S screen-lens-bin"
  property bool commandCopied: false
  readonly property string disclosure: "GPT-5.6 Luna · OpenAI\nScreen image + text sent to OpenAI.\nAPI usage charges apply."
  property alias sourceSelector: fromDropdown
  property alias targetSelector: toDropdown
  readonly property var options: languages.map(function(item) { return {value: item.code, label: item.label} })
  function resetSelectors() { fromDropdown.close(); toDropdown.close() }
  readonly property var languages: [
    {code: "ja", label: "日本語"}, {code: "en", label: "English"},
    {code: "zh-CN", label: "简体中文"}, {code: "es", label: "Español"},
    {code: "fr", label: "Français"}
  ]
  signal targetSelected(string code)
  signal sourceSelected(string code)
  signal translateRequested(string code, string sourceCode)
  signal cancelled()
  signal credentialsRequested()
  signal checkRequested()
  spacing: Style.space(12)
  function submit() {
    if (engineState !== "ready" || busy || source === target || !languages.some(function(item) { return item.code === root.target })
        || !languages.some(function(item) { return item.code === root.source })) return
    translateRequested(target, source)
  }
  Keys.onEscapePressed: cancelled()
  Text {
    text: "Screen Lens"; textFormat: Text.PlainText
    font.family: Style.font.family; font.pixelSize: Style.font.title; font.bold: true
    color: Color.foreground
  }
  RowLayout {
    visible: root.engineState === "ready"
    Layout.fillWidth: true
    spacing: Style.space(12)
    Ui.Dropdown {
      id: fromDropdown
      objectName: "sourceSelector"
      Layout.fillWidth: true; Layout.preferredWidth: 1
      label: "From"; value: root.source; options: root.options
      enabled: !root.busy
      onChanged: function(code) { root.source = code; root.sourceSelected(code) }
      onPopupOpenChanged: if (popupOpen) toDropdown.close()
    }
    Text {
      text: "→"; textFormat: Text.PlainText
      Layout.alignment: Qt.AlignBottom
      Layout.bottomMargin: Style.space(8)
      font.family: Style.font.family; font.pixelSize: Style.font.body
      color: Color.foreground
    }
    Ui.Dropdown {
      id: toDropdown
      objectName: "targetSelector"
      Layout.fillWidth: true; Layout.preferredWidth: 1
      label: "To"; value: root.target; options: root.options
      enabled: !root.busy
      onChanged: function(code) { root.target = code; root.targetSelected(code) }
      onPopupOpenChanged: if (popupOpen) fromDropdown.close()
    }
  }
  Ui.Button {
    objectName: "translateButton"
    visible: root.engineState === "ready"
    Layout.fillWidth: true
    text: root.busy ? "Starting…" : root.source === root.target ? "Choose different languages" : "Translate screen"
    bordered: true; focusable: true; enabled: !root.busy && root.source !== root.target
    onClicked: root.submit()
  }
  Text {
    visible: root.engineState === "ready"
    Layout.fillWidth: true
    text: root.disclosure
    textFormat: Text.PlainText; wrapMode: Text.Wrap
    font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
    color: Color.foreground; opacity: 0.7
  }
  Ui.Button {
    objectName: "apiKeySettings"
    visible: root.engineState === "ready"
    Layout.fillWidth: true
    text: "API key settings"
    focusable: true; enabled: !root.busy
    onClicked: root.credentialsRequested()
  }
  ColumnLayout {
    objectName: "setupRequired"
    visible: root.engineState !== "ready"
    Layout.fillWidth: true
    spacing: Style.space(10)
    Text {
      Layout.fillWidth: true
      text: root.engineState === "checking" ? "Checking installation…" : "Setup required"
      textFormat: Text.PlainText
      font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true
      color: Color.foreground
    }
    Text {
      Layout.fillWidth: true
      text: "Install the translation engine in a terminal, then check again. An OpenAI API key is also required."
      textFormat: Text.PlainText; wrapMode: Text.Wrap
      font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
      color: Color.foreground; opacity: 0.7
    }
    TextEdit {
      id: installCommandText
      Layout.fillWidth: true
      text: root.installCommand; textFormat: TextEdit.PlainText
      readOnly: true; selectByMouse: true
      font.family: "monospace"; font.pixelSize: Style.font.body
      color: Color.foreground
    }
    Ui.Button {
      objectName: "copyInstallCommand"
      Layout.fillWidth: true
      text: root.commandCopied ? "Copied" : "Copy command"
      focusable: true; bordered: true
      onClicked: {
        installCommandText.selectAll(); installCommandText.copy(); installCommandText.deselect()
        root.commandCopied = true
      }
    }
    RowLayout {
      Layout.fillWidth: true
      Ui.Button {
        objectName: "installationGuide"
        Layout.fillWidth: true
        text: "Installation guide"; focusable: true
        onClicked: Qt.openUrlExternally("https://github.com/komagata/screen-lens#install")
      }
      Ui.Button {
        objectName: "checkEngineAgain"
        Layout.fillWidth: true
        text: "Check again"; focusable: true
        enabled: root.engineState !== "checking"
        onClicked: root.checkRequested()
      }
    }
  }
}
