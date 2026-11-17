import QtQuick
Item {
    property string path: ""
    property bool watchChanges: false
    signal fileChanged()
    signal loaded()
    signal loadFailed()
    function reload() { loaded() }
    Component.onCompleted: loaded()
}
