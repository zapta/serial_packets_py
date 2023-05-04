from __future__ import annotations

from enum import Enum
import logging

# Max size of data that is sent in a command request, command response,
# or in a message. This is the original size in bytes before byte stuffing.
# Data min length is always 0.
DATA_MAX_LEN = 1024


class PacketsEventType(Enum):
    """Event type."""
    CONNECTED = 1
    DISCONNECTED = 2


class PacketsEvent:
    """Callback event"""

    def __init__(self, event_type: PacketsEventType, level: int = logging.INFO):
        self.event_type = event_type
        self.level = level

    def __str__(self):
        return self.event_type.name


class PacketStatus(Enum):
    """Defines status codes. User NAME.value to convert to int. 
    valid values are [0, 255]
    """
    OK = 0
    GENERAL_ERROR = 1
    TIMEOUT = 2
    UNHANDLED = 3
    INVALID_ARGUMENT = 4
    LENGTH_ERROR = 5

    # Users can start allocating error codes from
    # here to 255.
    USER_ERRORS_BASE = 100
