import QtQuick
import QtTest
import Quickshell.Services.Pam
import ".." as Plugin

TestCase {
    id: test
    name: "FaceFeedback"
    property var face
    property var host
    property var pam
    Component {
        id: hostComponent
        QtObject {
            property string userName: "test"
            property bool lockRequested: true
            property bool authenticatingPassword: false
            property string enteredPassword: ""
            property int unlocks: 0
            function runWake() {}
            function logEvent(event) {}
            function finishUnlock() { unlocks++ }
        }
    }
    Component {
        id: faceComponent
        Plugin.FaceAuthenticator { secure: true; allowed: true; successFeedbackMs: 300 }
    }
    function init() {
        host = createTemporaryObject(hostComponent, test)
        face = createTemporaryObject(faceComponent, test, {host: host})
        verify(face !== null)
        pam = findChild(face, "mockPam")
        verify(pam !== null, "Tests must use fake PAM, never the system service")
        tryCompare(face, "configured", true)
    }
    function test_success_is_visible_before_unlock() {
        verify(face.start())
        compare(face.feedbackState, "checking")
        pam.finish(PamResult.Success)
        compare(face.feedbackState, "success")
        compare(host.unlocks, 0)
        verify(!face.start(), "No second scan during the success confirmation")
        tryCompare(host, "unlocks", 1, 1000)
    }
    function test_failure_stays_locked_and_retry_clears_red() {
        face.start()
        pam.finish(PamResult.Failure)
        compare(face.feedbackState, "failure")
        wait(340)
        compare(host.unlocks, 0)
        verify(face.start())
        compare(face.feedbackState, "checking")
    }
    function test_cancel_discards_late_success() {
        face.start()
        face.cancel()
        pam.finish(PamResult.Success)
        wait(340)
        compare(host.unlocks, 0)
        compare(face.feedbackState, "idle")
    }
    function test_cancel_revokes_pending_success() {
        face.start()
        pam.finish(PamResult.Success)
        face.cancel()
        wait(340)
        compare(host.unlocks, 0)
        compare(face.feedbackState, "idle")
    }
    function test_password_entry_blocks_deferred_unlock() {
        face.start()
        pam.finish(PamResult.Success)
        host.enteredPassword = "x"
        wait(340)
        compare(host.unlocks, 0)
        compare(face.feedbackState, "idle")
    }
    function test_disabled_face_revokes_pending_success() {
        face.start()
        pam.finish(PamResult.Success)
        face.allowed = false
        wait(340)
        compare(host.unlocks, 0)
    }
    function test_lost_lock_revokes_pending_success() {
        face.start()
        pam.finish(PamResult.Success)
        face.secure = false
        wait(340)
        compare(host.unlocks, 0)
    }
    function test_error_is_red_but_cancelled_error_is_ignored() {
        face.start()
        pam.error(1)
        compare(face.feedbackState, "failure")
        face.cancel()
        pam.error(1)
        compare(face.feedbackState, "idle")
        compare(host.unlocks, 0)
    }
    function test_other_designs_keep_immediate_unlock() {
        face.successFeedbackMs = 0
        face.start()
        pam.finish(PamResult.Success)
        compare(host.unlocks, 1)
    }
}
