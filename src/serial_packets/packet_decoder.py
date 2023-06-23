from __future__ import annotations

import logging
import asyncio
from PyCRC.CRCCCITT import CRCCCITT
from typing import Optional

from ._packets import PacketType, PACKET_START_FLAG, PACKET_END_FLAG, PACKET_ESC, MIN_PACKET_LEN, MAX_PACKET_LEN
from .packets import PacketData, MAX_DATA_LEN
# from .packets import  PACKET_MAX_LEN

logger = logging.getLogger(__name__)


class DecodedCommandPacket:

    def __init__(self, cmd_id: int, endpoint: int, data: PacketData):
        self.cmd_id: int = cmd_id
        self.endpoint: int = endpoint
        self.data: PacketData = data

    def __str__(self):
        return f"Command packet: {self.cmd_id}, {self.endpoint}, {self.data.size()}"


class DecodedResponsePacket:

    def __init__(self, cmd_id: int, status: int, data: PacketData):
        self.cmd_id: int = cmd_id
        self.status: int = status
        self.data: PacketData = data

    def __str__(self):
        return f"Response packet: {self.cmd_id}, {self.status}, {self.data.size()}"


class DecodedMessagePacket:

    def __init__(self, endpoint: int, data: PacketData):
        self.endpoint: int = endpoint
        self.data: PacketData = data

    def __str__(self):
        return f"Message packet: {self.endpoint}, {self.data.size()}"
      
      
class DecodedLogPacket:

    def __init__(self,  data: PacketData):
        self.data: PacketData = data

    def __str__(self):
        return f"Log packet: {self.data.size()}"


class PacketDecoder:

    def __init__(self):
        # assert (decoded_packet_callback is not None)
        self.__crc_calc = CRCCCITT("FFFF")
        self.__packet_bfr = bytearray()
        self.__in_packet = False
        self.__pending_escape = False
        # self.__decoded_packet_callback = decoded_packet_callback

    def __str__(self):
        return f"In_packet ={self.__in_packet}, pending_escape={self.__pending_escape}, len={len(self.__packet_bytes)}"

    def __reset_packet(self, in_packet: bool):
        self.__in_packet = in_packet
        self.__pending_escape = False
        self.__packet_bfr.clear()

   

    def receive_byte(
        self, b: int
    ) -> Optional(DecodedCommandPacket | DecodedResponsePacket
                  | DecodedMessagePacket):
        """ Returns a decoded packet or None."""
        # If not already in a packet, wait for next flag.
        if not self.__in_packet:
            if b == PACKET_START_FLAG:
                # Start collecting a packet.
                self.__reset_packet(True)
            else:
                # Here we drop bytes until next packet start. Should not
                # happen in normal operation.
                logger.error(f"Dropping byte {b:02x}")
                pass
            return None

        # Here collecting packet bytes.
        assert (self.__in_packet)

        if b == PACKET_START_FLAG:
            # Abort current packet and start a new one.
            logger.error(
                f"Dropping partial packet of size {len(self.__packet_bfr)}.")
            self.__reset_packet(True)
            return None

        if b == PACKET_END_FLAG:
            # Process current packet.
            if self.__pending_escape:
                logger.error("Packet has a pending escape, dropping.")
                decoded_packet = None
            else:
                # Returns None or a packet.
                decoded_packet = self.__process_packet()
            self.__reset_packet(False)
            return decoded_packet

        # Check for size overrun. At this point, we know that the packet will
        # have at least one more additional byte, either normal or escaped.
        if len(self.__packet_bfr) >= MAX_PACKET_LEN:
            logger.error("Packet is too long (%d), dropping",
                         len(self.__packet_bfr))
            self.__reset_packet(False)
            return None

        # Handle escape byte.
        if b == PACKET_ESC:
            if self.__pending_escape:
                logger.error("Two consecutive escape chars, dropping packet")
                self.__reset_packet(False)
            else:
                self.__pending_escape = True
            return None

        # Handle an escaped byte.
        if self.__pending_escape:
            # Flip back for 5x to 7x.
            b1 = b ^ 0x20
            if b1 != PACKET_START_FLAG and b1 != PACKET_END_FLAG and b1 != PACKET_ESC:
                logger.error(
                    f"Invalid escaped byte ({b1:02x}, {b:02x}), dropping packet"
                )
                self.__reset_packet(False)
            else:
                self.__packet_bfr.append(b1)
                self.__pending_escape = False
            return None

        # Handle a normal byte
        self.__packet_bfr.append(b)

    def __process_packet(self):
        """Returns a packet or None."""
        rx_bfr = self.__packet_bfr

        # Check for minimum length. A minimum we should
        # have a type byte and two CRC bytes.
        n = len(rx_bfr)
        if n < MIN_PACKET_LEN:
            logger.error("Packet too short (%d), dropping", n)
            return None

        # Check CRC
        packet_crc = int.from_bytes(rx_bfr[-2:], byteorder='big', signed=False)
        computed_crc = self.__crc_calc.calculate(bytes(rx_bfr[:-2]))
        if computed_crc != packet_crc:
            logger.error("Packet CRC error %04x vs %04x, dropping", packet_crc,
                         computed_crc)
            return None

        # Construct decoded packet
        type_value = rx_bfr[0]
        if type_value == PacketType.COMMAND.value:
            cmd_id = int.from_bytes(rx_bfr[1:5], byteorder='big', signed=False)
            endpoint = rx_bfr[5]
            data = PacketData().add_bytes(rx_bfr[6:-2])
            decoded_packet = DecodedCommandPacket(cmd_id, endpoint, data)
        elif type_value == PacketType.RESPONSE.value:
            cmd_id = int.from_bytes(rx_bfr[1:5], byteorder='big', signed=False)
            status = rx_bfr[5]
            data = PacketData().add_bytes(rx_bfr[6:-2])
            decoded_packet = DecodedResponsePacket(cmd_id, status, data)
        elif type_value == PacketType.MESSAGE.value:
            endpoint = rx_bfr[1]
            data = PacketData().add_bytes(rx_bfr[2:-2])
            decoded_packet = DecodedMessagePacket(endpoint, data)
        elif type_value == PacketType.LOG.value:
            data = PacketData().add_bytes(rx_bfr[1:-2])
            decoded_packet = DecodedLogPacket(data)
        else:
            logger.error("Invalid packet type %02x, dropping packet",
                         type_value)
            return None

        if data.size() > MAX_DATA_LEN:
            logger.error("Packet data too long (type=%d, len=%d), dropping",
                         type_value, data.size())
            return None

        # Inform the user about the new packet.
        # self.__decoded_packet_callback(decoded_packet)
        return decoded_packet

        # self.__packets_queue.put_nowait(decoded_packet)
