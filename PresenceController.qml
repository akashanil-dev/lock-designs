// SPDX-License-Identifier: MIT
import QtQuick
import Quickshell
import Quickshell.Io
import "PresencePolicy.js" as Policy

Item {
    id: presence
    required property var host
    required property var face
    property bool presenceEnabled: false
    property bool calibrated: false
    property bool faceEnabled: false
    property int awaySeconds: 30
    property string sensorState: "unknown"
    property int distanceMm: 0
    property int confidence: 0
    property var policy: Policy.createPolicy()
    property string lastAction: "none"
    readonly property bool active: presenceEnabled && calibrated
    onActiveChanged: {
        sensor.running = active
        if (!active) {
            retry.stop()
            freshness.stop()
            sensorState = "unknown"
            policy = Policy.createPolicy()
            face.cancel()
        }
    }

    function consume(event) {
        if (!event || event.version !== 1 || ["present", "absent", "unknown"].indexOf(event.state) < 0) return
        if (event.state !== "unknown" &&
            (!Number.isFinite(event.distance_mm) || !Number.isFinite(event.confidence))) return
        sensorState = event.state
        distanceMm = event.distance_mm || 0
        confidence = event.confidence || 0
        if (event.state !== "unknown") freshness.restart()
        var result = Policy.advance(policy, Date.now(), event, host.locked,
            {enabled: active, faceEnabled: faceEnabled, awaySeconds: awaySeconds})
        policy = result.policy
        result.actions.forEach(function(action) {
            lastAction = action
            if (action === "cancelFace") face.cancel()
            else if (action === "lock") {
                if (!host.beginLock()) lastAction = "lock-unavailable"
                else host.logEvent("presence-away-lock")
            } else if (action === "authenticate") {
                if (!face.start()) lastAction = "face-unavailable"
            }
        })
    }
    function settings() {
        try {
            let data = JSON.parse(configuration.text())
            let delay = Number(data.away_seconds)
            presenceEnabled = data.enabled === true
            calibrated = data.calibrated === true
            faceEnabled = data.face_enabled === true
            awaySeconds = Number.isFinite(delay) ? Math.max(5, Math.min(300, Math.round(delay))) : 30
            if (!active) {
                policy = Policy.createPolicy()
                face.cancel()
            }
        } catch(error) {
            presenceEnabled = false
            faceEnabled = false
            policy = Policy.createPolicy()
            face.cancel()
        }
    }
    FileView {
        id: configuration
        path: Quickshell.env("HOME") + "/.config/omarchy/presence.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: presence.settings()
        onLoadFailed: { presence.presenceEnabled = false; presence.faceEnabled = false; presence.face.cancel() }
    }
    Process {
        id: sensor
        command: ["/usr/bin/python3", "/usr/local/lib/omarchy-presence/sensor.py", "stream"]
        running: presence.active
        stdout: SplitParser {
            onRead: function(line) {
                if (line.length > 2048) return
                try { presence.consume(JSON.parse(line)) }
                catch(error) { presence.consume({version:1,state:"unknown"}) }
            }
        }
        onExited: {
            presence.consume({version:1,state:"unknown"})
            if (presence.active) retry.start()
        }
    }
    Timer {
        id: retry
        interval: 5000
        onTriggered: if (presence.active) sensor.running = true
    }
    Timer {
        id: freshness
        interval: 4500
        onTriggered: presence.consume({version:1,state:"unknown"})
    }
}
