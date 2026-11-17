// SPDX-License-Identifier: MIT
// Presence requests authentication; it can never authorize an unlock.
function createPolicy() {
    return {sampleAt: null, presence: "unknown", seenPresent: false,
            absentAt: null, away: false, lockIssued: false, wasLocked: false};
}

function advance(p, now, reading, locked, config) {
    var actions = [];
    if (!config.enabled) {
        return {policy: createPolicy(), actions: []};
    }
    // A time jump/suspend invalidates old absence deadlines and arrival edges.
    if (p.sampleAt !== null && (now < p.sampleAt || now - p.sampleAt > 4500)) {
        p = createPolicy();
        actions.push("cancelFace");
    }
    if (!locked && p.wasLocked) {
        p.away = false;
        p.absentAt = null;
        p.lockIssued = false;
        p.seenPresent = false;
    }
    p.wasLocked = locked;
    if (reading) {
        p.sampleAt = now;
        var state = reading.state;
        var reliableArrival = state === "present" && reading.confidence >= 50 && reading.distance_mm < 1500;
        if (state !== "present" && state !== "absent") {
            p.presence = "unknown";
            p.absentAt = null;
            p.away = false;
            p.seenPresent = false;
            p.lockIssued = false;
            actions.push("cancelFace");
        } else if (state === "present") {
            // Firmware can briefly assert present while distance is saturated.
            // Do not spend the single arrival attempt on that transitional frame.
            if (locked && p.away && config.faceEnabled && reliableArrival) actions.push("authenticate");
            p.presence = "present";
            p.absentAt = null;
            if (reliableArrival) p.away = false;
            p.lockIssued = false;
            if (reliableArrival) p.seenPresent = true;
        } else {
            if (p.presence !== "absent") actions.push("cancelFace");
            p.presence = "absent";
            if (p.absentAt === null) p.absentAt = now;
        }
    }
    if (p.presence === "absent" && p.absentAt !== null) {
        if (now - p.absentAt >= 2000) p.away = true;
        if (!locked && p.seenPresent && !p.lockIssued &&
                now - p.absentAt >= config.awaySeconds * 1000) {
            actions.push("lock");
            p.lockIssued = true;
        }
    }
    return {policy: p, actions: actions};
}

if (typeof module !== "undefined") module.exports = {createPolicy: createPolicy, advance: advance};
