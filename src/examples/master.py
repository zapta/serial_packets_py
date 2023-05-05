# A sample program that sends serial_packets commands at endpoint 20.
# To test with slave.py, use two serial points with crossed RX/TX.

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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("master")

parser = argparse.ArgumentParser()
parser.add_argument("--port", dest="port", default=None, help="Serial port to use.")
args = parser.parse_args()


async def event_async_callback(event: PacketsEvent) -> None:
    logger.info("%s event", event)


async def message_async_callback(endpoint: int, data: bytearray) -> Tuple[int, bytearray]:
    logger.info(f"Received message: [%d] %s", endpoint, data.hex(sep=' '))


async def command_async_callback(endpoint: int, data: bytearray) -> Tuple[int, bytearray]:
    logger.info(f"Received command: [%d] %s", endpoint, data.hex(sep=' '))
    # In this example, this node doesn't receives commands.
    return (PacketStatus.UNHANDLED.value, bytearray())


async def async_main():
    logger.info("Started.")
    assert (args.port is not None)
    client = SerialPacketsClient(args.port, command_async_callback, message_async_callback,
                                 event_async_callback)
    await client.connect()
    logger.info("Master connected")
    while True:
        # Send a command every 500 ms.
        await asyncio.sleep(0.5)
        cmd_endpoint = 20
        cmd_data = bytearray([0x13, 0x00, 0x7D, 0x00, 0x7E, 0x00])
        logger.info("Sending command: [%d], %s", cmd_endpoint, cmd_data.hex(sep=' '))
        rx_status, rx_data = await client.send_command_blocking(cmd_endpoint, cmd_data, timeout=0.2)
        logger.info(f"Command result: [%d], %s", rx_status, rx_data.hex(sep=' '))


asyncio.run(async_main(), debug=True)
