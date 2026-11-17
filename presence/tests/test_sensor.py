import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sensor import Decoder, HEADER, PAYLOAD, Sample, descriptor_layout, discover


def report(presence=1, confidence=98, distance=450, state=2):
    return HEADER.pack(0x2000e1, 123, 34) + PAYLOAD.pack(state, 6, 10, 8, 20, 30, distance, confidence, presence, 550)


class SensorTest(unittest.TestCase):
    def test_partial_and_concatenated_reports(self):
        decoder = Decoder()
        data = report() + report(0, 0, 0)
        decoded = []
        for byte in data:
            decoded.extend(decoder.feed(bytes([byte])))
        self.assertEqual([r.presence for r in decoded], [1, 0])
        self.assertEqual(decoded[0].distance_mm, 450)

    def test_malformed_length_is_not_trusted(self):
        with self.assertRaises(ValueError):
            Decoder().feed(HEADER.pack(0x2000e1, 0, 2**32 - 1))

    def test_wrong_sensor_is_rejected(self):
        with self.assertRaises(ValueError):
            Decoder().feed(HEADER.pack(0x200041, 0, 34))

    def test_invalid_firmware_reading_is_unknown(self):
        for sample in [Sample(0, 400, 100, 1), Sample(2, 400, -1, 1), Sample(2, 400, 100, -1)]:
            self.assertEqual(sample.event()['state'], 'unknown')

    def test_empty_room_zero_confidence_is_valid(self):
        self.assertEqual(Sample(2, 0, 0, 0).event()['state'], 'absent')

    def test_report_buffer_is_bounded(self):
        with self.assertRaises(ValueError):
            Decoder().feed(b'\0' * 8193)

    def test_descriptor_rejects_truncation(self):
        with self.assertRaises(ValueError):
            descriptor_layout(bytes([0x77, 0x01]))

    def test_live_descriptor_matches_explicitly_supported_hardware(self):
        self.assertEqual(discover().name, 'HID-SENSOR-2000e1.4.auto')


if __name__ == '__main__':
    unittest.main()
