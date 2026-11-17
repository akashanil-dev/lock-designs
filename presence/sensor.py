#!/usr/bin/python3
"""Event-driven reader for Lenovo's VL53L1_HOD, using Linux's existing driver.

The root service only operates the sensor and publishes measurements. It never
opens a camera, invokes a command, authenticates a user, or unlocks a session.
"""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import select
import signal
import socket
import struct
import sys
import time

HEADER = struct.Struct('<IQI')
PAYLOAD = struct.Struct('<BBIIQQibbH')
SOCKET = '/run/omarchy-presence/sensor.sock'


@dataclass(frozen=True)
class Sample:
    state: int
    distance_mm: int
    confidence: int
    presence: int

    def event(self):
        # Only firmware's ready state and boolean presence reports are usable.
        # Confidence is diagnostic: it naturally decays on an empty chair.
        valid = (self.state == 2 and self.presence in (0, 1)
                 and 0 <= self.confidence <= 100 and 0 <= self.distance_mm <= 65535)
        return {'version': 1, 'state': ('present' if self.presence else 'absent')
                if valid else 'unknown', 'distance_mm': self.distance_mm,
                'confidence': self.confidence, 'monotonic': time.monotonic()}


class Decoder:
    def __init__(self):
        self.pending = bytearray()

    def feed(self, data):
        self.pending.extend(data)
        if len(self.pending) > 8192:
            raise ValueError('sensor buffer limit exceeded')
        result = []
        while len(self.pending) >= HEADER.size:
            usage, timestamp, length = HEADER.unpack_from(self.pending)
            if usage != 0x2000e1 or length != PAYLOAD.size:
                raise ValueError('unsupported sensor report layout')
            if len(self.pending) < HEADER.size + length:
                break
            state, event, clock, custom, t1, t2, distance, confidence, presence, limit = (
                PAYLOAD.unpack_from(self.pending, HEADER.size))
            del self.pending[:HEADER.size + length]
            result.append(Sample(state, distance, confidence, presence))
        return result


def decode_string(path):
    return bytes(map(int, path.read_text().split())).split(b'\0')[0].decode('ascii')


def descriptor_layout(data):
    """Extract HID input field widths; sysfs omits each field's report count."""
    offset, globals_, stack, usages, logical, reports = 0, {}, [], [], 0, {}
    while offset < len(data):
        prefix = data[offset]
        offset += 1
        if prefix == 0xfe:
            raise ValueError('unsupported HID long item')
        size = (0, 1, 2, 4)[prefix & 3]
        kind, tag = (prefix >> 2) & 3, prefix >> 4
        if offset + size > len(data):
            raise ValueError('truncated HID descriptor')
        value = int.from_bytes(data[offset:offset + size], 'little')
        offset += size
        if kind == 1:
            if tag == 10:
                stack.append(globals_.copy())
            elif tag == 11:
                if not stack:
                    raise ValueError('invalid HID global stack')
                globals_ = stack.pop()
            else:
                globals_[tag] = value
        elif kind == 2 and tag == 0:
            usages.append(value if size == 4 else (globals_.get(0, 0) << 16) | value)
        elif kind == 0:
            if tag == 8:
                reports.setdefault(globals_.get(8, 0), []).append(
                    (usages[0] if usages else 0, globals_.get(7, 0), globals_.get(9, 0)))
            usages = []
    return reports


def discover():
    matches = []
    for path in Path('/sys/bus/platform/devices').glob('HID-SENSOR-2000e1.*'):
        model = next(path.glob('feature-*-200306/*-value'), None)
        maker = next(path.glob('feature-*-200305/*-value'), None)
        if not model or not maker:
            continue
        if decode_string(model) != 'VL53L1_HOD' or decode_string(maker) != 'ST_MICRO':
            continue
        reports = descriptor_layout((path.resolve().parent / 'report_descriptor').read_bytes())
        expected = [(0x200800, 8, 1), (0x200810, 8, 1), (0x20055f, 32, 1),
                    (0x20055e, 32, 1), (0x200529, 32, 2), (0x20052b, 32, 2),
                    (0x200544, 32, 1), (0x200545, 8, 1), (0x2004b1, 8, 1),
                    (0x200541, 16, 1)]
        if expected not in reports.values():
            raise ValueError('VL53L1_HOD report descriptor differs from the tested layout')
        matches.append(path)
    if len(matches) != 1:
        raise ValueError(f'expected one supported presence sensor; found {len(matches)}')
    return matches[0]


def unknown(reason):
    return {'version': 1, 'state': 'unknown', 'reason': reason, 'monotonic': time.monotonic()}


def serve(uid, seconds=0):
    if os.geteuid() != 0:
        raise PermissionError('sensor activation requires the root-owned system service')
    sensor = discover()
    enable = sensor / 'enable_sensor'
    if enable.read_text().strip() != '0':
        raise RuntimeError('sensor already enabled; refusing to take ownership')
    fd = os.open('/dev/' + sensor.name, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    server = None
    clients = []
    activated = False
    decoder = Decoder()
    latest = unknown('starting')
    started = last = time.monotonic()
    last_health = started
    def publish(event):
        message = (json.dumps(event, separators=(',', ':')) + '\n').encode()
        if seconds:
            print(message.decode().strip(), flush=True)
        for client in clients[:]:
            try:
                if client.send(message) != len(message):
                    raise OSError('slow subscriber')
            except OSError:
                clients.remove(client)
                client.close()
    try:
        if not seconds:
            directory = Path(SOCKET).parent
            directory.mkdir(mode=0o755, exist_ok=True)
            if directory.stat().st_uid != 0 or directory.stat().st_mode & 0o022:
                raise PermissionError('unsafe socket directory')
            Path(SOCKET).unlink(missing_ok=True)
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(SOCKET)
            os.chmod(SOCKET, 0o600)
            os.chown(SOCKET, uid, -1)
            server.listen(4)
            server.setblocking(False)
        if seconds:
            enable.write_text('1\n')
            activated = True
            print('VL53L1_HOD enabled; waiting for kernel events', file=sys.stderr, flush=True)
        while not seconds or time.monotonic() - started < seconds:
            if not seconds and not clients and activated:
                enable.write_text('0\n')
                activated = False
                decoder = Decoder()
                latest = unknown('no subscribers')
            readers = ([fd] if activated else []) + ([server] if server else []) + clients
            ready, _, _ = select.select(readers, [], [], 3 if activated else None)
            now = time.monotonic()
            if server in ready:
                client, _ = server.accept()
                pid, peer_uid, gid = struct.unpack('3i', client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if peer_uid not in (0, uid) or len(clients) >= 4:
                    client.close()
                else:
                    client.setblocking(False)
                    clients.append(client)
                    if not activated:
                        # Discard reports buffered before the previous shutdown.
                        while True:
                            try:
                                if not os.read(fd, 4096): break
                            except BlockingIOError:
                                break
                        enable.write_text('1\n')
                        activated = True
                        last = last_health = now
                    publish(latest)
            # Subscribers receive measurements only; incoming bytes or an EOF
            # close that connection. No privileged request protocol exists.
            for client in clients[:]:
                if client in ready:
                    clients.remove(client)
                    client.close()
            if fd in ready:
                data = os.read(fd, 4096)
                if not data:
                    raise OSError('sensor disconnected')
                for sample in decoder.feed(data):
                    latest = sample.event()
                    last = now
                    publish(latest)
            # The firmware goes quiet when absent. A synchronous input request
            # every three quiet seconds validates it and causes a full report
            # through the kernel character device, without a userspace spin.
            if activated and now - last >= 3 and now - last_health >= 3:
                field = next(sensor.glob('input-*-2004b1/*-value'))
                field.read_text()
                last_health = now
            if activated and now - last > 12:
                publish(unknown('sensor unresponsive'))
                raise OSError('sensor stopped responding to input requests')
    finally:
        publish(unknown('stopped'))
        for client in clients:
            client.close()
        if server:
            server.close()
            Path(SOCKET).unlink(missing_ok=True)
        os.close(fd)
        if activated:
            enable.write_text('0\n')
        print('Sensor restored to disabled', file=sys.stderr, flush=True)


def stream():
    """Unprivileged bridge: blocking socket reads, no timers while connected."""
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(SOCKET)
                # The peer must be the privileged sensor publisher.
                if struct.unpack('3i', sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1] != 0:
                    raise PermissionError('sensor publisher is not root')
                pending = b''
                while True:
                    data = sock.recv(4096)
                    if not data:
                        raise ConnectionError('sensor publisher stopped')
                    pending += data
                    if len(pending) > 8192:
                        raise ValueError('sensor publisher exceeded message limit')
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        event = json.loads(line)
                        if event.get('version') != 1 or event.get('state') not in ('present', 'absent', 'unknown'):
                            raise ValueError('invalid sensor event')
                        print(json.dumps(event), flush=True)
        except (OSError, ValueError) as error:
            print(json.dumps(unknown(type(error).__name__)), flush=True)
            time.sleep(3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['serve', 'stream', 'probe', 'discover'])
    parser.add_argument('--uid', type=int, default=1000)
    parser.add_argument('--seconds', type=int, default=30)
    args = parser.parse_args()
    if args.uid < 1000 or not 1 <= args.seconds <= 180:
        parser.error('invalid uid or diagnostic duration')
    def terminate(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    if args.mode == 'discover':
        print(discover())
    elif args.mode == 'stream':
        stream()
    else:
        try:
            serve(args.uid, args.seconds if args.mode == 'probe' else 0)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
