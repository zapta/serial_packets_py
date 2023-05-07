from __future__ import annotations

import logging
import time

from PyCRC.CRCCCITT import CRCCCITT
from .packets import PacketData
from ._packets import PacketType, PACKET_FLAG, PACKET_ESC, MAX_DATA_LEN, MAX_PACKET_LEN,  PRE_FLAG_TIMEOUT

logger = logging.getLogger(__name__)


class PacketEncoder:

    def __init__(self):
        self.__last_packet_time = 0
        self.__crc_calc = CRCCCITT("FFFF")

    def __construct_command_packet(self, cmd_id: int, endpoint: int, data: PacketData):
        """Constructs a command packet, before byte stuffing"""
        packet = bytearray()
        packet.append(PacketType.COMMAND.value)
        packet.extend(cmd_id.to_bytes(4, 'big'))
        packet.append(endpoint)
        packet.extend(data._internal_data_bytes())
        crc = self.__crc_calc.calculate(bytes(packet))
        packet.extend(crc.to_bytes(2, 'big'))
        assert (len(packet) <= MAX_PACKET_LEN)
        return packet

    def __construct_response_packet(self, cmd_id: int, status: int, data: PacketData):
        """Constructs a response packet, before byte stuffing"""
        packet = bytearray()
        packet.append(PacketType.RESPONSE.value)
        packet.extend(cmd_id.to_bytes(4, 'big'))
        packet.append(status)
        packet.extend(data._internal_data_bytes())
        crc = self.__crc_calc.calculate(bytes(packet))
        packet.extend(crc.to_bytes(2, 'big'))
        assert (len(packet) <= MAX_PACKET_LEN)
        return packet
      
    def __construct_message_packet(self, endpoint: int, data: PacketData):
        """Constructs a message packet, before byte stuffing"""
        packet = bytearray()
        packet.append(PacketType.MESSAGE.value)
        packet.append(endpoint)
        packet.extend(data._internal_data_bytes())
        crc = self.__crc_calc.calculate(bytes(packet))
        packet.extend(crc.to_bytes(2, 'big'))
        assert (len(packet) <= MAX_PACKET_LEN)
        return packet

    def __byte_stuffing(self, packet: bytearray, insert_pre_flag: bool):
        """Byte stuff the packet using HDLC format. Also adds packet flag(s)"""
        result = bytearray()
        if insert_pre_flag:
            result.append(PACKET_FLAG)
        for byte in packet:
            if byte == PACKET_FLAG or byte == PACKET_ESC:
                result.append(PACKET_ESC)
                result.append(byte ^ 0x20)
            else:
                result.append(byte)
        result.append(PACKET_FLAG)
        return result

    def __track_packet_interval(self):
        last_packet_time = self.__last_packet_time
        self.__last_packet_time = time.time()
        elapsed = self.__last_packet_time - last_packet_time
        # We insert a pre packet flag only if the packets are sparse.
        insert_pre_flag = elapsed > PRE_FLAG_TIMEOUT
        return insert_pre_flag

    def encode_command_packet(self, cmd_id: int, endpoint: int, data: PacketData):
        """Returns the command packet in wire format"""
        assert (data.size() <= MAX_DATA_LEN)
        insert_pre_flag = self.__track_packet_interval()
        packet = self.__construct_command_packet(cmd_id, endpoint, data)
        stuffed_packet = self.__byte_stuffing(packet, insert_pre_flag)
        return stuffed_packet

    def encode_response_packet(self, cmd_id: int, status: int, data: PacketData):
        """Returns the packet in wire format."""
        assert (data.size() <= MAX_DATA_LEN)
        insert_pre_flag = self.__track_packet_interval()
        packet = self.__construct_response_packet(cmd_id, status, data)
        stuffed_packet = self.__byte_stuffing(packet, insert_pre_flag)
        return stuffed_packet
      
    def encode_message_packet(self,  endpoint: int, data: PacketData):
        """Returns the message packet in wire format"""
        assert (data.size() <= MAX_DATA_LEN)
        insert_pre_flag = self.__track_packet_interval()
        packet = self.__construct_message_packet(endpoint, data)
        stuffed_packet = self.__byte_stuffing(packet, insert_pre_flag)
        return stuffed_packet  
 
