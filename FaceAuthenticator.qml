// SPDX-License-Identifier: MIT
// PAM lane design informed by Kosta Hantzis's omarchy-face-unlock (MIT).
// Gaze is an independent, unmodified GPL-3.0-or-later authentication backend.
import QtQuick
import Quickshell.Io
import Quickshell.Services.Pam

Item {
    id: face
    required property var host
    required property bool secure
    property bool allowed: false
    property bool configured: false
    property bool scanning: false
    property string feedbackState: "idle"
    property int successFeedbackMs: 0
    property bool successPending: false
    property double startedAt: 0
    property string message: ""
    property double lastDurationMs: 0

    function cancel() {
        scanning = false
        successPending = false
        successFeedback.stop()
        feedbackState = "idle"
        deadline.stop()
        if (pam.active) pam.abort()
    }
    function fail(message) {
        cancel()
        feedbackState = "failure"
        face.message = message
    }
    function finishSuccess() {
        // A visual result never grants authentication. Only the accepted PAM
        // success below can arm this, and cancellation revokes it immediately.
        if (!successPending) return
        if (!allowed || !secure || !host.lockRequested ||
            host.authenticatingPassword || host.enteredPassword.length > 0) {
            cancel()
            return
        }
        successPending = false
        host.finishUnlock()
    }
    function start() {
        if (!allowed || !configured || !secure || !host.lockRequested ||
            host.authenticatingPassword || host.enteredPassword.length > 0 || scanning || successPending || pam.active) return false
        host.runWake()
        message = "Looking for you…"
        scanning = true
        feedbackState = "checking"
        startedAt = Date.now()
        if (!pam.start()) {
            fail("Face unlock unavailable. Use your password.")
            return false
        }
        deadline.start()
        return true
    }
    onAllowedChanged: if (!allowed) cancel()
    onSecureChanged: if (!secure) cancel()
    FileView {
        path: "/etc/pam.d/omarchy-presence-face"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: face.configured = true
        onLoadFailed: { face.configured = false; face.cancel() }
    }
    PamContext {
        id: pam
        config: "omarchy-presence-face"
        user: face.host.userName
        onCompleted: function(result) {
            var acceptCompletion = face.scanning && face.allowed && face.secure && face.host.lockRequested
            face.scanning = false
            deadline.stop()
            face.lastDurationMs = Date.now() - face.startedAt
            if (!acceptCompletion) return
            if (result === PamResult.Success) {
                face.feedbackState = "success"
                face.successPending = true
                face.message = "Recognized"
                face.host.logEvent("presence-face-success-ms=" + Math.round(face.lastDurationMs))
                if (face.successFeedbackMs > 0) successFeedback.restart()
                else face.finishSuccess()
            } else {
                face.fail("Face not recognized. Use your password or press Enter to retry.")
                face.host.logEvent("presence-face-rejected")
            }
        }
        onError: function(error) {
            if (face.scanning) face.fail("Face unlock unavailable. Use your password.")
        }
        // A dedicated face-only PAM service never receives password text.
        onResponseRequiredChanged: if (responseRequired && face.scanning) {
            face.fail("Face check needs interaction. Use your password.")
        }
    }
    Timer {
        id: deadline
        interval: 6000
        onTriggered: {
            face.fail("Face check timed out. Use your password.")
        }
    }
    Timer {
        id: successFeedback
        interval: Math.max(1, Math.min(300, face.successFeedbackMs))
        onTriggered: face.finishSuccess()
    }
}
