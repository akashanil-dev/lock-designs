import QtQuick
Item {
    objectName: "mockPam"
    property string config: ""
    property string user: ""
    property bool active: false
    property bool responseRequired: false
    signal completed(int result)
    signal error(int error)
    function start() { active = true; return true }
    function abort() { active = false }
    function finish(result) { active = false; completed(result) }
}
