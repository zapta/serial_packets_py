# Unit tests of PacketEncoder

import unittest
import sys

# Assuming VSCode project opened at repo directory
sys.path.insert(0, "./src")

from serial_packets._packet_encoder import PacketEncoder


class TestPacketEncoder(unittest.TestCase):

    def test_byte_stuffing(self):
        e = PacketEncoder()
        bytes = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        # With pre packet flag.
        stuffed = e._PacketEncoder__byte_stuffing(bytes, True)
        self.assertCountEqual(
            stuffed, bytearray([0x7e, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99, 0x7e]))
        # Without pre packet flag.
        stuffed = e._PacketEncoder__byte_stuffing(bytes, False)
        self.assertCountEqual(stuffed,
                              bytearray([0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99, 0x7e]))


if __name__ == '__main__':
    unittest.main()
