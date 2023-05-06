from __future__ import annotations

from enum import Enum
import logging

# Max size of data that is sent in a command request, command response,
# or in a message. This is the original size in bytes before byte stuffing.
# Data min length is always 0.
MAX_DATA_LEN = 1024

# Endpoints 200-255 are reserved for future protocol expansion.
MAX_USER_ENDPOINT = 199

MIN_RX_WORKERS_COUNT = 1
MAX_RX_WORKER_COUNT = 20
DEFAULT_RX_WORKER_COUNT = 5


class PacketsEventType(Enum):
    """Event type."""
    CONNECTED = 1
    DISCONNECTED = 2


class PacketsEvent:
    """Callback event that is passed to the user.."""

    def __init__(self, event_type: PacketsEventType, description: str):
        self.event_type: PacketsEventType = event_type
        self.description: str = description
        
    def event_type(self) -> PacketsEventType:
      return self.__event_type   
    
    def description(self) ->str:
      return self.__description 
    

    def __str__(self):
        return f"{self.event_type.name}: {self.description}"


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
    OUT_OF_RANGE = 6
    NOT_CONNECTED = 7

    # Users can start allocating error codes from
    # here to 255.
    USER_ERRORS_BASE = 100
