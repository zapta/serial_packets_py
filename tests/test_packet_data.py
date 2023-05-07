# Unit tests of PacketData

import unittest
import sys

# Assuming VSCode project opened at repo directory
sys.path.insert(0, "./src")

from serial_packets.packets import PacketData


class TestPacketData(unittest.TestCase):

    def test_constructor(self):
        d = PacketData()
        self.assertEqual(d.size(), 0)
        self.assertEqual(d.bytes_read(), 0)
        self.assertEqual(d.bytes_availale_to_read(), 0)
        self.assertTrue(d.all_read())

    def test_add_byte(self):
        d = PacketData()
        d.add_byte(0x02)
        self.assertEqual(d.size(), 1)
        self.assertEqual(d.bytes(), bytearray([0x2]))
        self.assertEqual(d.bytes_read(), 0)

    def test_add_uint16(self):
        d = PacketData()
        d.add_uint16(0xff34)
        self.assertEqual(d.size(), 2)
        self.assertEqual(d.bytes(), bytearray([0xff, 0x34]))
        self.assertEqual(d.bytes_read(), 0)

    def test_add_uint32(self):
        d = PacketData()
        d.add_uint32(0xff345678)
        self.assertEqual(d.size(), 4)
        self.assertEqual(d.bytes(), bytearray([0xff, 0x34, 0x56, 0x78]))
        self.assertEqual(d.bytes_read(), 0)

    def test_add_bytes(self):
        d = PacketData()
        d.add_bytes(bytearray([0xff, 0x11, 0x22, 0x33, 0x44]))
        self.assertEqual(d.size(), 5)
        self.assertEqual(d.bytes(), bytearray([0xff, 0x11, 0x22, 0x33, 0x44]))
        self.assertEqual(d.bytes_read(), 0)

    def test_read_byte(self):
        d = PacketData()
        d.add_bytes(bytearray([0xfe, 0x11]))
        v = d.read_byte()
        self.assertEqual(v, 0xfe)
        self.assertEqual(d.bytes_read(), 1)

    def test_read_uint16(self):
        d = PacketData()
        d.add_bytes(bytearray([0xfe, 0x11, 0x12]))
        v = d.read_uint16()
        self.assertEqual(v, 0xfe11)
        self.assertEqual(d.bytes_read(), 2)

    def test_read_uint32(self):
        d = PacketData()
        d.add_bytes(bytearray([0xfe, 0x11, 0x22, 0x33]))
        v = d.read_uint32()
        self.assertEqual(v, 0xfe112233)
        self.assertEqual(d.bytes_read(), 4)

    def test_read_uint32(self):
        d = PacketData()
        d.add_bytes(bytearray([0x11, 0x22, 0x33]))
        v = d.read_bytes(3)
        self.assertEqual(v, bytearray([0x11, 0x22, 0x33]))
        self.assertEqual(d.bytes_read(), 3)

    def test_hex_string(self):
        d = PacketData()
        d.add_bytes(bytearray([0xa1, 0xb2, 0xc3]))
        self.assertEqual(d.hex_str(), "a1 b2 c3")


if __name__ == '__main__':
    unittest.main()
