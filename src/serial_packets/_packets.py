from __future__ import annotations

from enum import Enum
from .packets import DATA_MAX_LEN

# Flag and escape bytes per HDLC specification.
PACKET_FLAG = 0x7E
PACKET_ESC = 0X7D

# Prefix a packet with a flag byte only if interval from previous
# encoded packet is longer that this time in secs.
PRE_FLAG_TIMEOUT = 1.0

# Packet sizes in bytes, with zero data length, and before
# byte stuffing, and flagging.
PACKET_MIN_OVERHEAD = 4
PACKET_MAX_OVERHEAD = 8

PACKET_MIN_LEN = PACKET_MIN_OVERHEAD
PACKET_MAX_LEN = PACKET_MAX_OVERHEAD + DATA_MAX_LEN

# Do not change the numeric tags since the will change
# the wire representation.
class PacketType(Enum):
    COMMAND = 1
    RESPONSE = 2
