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

   

    def test_decode_command_packet(self):
        """Tests decoding of a command packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(
            bytes([
                0x7c, 0x01, 0xff, 0x12, 0x34, 0x56, 0x20, 0xff, 0x00, 0x7d, 0x5c, 0x11, 0x7d, 0x5e,
                0x22, 0x7d, 0x5d, 0x99, 0x7a, 0xa7, 0x7e
            ]))
        self.assertEqual(len(self.packets), 1)
        packet: DecodedCommandPacket = self.packets[0]
        self.assertIsInstance(packet, DecodedCommandPacket)
        self.assertEqual(packet.cmd_id, 0xff123456)
        self.assertEqual(packet.endpoint, 0x20)
        # print(f"Actual: 0x{packet.data.data_bytes().hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(packet.data.data_bytes(), bytearray([0xff, 0x00, 0x7c, 0x11, 0x7e, 0x22, 0x7d, 0x99]))
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertFalse(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)

    def test_decode_response_packet(self):
        """Tests decoding of a response packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(
            bytes([
                 0x7c, 0x02, 0xff, 0x12, 0x34, 0x56, 0x20, 0xff, 0x00, 0x7d, 0x5c, 0x11, 0x7d, 0x5e,
                0x22, 0x7d, 0x5d, 0x99, 0xf7, 0x04, 0x7e
            ]))
        self.assertEqual(len(self.packets), 1)
        packet: DecodedResponsePacket = self.packets[0]
        self.assertIsInstance(packet, DecodedResponsePacket)
        self.assertEqual(packet.cmd_id, 0xff123456)
        self.assertEqual(packet.status, 0x20)
        # print(f"Actual: 0x{packet.data.data_bytes().hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(packet.data.data_bytes(), bytearray([0xff, 0x00, 0x7c, 0x11, 0x7e, 0x22, 0x7d, 0x99]))
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertFalse(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)

    def test_decode_message_packet(self):
        """Tests decoding of a message packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(bytes([0x7c, 0x03, 0x20, 0xff, 0x00, 0x7d, 0x5c, 0x11, 0x7d, 0x5e, 0x22, 0x7d, 0x5d, 0x99,
                0xe7, 0x2d, 0x7e]))
        self.assertEqual(len(self.packets), 1)
        packet: DecodedMessagePacket = self.packets[0]
        self.assertIsInstance(packet, DecodedMessagePacket)
        self.assertEqual(packet.endpoint, 0x20)
        # print(f"Actual: 0x{packet.data.data_bytes().hex(sep='#').replace('#', ', 0x')}")
        self.assertEqual(packet.data.data_bytes(), bytearray([0xff, 0x00, 0x7c, 0x11, 0x7e, 0x22, 0x7d, 0x99]))
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertFalse(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)

    def test_decode_packet_bad_crc(self):
        """Tests decoding of a packet with bad CRC."""
        d = PacketDecoder(self.packet_callback)
        # Usign the packet from the command test above but with the second crc byte modified (a7 -> aa).
        d.receive(bytes([0x7c, 0x01, 0xff, 0x12, 0x34, 0x56, 0x20, 0xff, 0x00, 0x7d, 0x5c, 0x11, 0x7d, 0x5e,
                0x22, 0x7d, 0x5d, 0x99, 0x7a, 0xaa, 0x7e]))
        self.assertEqual(len(self.packets), 0)
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 0)
        self.assertFalse(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)
        
    def test_partial_packet_error(self):
        """Tests the scenario where a start flag appears mid packet."""
        d = PacketDecoder(self.packet_callback)
        d.receive(bytes([0x7c, 0x01, 0x7d]))
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 1)
        self.assertTrue(d._PacketDecoder__in_packet)
        self.assertTrue(d._PacketDecoder__pending_escape)
        d.receive(bytes([0x7c, 0x03, 0x04, 0x05]))
        self.assertEqual(len(self.packets), 0)
        self.assertEqual(len(d._PacketDecoder__packet_bfr), 3)
        self.assertTrue(d._PacketDecoder__in_packet)
        self.assertFalse(d._PacketDecoder__pending_escape)


if __name__ == '__main__':
    unittest.main()
