from __future__ import annotations

import asyncio
import serial_asyncio
import logging
import time
import traceback

from enum import Enum
from typing import Optional, Tuple, Dict, Callable
from asyncio.transports import BaseTransport
from ._packet_encoder import PacketEncoder
from ._packet_decoder import PacketDecoder, DecodedPacket
from ._packets import PacketType, DATA_MAX_LEN
from .packets import PacketStatus, PacketsEvent, PacketsEventType

logger = logging.getLogger(__name__)

# pyserial_asyncio is documented at
# https://github.com/pyserial/pyserial-asyncio


class _TxCommandContext:

    def __init__(self, cmd_id: int, expiration_time: float, future: asyncio.Future):
        """Constructs a command context."""
        self.__cmd_id = cmd_id
        self.__future = future
        self.__expiration_time = expiration_time

    def __str__(self):
        return f"cmd_context {self.__cmd_id}, {self.__expiration_time - time.time()} sec left"

    def set_result(self, status: int, data: bytearray):
        """Transfer the command result to its future."""
        self.__future.set_result((status, data))

    def is_expired(self):
        """Tests if the command timeout."""
        return time.time() > self.__expiration_time


class _SerialProtocol(asyncio.Protocol):
    """Callbacks for the asyncio serial client."""

    def __init__(self):
        self.__client: SerialPacketsClient = None
        self.__port: str = None
        self.__packet_decoder: PacketDecoder = None

    def set(self, client: SerialPacketsClient, port: str, packet_decoder: PacketDecoder):
        self.__client = client
        self.__port = port
        self.__packet_decoder = packet_decoder

    def connection_made(self, transport: BaseTransport):
        self.__client._post_event(PacketsEvent(PacketsEventType.CONNECTED,  logging.INFO))
        # logger.info("Serial [%s] opened.", self.__port)

    def data_received(self, data: bytes):
        self.__packet_decoder._receive(data)

    def connection_lost(self, exc):
        self.__client._post_event(PacketsEvent(PacketsEventType.DISCONNECTED, logging.WARN))

        # logger.info("Serial [%s] closed.", self.__port)

    def pause_writing(self):
        logger.warn("Serial [%s] paused.", self.__port)
        # print('Writing paused', flush=True)

    def resume_writing(self):
        logger.warn("Serial [%s] resumed.", self.__port)
        # print('Writing resumed', flush=True)


class SerialPacketsClient:

    def __init__(self,
                 port: str,
                 command_async_callback: Optional(Callable[[int, bytearray],
                                                           Tuple(int, bytearray)]),
                 event_async_callback: Optional(Callable[[PacketsEvents], None]),
                 baudrate: int = 115200,
                 workers=3):
        """
        Constructs a serial messaging client. 
        
        The constructor doesn't actually open the port. To do that, call connect().

        Args:
        * port: A string with dependent serial port to use. E.g. 'COM1'.
            
        * command_async_callback: An async callback function to be called on incoming
          command requests. Ignored if None. This is an async function that accepts 
          an endpoint (int [0-255]) and command data (bytearray, [0 to DATA_MAX_LEN]) and return
          status (int [0-255]) and response data (bytearray, [0 to DATA_MAX_LEN]).
                
        * baudrate: And optional int port baud rate to set. Default is 115200.
        
        Returns:
        * A new serial messaging client.
        """
        assert (workers > 0 and workers < 10)
        self.__port = port
        self.__baudrate = baudrate
        self.__command_async_callback = command_async_callback
        self.__event_async_callback = event_async_callback
        self.__transport = None
        self.__protocol = None
        self.__packet_encoder = PacketEncoder()
        self.__packet_decoder = PacketDecoder()
        self.__command_id_counter = 0
        self.__tx_cmd_contexts: Dict[int, _TxCommandContext] = {}
        self.__event_queue = asyncio.Queue()

        # Per https://stackoverflow.com/questions/71304329
        self.__background_tasks = []

        # Create a worker task to clean pending command contexts that were timeout.
        # logger.debug("Creating cleanup task")
        # task = asyncio.create_task(self.__cleanup_task_body(), name="cleanup")
        # self.__background_tasks.append(task)
        
        # logger.debug("Creating cleanup task")
        # task = asyncio.create_task(self.__safe_task_runner(self.__cleanup_task_body), name="cleanup")
        # self.__background_tasks.append(task)
        
        self.__create_worker_task(self.__cleanup_task_body, "cleanup")
        
        self.__create_worker_task(self.__events_task_body, "events")

        
        # logger.debug("Creating packets event task")
        # task = asyncio.create_task(self.__events_task_body(), name="packet_events")
        # self.__background_tasks.append(task)

        # Create a few worker tasks to process incoming packets.
        logger.debug("Creating [%d] workers tasks", workers)
        for i in range(3):
            self.__create_worker_task(self.__rx_task_body, f"rx_task_{i+1:02d}")

            # task = asyncio.create_task(self.__rx_task_body(), name=f"rx_task_{i+1:02d}")
            # self.__background_tasks.append(task)

    def __str__(self) -> str:
        return f"{self.__port}@{self.__baudrate}"
      
    def _post_event(self, event: PacketsEvent) -> None:
      logger.log(event.level, "Posted event: %s", event)
      self.__event_queue.put_nowait(event)

    async def connect(self):
        """Connect to serial port."""
        logger.info("Connecting to port [%s]", self.__port)
        self.__transport, self.__protocol = await serial_asyncio.create_serial_connection(
            asyncio.get_event_loop(), _SerialProtocol, self.__port, baudrate=self.__baudrate)
        self.__protocol.set(self, self.__port, self.__packet_decoder)
        
    def __create_worker_task(self, task_body, name):
        logger.debug("Creating worker task '%s'", name)
        task = asyncio.create_task(self.__worker_task_runner(task_body), name=name)
        self.__background_tasks.append(task)
      
    async def __worker_task_runner(self, task_body):
       """Worker tasks runner. Restarts in case of an exception"""
       task_name = asyncio.current_task().get_name()
       while True:
        try:
          await task_body()
        except Exception as e:
          logger.error("Task [%s] exception:", task_name)
          traceback.print_exception(e)

    async def __cleanup_task_body(self):
        """Body of the worker task that clean timeout tx command contexts"""
        task_name = asyncio.current_task().get_name()
        logger.debug("Cleanup task [%s] started", task_name)
        while True:
            await asyncio.sleep(0.05)  
            # print(f"Cleaning task loop", flush=True)
            # NOTE: Deleting dict elements inside a dict iteration is not allowed.
            # Using a workaround instead.
            keys = list(self.__tx_cmd_contexts.keys())
            for cmd_id in keys:
                tx_context = self.__tx_cmd_contexts.get(cmd_id)
                if tx_context.is_expired():
                    logger.error("Command [%d] timeout", cmd_id)
                    tx_context.set_result(0xff, bytearray())
                    self.__tx_cmd_contexts.pop(cmd_id)

    async def __rx_task_body(self):
        """Body of the worker tasks to serve incoming packets."""
        task_name = asyncio.current_task().get_name()
        # print(f"RX task '{task_name}' started", flush=True)
        logger.debug("RX worker task [%s] started", task_name)
        while True:
            packet: DecodedPacket = await self.__packet_decoder.get_next_packet()
            # Since we call user's callback we want to protect the thread from
            # exceptions.
            if packet.type == PacketType.COMMAND:
                await self.__handle_incoming_command_packet(packet)
                continue
            if packet.type == PacketType.RESPONSE:
                await self.__handle_incoming_response_packet(packet)
                continue
            logger.error(f"Unknown packet type [%d], dropping", packet.type)
           
                
                
    async def __events_task_body(self):
        """Body of the worker tasks to service posted events.
        
        For now the event information is minimal and informative
        only but we may extend it in the future.
        """
        task_name = asyncio.current_task().get_name()
        logger.debug("Event worker task [%s] started", task_name)
        while True:
            event: PacketsEvent = await self.__event_queue.get() 
            logger.debug("Event worker got an event")
            if self.__event_async_callback is None:
              logger.debug("No event callback, dropping event: %s", event)
              continue    
            logger.log(event.level, "Callback with event %s", event)
            await self.__event_async_callback(event)
            

    async def __handle_incoming_command_packet(self, packet: DecodedPacket):
        assert (packet.type == PacketType.COMMAND)
        if self.__command_async_callback:
            status, data = await self.__command_async_callback(packet.endpoint, packet.data)
            if len(data) > DATA_MAX_LEN:
                logger.error("Command response data too long (%d), failing command", len(data))
                status, data = (PacketStatus.LENGTH_ERROR.value, bytearray())
        else:
            status, data = (PacketStatus.UNHANDLED.value, bytearray())
        response_packet = self.__packet_encoder.encode_response_packet(packet.cmd_id, status, data)
        self.__transport.write(response_packet)

    async def __handle_incoming_response_packet(self, packet: DecodedPacket):
        # print(f"Handling resp packet ({len(self.__tx_cmd_contexts)} tx contexts)", flush=True)
        assert (packet.type == PacketType.RESPONSE)
        tx_context: _TxCommandContext = self.__tx_cmd_contexts.pop(packet.cmd_id, None)
        if not tx_context:
            logger.error("Response has no matching command [%d], may timeout. Dropping",
                         packet.cmd_id)
            # print(f"Response has no matching context {packet.cmd_id}, dropping", flush=True)
            return
        tx_context.set_result(packet.status, packet.data)

    async def send_command_blocking(self,
                                    endpoint: int,
                                    data: bytearray,
                                    timeout=1.0) -> Tuple([int, bytearray]):
        """ Sends a command and wait for result or timeout. This is a convenience
        method that calls send_command_future() and then waits on the future
        for command result.

        Args:
        * endpoint: The target endpoint (int [0-255]) on the receiver side.  
        * data: The command data (bytearray, [0, DATA_MAX_LEN]).
        * timeout: Command timeout in secs (float 0.1 to 5.0, default 1.0). 
        If a command response is not received within this period, the command
        is aborted with status PacketStatus.TIMEOUT.value and an empty 
        data bytearray.
        
        Returns:
        * status: The command returned status (int, [0-255]) or PacketStatus.TIMEOUT.value
        in case of a timeout.
        * data: The command's response data (bytearray [0, DATA_MAX_LEN] or an empty bytearray
        in case of a timeout.
        """
        future = self.send_command_future(endpoint, data, timeout=timeout)
        status, data = await future
        return (status, data)

    def send_command_future(self,
                            endpoint: int,
                            data: bytearray,
                            timeout=1.0) -> Tuple([int, bytearray]):
        """ Sends a command and return immediately without blocking. 
        
        Caller should wait on the returned future to receive the command
        response once available. The command response is a Tuple with 
        two values, the status code (int, [0-255]) and  response data
        byte returned from the caller (bytearray [0, MAX_DATA_LEN]). Some status
        code values are defined by PacketStatus enum.

        Args:
        * endpoint: The target endpoint (int [0-255]) on the receiver side.  
        * data: The command's data (bytearray [0, DATA_MAX_LEN]).
        * timeout: Command timeout in secs (float 0.1 to 5.0, default 1.0). 
        If a command response is not received within this period, the command
        is aborted with status PacketStatus.TIMEOUT.value and an empty 
        data bytearray.
        
        Returns:
        * A future to wait on for command result. 
        """
        assert (endpoint >= 0 and endpoint <= 255)
        assert (len(data) <= DATA_MAX_LEN)
        assert (timeout >= 0.1 and timeout <= 5.0)
        # Allocate a 32 bit fresh command id. Wrap around are ok since
        # commands are short living.
        self.__command_id_counter = (self.__command_id_counter + 1) & 0xffffffff
        cmd_id = self.__command_id_counter
        assert (not cmd_id in self.__tx_cmd_contexts)
        # Encode packet bytes
        packet = self.__packet_encoder.encode_command_packet(cmd_id, endpoint, data)
        logger.debug("TX command packet [%d]: %s", cmd_id, packet.hex(sep=' '))
        # Create command tx context
        expiration_time = time.time() + timeout
        future = asyncio.Future()
        tx_cmd_context = _TxCommandContext(cmd_id, expiration_time, future)
        self.__tx_cmd_contexts[cmd_id] = tx_cmd_context
        # Start sending
        self.__transport.write(packet)
        # Future will be signaled on response or timeout.
        return future
