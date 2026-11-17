# Attribution

The new sensor publisher, presence policy, integration components, and local
setup tools were implemented for Akash A. Existing projects remain credited.

- **Gaze — Gundu Labs and contributors**, GPL-3.0-or-later:
  https://github.com/GunduLabs/gaze. Used as an unmodified separate authentication
  backend, version 0.5.1. Its IR emitter detection/control implementation informed
  the bounded hardware diagnostic. Gaze supplies recognition, liveness, encryption,
  enrollment, and PAM; this project does not claim authorship of those features.
  Its models have their own upstream licenses.
- **Lock Designs — Jean Alvarado**, MIT:
  https://github.com/SmoothPixels/lock-designs. The installed user's
  existing customized lock host is retained, with a small local integration.
  Its original LICENSE and existing authorship are preserved in its directory.
- **Omarchy — David Heinemeier Hansson and contributors**, MIT:
  https://github.com/omacom/omarchy. Provides the shell, session lock, theme,
  existing password lane, and plugin framework.
- **Face Unlock for Omarchy — Kosta Hantzis**, MIT:
  https://github.com/therealasclepius/omarchy-face-unlock. Its separate cancellable
  PAM lane and late-completion guards informed FaceAuthenticator.qml. Its existing
  upstream Omarchy copyright is retained in the license notice below.
- **Linux HID sensor framework — Linux/Intel contributors**, GPL-2.0-only source:
  https://docs.kernel.org/hid/hid-sensor.html and
  https://github.com/torvalds/linux/blob/master/drivers/hid/hid-sensor-custom.c.
  The existing kernel interface and report framing are used; no kernel source
  was incorporated into the runtime Python implementation.
- **PJungkamp/yoga9-linux**, MIT:
  https://github.com/PJungkamp/yoga9-linux/tree/main/intel-ish/read-hid-sensor.
  Its research on Lenovo's human-presence reports helped identify distance,
  confidence, and presence fields. The implementation validates this laptop's
  actual HID descriptor and decodes its reports independently.
- **Facelock — tyvsmith and contributors**, MIT OR Apache-2.0:
  https://github.com/tyvsmith/facelock. Evaluated as an alternative backend, not
  installed or used by the final integration.

## MIT notices for the existing lock implementation and PAM design

Copyright (c) David Heinemeier Hansson
Copyright (c) 2026 Jean Alvarado
Copyright (c) 2026 Kosta Hantzis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
