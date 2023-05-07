# Unit tests of PacketEncoder

import unittest
import sys

# Assuming VSCode project opened at repo directory
sys.path.insert(0, "./src")

from serial_packets._packet_encoder import PacketEncoder


class TestPacketEncoder(unittest.TestCase):

    def test_byte_stuffing_with_pre_flag(self):
        e = PacketEncoder()
        input = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        output = e._PacketEncoder__byte_stuffing(input, True)
        self.assertCountEqual(
            output, bytearray([0x7e, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99, 0x7e]))

    def test_byte_stuffing_no_pre_flag(self):
        e = PacketEncoder()
        input = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        output = e._PacketEncoder__byte_stuffing(input, False)
        self.assertCountEqual(output,
                              bytearray([0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99, 0x7e]))

    def test_construct_command_packet(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e._PacketEncoder__construct_command_packet(0x12345678, 0x20, data)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray([
                0x01, 0x12, 0x34, 0x56, 0x78, 0x20, 0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99, 0xd4, 0x80
            ]))

    def test_construct_response_packet(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e._PacketEncoder__construct_response_packet(0x12345678, 0x20, data)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray([
                0x02, 0x12, 0x34, 0x56, 0x78, 0x20, 0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99, 0xd1, 0x1f
            ]))

    def test_construct_message_packet(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e._PacketEncoder__construct_message_packet(0x20, data)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(packet,
                         bytearray([0x03, 0x20, 0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99, 0xa7, 0x1e]))

    def test_encode_command_packet_with_pre_flag(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e.encode_command_packet(0xff123456, 0x20, data, True)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray([
                0x7e, 0x01, 0xff, 0x12, 0x34, 0x56, 0x20, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d,
                0x99, 0x09, 0x8c, 0x7e
            ]))

    def test_encode_command_packet_no_pre_flag(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e.encode_command_packet(0xff123456, 0x20, data, False)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray([
                0x01, 0xff, 0x12, 0x34, 0x56, 0x20, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99,
                0x09, 0x8c, 0x7e
            ]))

    def test_encode_response_packet_with_pre_flag(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e.encode_response_packet(0xff123456, 0x20, data, True)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray([
                0x7e, 0x02, 0xff, 0x12, 0x34, 0x56, 0x20, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d,
                0x99, 0x0c, 0x13, 0x7e
            ]))

    def test_encode_response_packet_no_pre_flag(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e.encode_response_packet(0xff123456, 0x20, data, False)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray([
                0x02, 0xff, 0x12, 0x34, 0x56, 0x20, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99,
                0x0c, 0x13, 0x7e
            ]))

    def test_encode_message_packet_with_pre_flag(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e.encode_message_packet(0x20, data, True)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray([
                0x7e, 0x03, 0x20, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99, 0xa7, 0x1e, 0x7e
            ]))

    def test_encode_message_packet_no_pre_flag(self):
        e = PacketEncoder()
        data = bytearray([0xff, 0x00, 0x7e, 0x22, 0x7d, 0x99])
        packet = e.encode_message_packet(0x20, data, False)
        # print(f"Actual: 0x{packet.hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(
            packet,
            bytearray(
                [0x03, 0x20, 0xff, 0x00, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99, 0xa7, 0x1e, 0x7e]))


if __name__ == '__main__':
    unittest.main()
