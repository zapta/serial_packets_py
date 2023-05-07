# Unit tests of PacketDecoder

import unittest
import sys

# Assuming VSCode project opened at repo directory
sys.path.insert(0, "./src")

from serial_packets._packet_decoder import PacketDecoder, DecodedCommandPacket, DecodedResponsePacket, DecodedMessagePacket


class TestPacketEncoder(unittest.TestCase):

    def setUp(self):
        self.packets = []

    def packet_callback(
            self,
            packet: DecodedCommandPacket | DecodedResponsePacket | DecodedMessagePacket) -> None:
        print(f"Callback got a packet: {packet}")
        self.packets.append(packet)

    def test_first_packet_no_pre_flag(self):
        """Tests that the decoder requires an initial packet flag."""
        d = PacketDecoder(self.packet_callback)
        d.receive(bytes([0x03, 0x20, 0x11, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0xa9, 0xe0, 0x7e]))
        self.assertEqual(len(self.packets), 0)
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertTrue(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)

    def test_command_packet(self):
        """Tests decoding of a command packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(
            bytes([
                0x7e, 0x01, 0xff, 0x12, 0x34, 0x56, 0x20, 0x11, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0xbc,
                0x7d, 0x5d, 0x7e
            ]))
        self.assertEqual(len(self.packets), 1)
        packet: DecodedCommandPacket = self.packets[0]
        self.assertIsInstance(packet, DecodedCommandPacket)
        self.assertEqual(packet.cmd_id, 0xff123456)
        self.assertEqual(packet.endpoint, 0x20)
        # print(f"Actual: 0x{packet.data.bytes().hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(packet.data.data_bytes(), bytearray([0x11, 0x7e, 0x22, 0x7d]))
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertTrue(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)

    def test_response_packet(self):
        """Tests decoding of a response packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(
            bytes([
                0x7e, 0x02, 0xff, 0x12, 0x34, 0x56, 0x20, 0x11, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x0d,
                0xb2, 0x7e
            ]))
        self.assertEqual(len(self.packets), 1)
        packet: DecodedResponsePacket = self.packets[0]
        self.assertIsInstance(packet, DecodedResponsePacket)
        self.assertEqual(packet.cmd_id, 0xff123456)
        self.assertEqual(packet.status, 0x20)
        # print(f"Actual: 0x{packet.data.bytes().hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(packet.data.data_bytes(), bytearray([0x11, 0x7e, 0x22, 0x7d]))
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertTrue(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)

    def test_message_packet(self):
        """Tests decoding of a message packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(bytes([0x7e, 0x03, 0x20, 0x11, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0xa9, 0xe0, 0x7e]))
        self.assertEqual(len(self.packets), 1)
        packet: DecodedMessagePacket = self.packets[0]
        self.assertIsInstance(packet, DecodedMessagePacket)
        self.assertEqual(packet.endpoint, 0x20)
        # print(f"Actual: 0x{packet.data.bytes().hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(packet.data.data_bytes(), bytearray([0x11, 0x7e, 0x22, 0x7d]))
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertTrue(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)

    def test_packet_bad_crc(self):
        """Tests decoding of a message packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(bytes([0x7e, 0x03, 0x20, 0x11, 0x7d, 0x5e, 0x23, 0x7d, 0x5d, 0xa9, 0xe0, 0x7e]))
        self.assertEqual(len(self.packets), 0)
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertTrue(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)


if __name__ == '__main__':
    unittest.main()
