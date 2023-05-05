# A sample program that accepts handles serial_packets commands at endpoint 20.
# To test with master.py, use two serial points with crossed RX/TX.

from __future__ import annotations

# For using the local version of serial_packet.
import sys

sys.path.insert(0, "../../src")

import argparse
import asyncio
import logging
from typing import Tuple, Optional
from serial_packets.client import SerialPacketsClient
from serial_packets.packets import PacketStatus, PacketsEvent, PacketsEventType

# Set default logging level for the entire program.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("slave_main")

parser = argparse.ArgumentParser()
parser.add_argument("--port", dest="port", default=None, help="Serial port to use.")
args = parser.parse_args()


async def event_async_callback(event: PacketsEvent) -> None:
    logger.info("%s event", event)


async def command_async_callback(endpoint: int, data: bytearray) -> Tuple[int, bytearray]:
    logger.info(f"Received command: [%d] %s", endpoint, data.hex(sep=' '))
    if (endpoint == 20):
        return handle_command_endpoint_20(data)
    # Add here handling of other end points.
    return (PacketStatus.UNHANDLED.value, bytearray())


def handle_command_endpoint_20(data: bytearray) -> Tuple[int, bytearray]:
    status, response_data = (PacketStatus.OK.value, bytearray([1, 2, 3, 4]))
    logger.info(f"Command response: [%d] %s", status, response_data.hex(sep=' '))
    return (status, response_data)


async def async_main():
    logger.info("Started.")
    assert (args.port is not None)
    client = SerialPacketsClient(args.port, command_async_callback, event_async_callback)
    await client.connect()
    logger.info("Connected")
    while True:
        # Nothing to do here in this simple example.
        await asyncio.sleep(1)


asyncio.run(async_main(), debug=True)
