from __future__ import annotations

import logging
import time

from PyCRC.CRCCCITT import CRCCCITT
from ._packets import PacketType, PACKET_START_FLAG, PACKET_END_FLAG, PACKET_ESC, MAX_DATA_LEN, MAX_PACKET_LEN

logger = logging.getLogger(__name__)


class PacketEncoder:

    def __init__(self):
        # self.__last_packet_time = 0
        self.__crc_calc = CRCCCITT("FFFF")

    def __construct_command_packet(self, cmd_id: int, endpoint: int, data: bytearray):
        """Constructs a command packet, before byte stuffing"""
        packet = bytearray()
        packet.append(PacketType.COMMAND.value)
        packet.extend(cmd_id.to_bytes(4, 'big'))
        packet.append(endpoint)
        packet.extend(data)
        crc = self.__crc_calc.calculate(bytes(packet))
        packet.extend(crc.to_bytes(2, 'big'))
        assert (len(packet) <= MAX_PACKET_LEN)
        return packet

    def __construct_response_packet(self, cmd_id: int, status: int, data: bytearray):
        """Constructs a response packet, before byte stuffing"""
        packet = bytearray()
        packet.append(PacketType.RESPONSE.value)
        packet.extend(cmd_id.to_bytes(4, 'big'))
        packet.append(status)
        packet.extend(data)
        crc = self.__crc_calc.calculate(bytes(packet))
        packet.extend(crc.to_bytes(2, 'big'))
        assert (len(packet) <= MAX_PACKET_LEN)
        return packet

    def __construct_message_packet(self, endpoint: int, data: bytearray):
        """Constructs a message packet, before byte stuffing"""
        packet = bytearray()
        packet.append(PacketType.MESSAGE.value)
        packet.append(endpoint)
        packet.extend(data)
        crc = self.__crc_calc.calculate(bytes(packet))
        packet.extend(crc.to_bytes(2, 'big'))
        assert (len(packet) <= MAX_PACKET_LEN)
        return packet

    def __byte_stuffing(self, packet: bytearray):
        """Byte stuff the packet using HDLC format. Also adds packet flag(s)"""
        result = bytearray()
        result.append(PACKET_START_FLAG)
        for byte in packet:
            if byte == PACKET_START_FLAG or byte == PACKET_END_FLAG or byte == PACKET_ESC:
                result.append(PACKET_ESC)
                result.append(byte ^ 0x20)
            else:
                result.append(byte)
        result.append(PACKET_END_FLAG)
        return result

    def encode_command_packet(self, cmd_id: int, endpoint: int, data: bytearray):
        """Returns the command packet in wire format"""
        assert (len(data) <= MAX_DATA_LEN)
        packet = self.__construct_command_packet(cmd_id, endpoint, data)
        stuffed_packet = self.__byte_stuffing(packet)
        return stuffed_packet

    def encode_response_packet(self, cmd_id: int, status: int, data: bytearray):
        """Returns the packet in wire format."""
        assert (len(data) <= MAX_DATA_LEN)
        packet = self.__construct_response_packet(cmd_id, status, data)
        stuffed_packet = self.__byte_stuffing(packet)
        return stuffed_packet

    def encode_message_packet(self, endpoint: int, data: bytearray):
        """Returns the message packet in wire format"""
        assert (len(data) <= MAX_DATA_LEN)
        packet = self.__construct_message_packet(endpoint, data)
        stuffed_packet = self.__byte_stuffing(packet)
        return stuffed_packet
