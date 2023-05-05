from __future__ import annotations

from enum import Enum
from .packets import MAX_DATA_LEN

# Flag and escape bytes per HDLC specification.
PACKET_FLAG = 0x7E
PACKET_ESC = 0X7D

# Prefix a packet with a flag byte only if interval from previous
# encoded packet is longer that this time in secs.
PRE_FLAG_TIMEOUT = 1.0

# Packet sizes in bytes, with zero data length, and before
# byte stuffing, and flagging.
MIN_PACKET_OVERHEAD = 4
MAX_PACKET_OVERHEAD = 8

MIN_PACKET_LEN = MIN_PACKET_OVERHEAD
MAX_PACKET_LEN = MAX_PACKET_OVERHEAD + MAX_DATA_LEN

# Range of command timeout values.
MIN_CMD_TIMEOUT = 0.1
MAX_CMD_TIMEOUT = 10.0
DEFAULT_CMD_TIMEOUT = 1.0

# How many workers the use can request.
MIN_WORKERS_COUNT = 1
MAX_WORKERS_COUNT = 30
DEFAULT_WORKERS_COUNT = 3

# Do not change the numeric tags since the will change
# the wire representation.
class PacketType(Enum):
    COMMAND = 1
    RESPONSE = 2
    MESSAGE = 3
