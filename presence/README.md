# Optional presence and face authentication

The plugin root contains `PresencePolicy.js`, `PresenceController.qml`, and `FaceAuthenticator.qml`. This directory preserves the separate sensor publisher and settings CLI used with those components. These are host-specific integration sources, not a universal face-unlock installer.

## Verified hardware and dependencies

Tested with Lenovo Yoga Slim 6 14IAP8 (82WU), the ST VL53L1_HOD sensor exposed by Linux `hid-sensor-custom`, and Chicony 04f2:b756 infrared camera. `sensor.py` validates the supported HID report descriptor and refuses unsupported devices. It publishes bounded numerical events on a local socket; it performs no authentication.

The configured host uses Gaze 0.5.1 with its IR camera and illuminator, encrypted enrollment, and liveness enabled. Gaze is a separate, unmodified dependency; its code, models, and biometric templates are not bundled. Gaze 0.5.2 required a newer OpenCV ABI than this host had at setup; reassess current packages before installing elsewhere. Do not bypass dependency checks.

Required runtime locations:

- `/usr/local/lib/omarchy-presence/sensor.py`
- `/usr/local/bin/omarchy-presence`
- `omarchy-presence-sensor.service`
- `/etc/pam.d/omarchy-presence-face`, an isolated face-only PAM service using `pam_gaze.so`
- `~/.config/omarchy/presence.json`, owned by the desktop user

`install_system.py` records the reviewed host-specific system installation. It requires root, refuses an existing installation, and does not install Gaze. The included service is configured for UID **1000**; review and adapt it for a different account. It does not enable services for future boots. Do not rerun it on the already configured host.

A new installation should begin with presence and face disabled, without claiming calibration:

```json
{"enabled": false, "calibrated": false, "face_enabled": false, "away_seconds": 30}
```

Only mark calibration complete after testing seated positions, walking away, and returning with numerical sensor observations. Verify Gaze enrollment, the isolated PAM lane, and password fallback before enabling automatic authentication. Do not modify shared password, login, sudo, or polkit PAM stacks for this integration.

## Behaviour and settings

```sh
omarchy-presence status
omarchy-presence settings --away-seconds 30
omarchy-presence settings --presence off
omarchy-presence settings --face off
omarchy-presence watch
```

Delay range: 5–300 seconds after firmware-confirmed absence. The original configured host uses 15 seconds. Presence cancels the countdown. Returning after sustained absence triggers one bounded face attempt; password typing cancels it. Manually locking while seated does not immediately start face authentication. Sensor failures and stale events cancel automatic actions. Presence is not identity or gaze detection.

The sensor is powered only while subscribers are connected. Gaze keeps its models warm but releases capture and illumination after authentication. The integration does not configure firmware wake-from-suspend. Physical reboot/suspend and broader seated-position testing remain necessary; successful local walk-away tests do not establish Windows Hello-equivalent security.

## Checks

From the repository root:

```sh
node --test tests/policy.test.cjs
python -m unittest discover -s presence/tests -v
/usr/lib/qt6/bin/qmllint -I /usr/share/omarchy/shell -I /usr/lib/qt6/qml FaceAuthenticator.qml PresenceController.qml
```

The Python suite includes a live descriptor check and therefore requires the supported laptop. Tests and diagnostics contain no enrolled face templates. Attribution is in the repository’s `THIRD_PARTY_NOTICES.md`.
