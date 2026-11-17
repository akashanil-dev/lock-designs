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
    property double startedAt: 0
    property string message: ""
    property double lastDurationMs: 0

    function cancel() {
        scanning = false
        deadline.stop()
        if (pam.active) pam.abort()
    }
    function start() {
        if (!allowed || !configured || !secure || !host.lockRequested ||
            host.authenticatingPassword || host.enteredPassword.length > 0 || scanning || pam.active) return false
        host.runWake()
        message = "Looking for you…"
        scanning = true
        startedAt = Date.now()
        if (!pam.start()) {
            cancel()
            message = "Face unlock unavailable. Use your password."
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
                face.message = "Recognized"
                face.host.logEvent("presence-face-success-ms=" + Math.round(face.lastDurationMs))
                face.host.finishUnlock()
            } else {
                face.message = "Face not recognized. Use your password or press Enter to retry."
                face.host.logEvent("presence-face-rejected")
            }
        }
        onError: function(error) {
            face.cancel()
            face.message = "Face unlock unavailable. Use your password."
        }
        // A dedicated face-only PAM service never receives password text.
        onResponseRequiredChanged: if (responseRequired) {
            face.cancel()
            face.message = "Face check needs interaction. Use your password."
        }
    }
    Timer {
        id: deadline
        interval: 6000
        onTriggered: {
            face.cancel()
            face.message = "Face check timed out. Use your password."
        }
    }
}
