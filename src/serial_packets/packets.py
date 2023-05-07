from __future__ import annotations

from enum import Enum
from typing import Iterable
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

    def description(self) -> str:
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


class PacketData:
    """Packet data buffer, with methods to serialize/deserialize the data."""

    def __init__(self):
        """ Constructs a PacketData with given intitial data."""
        self.__data =  bytearray()
        self.__bytes_read = 0

    def hex_str(self) -> str:
        """Returns a string with a hex dump fo the bytes. Can be long."""
        return self.__data_bytes.hex(sep=' ')

    def bytes(self) -> bytearray:
        """Return a copy of the data bytes."""
        return self.__data.copy()

    def _internal_bytes_buffer(self) -> bytearray:
        """Package private. Returns a reference to the internal bytearray. Do not mutate."""
        return self.__data

    def size(self) -> int:
        """Returns the number of data bytes."""
        return len(self.__data)

    def clear(self) -> None:
        """Clear all data bytes and reset read location."""
        self.__data.clear()
        self.__bytes_read = 0

    def bytes_read(self) -> int:
        """The number of bytes read so far. This indicates current reading location."""
        return self.__bytes_read

    def bytes_availale_to_read(self) -> int:
        """Returns the number of bytes from the currennt reading location to the end of the data."""
        return len(self.__data) - self.__bytes_read

    def all_read(self) -> bool:
        """Returns true if read location is past the last data byte."""
        return self.__bytes_read == len(self.__data)

    def reset_read_location(self):
        """Set the reading location to the begining of the data."""
        self.__bytes_read = 0

    # --- Adding data

    def add_byte(self, val: int) -> PacketData:
        """Asserts that the value is in the range [0, 0xff] and appends it 
        to the data as a single byte."""
        assert (val >= 0 and val <= 0xff)
        self.__data.append(val)
        return self

    def add_uint16(self, val: int) -> PacketData:
        """Asserts that the value is in the range [0, 0xff] and appends it 
        to the data as 2 bytes in big endian order."""
        assert (val >= 0 and val <= 0xff)
        self.__data.extend(val.to_bytes(2, 'big'))
        return self

    def add_uint32(self, val: int) -> PacketData:
        """Asserts that the value is in the range [0, 0xffff] and appends it 
        to the data as 4 bytes in big endian order."""
        assert (val >= 0 and val <= 0xffff)
        self.__data.extend(val.to_bytes(4, 'big'))
        return self

    def add_bytes(self, bytes: bytearray) -> PacketData:
        """Appends the given bytes to the data."""
        self.__data.extend(bytes)
        return self

    #  --- Parsing data

    def read_byte(self) -> int | None:
        """Returns the next byte and advance the reading location by one byte,
        or returns None if already at the end of the daata.
        """
        if self.__bytes_read + 1 > len(self.__data):
            return None
        result = self.__data[self.__bytes_read]
        self.__bytes_read += 1
        return result

    def read_uint16(self) -> int | None:
        """Decods the next 2 bytes as a 16 bits unsigned big endian value.
        Returns the 16 bit numbmer and advances the reading location by 2 bytes,
        or returns None if insuffient number of bytes to read.
        """
        if self.__bytes_read + 2 > len(self.__data):
            return None
        result = int.from_bytes(self.__data[self.__bytes_read:self.__bytes_read + 2],
                                byteorder='big',
                                signed=False)
        self.__bytes_read += 2
        return result

    def read_uint32(self) -> int | None:
        """Decods the next 4 bytes as am unsigned  32 bits big endian value.
        Returns the 32 bit numbmer and advances the reading location by 4 bytes,
        or returns None if insuffient number of bytes to read.
        """
        if self.__bytes_read + 4 > len(self.__data):
            return None
        result = int.from_bytes(self.__data[self.__bytes_read:self.__bytes_read + 4],
                                byteorder='big',
                                signed=False)
        self.__bytes_read += 4
        return result

    def read_bytes(self, n: int) -> bytearray | None:
        """Returns the next n bytes and advances the reading location,
        or None if insuffient number of bytes."""
        assert (n >= 0)
        if self.__bytes_read + n > len(self.__data):
            return None
        result = self.__data[self.__bytes_read:self.__bytes_read + n]
        self.__bytes_read += n
        return result
