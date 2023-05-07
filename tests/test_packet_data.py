import unittest

import sys
# import os

# print(f"*** { os.getcwd()}")

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
        d.add_byte(0x01)
        self.assertEqual(d.size(), 1)
        self.assertEqual(d.bytes(), bytearray([0x1]))
        d.add_byte(0x02)
        self.assertEqual(d.size(), 2)
        self.assertEqual(d.bytes(), bytearray([0x1, 0x2]))
        self.assertEqual(d.bytes_read(), 0)


if __name__ == '__main__':
    unittest.main()
