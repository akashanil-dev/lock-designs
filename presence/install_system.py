#!/usr/bin/python3
"""Install the sensor publisher and isolated face PAM lane, without enabling UI."""
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PAM = '''#%PAM-1.0
# Omarchy Presence: face-only lane. Password stays in omarchy-lock-password.
auth requisite pam_faillock.so preauth
auth sufficient pam_gaze.so
auth required pam_deny.so
account include system-local-login
'''

def main():
    if os.geteuid() != 0: raise SystemExit('Run through pkexec or sudo')
    target = Path('/usr/local/lib/omarchy-presence')
    pam = Path('/etc/pam.d/omarchy-presence-face')
    if target.exists() or pam.exists(): raise SystemExit('Already installed; review before replacing existing files')
    if not Path('/usr/lib/security/pam_gaze.so').exists(): raise SystemExit('Gaze PAM module missing')
    target.mkdir(parents=True, mode=0o755)
    shutil.copyfile(ROOT/'sensor.py',target/'sensor.py');os.chmod(target/'sensor.py',0o644)
    shutil.copyfile(ROOT/'omarchy-presence','/usr/local/bin/omarchy-presence')
    os.chmod('/usr/local/bin/omarchy-presence',0o755)
    shutil.copyfile(ROOT/'omarchy-presence-sensor.service','/etc/systemd/system/omarchy-presence-sensor.service')
    os.chmod('/etc/systemd/system/omarchy-presence-sensor.service',0o644)
    pam.write_text(PAM);os.chmod(pam,0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','start','omarchy-presence-sensor.service'],check=True)
    print('Sensor service started; hardware stays off until a subscriber connects. UI remains disabled.')

if __name__ == '__main__': main()
