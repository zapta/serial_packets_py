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
from ._packet_decoder import PacketDecoder, DecodedCommandPacket, DecodedResponsePacket, DecodedMessagePacket
from ._packets import PacketType, MAX_DATA_LEN, MIN_CMD_TIMEOUT, MAX_CMD_TIMEOUT, DEFAULT_CMD_TIMEOUT, MIN_WORKERS_COUNT, MAX_WORKERS_COUNT, DEFAULT_WORKERS_COUNT, PRE_FLAG_TIMEOUT
from ._interval_tracker import IntervalTracker
from .packets import PacketStatus, PacketsEvent, PacketsEventType, PacketsEvent, PacketData, MAX_USER_ENDPOINT

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

    def set_command_result(self, status: int, data: PacketData):
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
        self.__is_connected = False

    def set(self, client: SerialPacketsClient, port: str, packet_decoder: PacketDecoder):
        self.__client = client
        self.__port = port
        self.__packet_decoder = packet_decoder

    def is_connected(self):
        return self.__is_connected

    def connection_made(self, transport: BaseTransport):
        self.__is_connected = True
        self.__client._post_event(
            PacketsEvent(PacketsEventType.CONNECTED, f"Connected to {self.__port}"))

    def data_received(self, data: bytes):
        self.__packet_decoder.receive(data)

    def connection_lost(self, exc):
        self.__is_connected = False
        self.__client._post_event(
            PacketsEvent(PacketsEventType.DISCONNECTED, f"Disconnected from {self.__port}"))

    def pause_writing(self):
        logger.warn("Serial [%s] paused.", self.__port)
        # print('Writing paused', flush=True)

    def resume_writing(self):
        logger.warn("Serial [%s] resumed.", self.__port)


class SerialPacketsClient:

    def __init__(self,
                 port: str,
                 command_async_callback: Optional(Callable[[int, PacketData],
                                                           Tuple(int, PacketData)]) = None,
                 message_async_callback: Optional(Callable[[int, PacketData], None]) = None,
                 event_async_callback: Optional(Callable[[PacketsEvent], None]) = None,
                 baudrate: int = 115200,
                 workers: int = DEFAULT_WORKERS_COUNT):
        """
        Constructs a serial messaging client. 
        
        The constructor doesn't actually open the port. To do that, call connect().

        Args:
        * port: A string with dependent serial port to use. E.g. 'COM1'.
            
        * command_async_callback: An optional async callback function to be called on incoming
          command requests. Ignored if None. This is an async function that accepts 
          an endpoint (int [0-255]) and command data (PacketData, [0 to DATA_MAX_LEN]) and return
          status (int [0-255]) and response data (PacketData, [0 to DATA_MAX_LEN]).
          
        * message_async_callback: An optional async callback function to be called on incoming
          messages. Ignored if None. This is an async function that accepts 
          an endpoint (int [0-255]) and command data (PacketData, [0 to DATA_MAX_LEN]) 
          and does not return a value.
          
        * event_async_callback: An optional async callback function to be called on
          on certain client events such as port connection and disconnection. 
          Ignored if None. This is an async function that accepts 
          a PacketEvent argument and returns no value.
                
        * baudrate: And optional int port baud rate to set. Default is 115200.
        
        * workers: An optional int that specifies how many worker tasks the client should
        use for servicing user callbacks. Having a value higher than 1 allows 
        more parallelism, but may be unnecessary. Range is MIN_WORKERS_COUNT to 
        MAX_WORKERS_COUNT, and default is DEFAULT_WORKERS_COUNT. 
        
        Returns:
        * A new serial messaging client.
        """
        assert (workers >= MIN_WORKERS_COUNT and workers <= MAX_WORKERS_COUNT)
        self.__port = port
        self.__baudrate = baudrate
        self.__command_async_callback = command_async_callback
        self.__message_async_callback = message_async_callback
        self.__event_async_callback = event_async_callback
        self.__transport = None
        self.__protocol = None
        self.__packet_encoder = PacketEncoder()
        self.__packet_decoder = PacketDecoder(self.__on_decoded_packet)
        self.__command_id_counter = 0
        self.__interval_tracker = IntervalTracker(PRE_FLAG_TIMEOUT)
        self.__tx_cmd_contexts: Dict[int, _TxCommandContext] = {}
        # Work items types:
        # * PacketsEvent: call user's event handler.
        # * DecodedCommandPacket: handle incoming command packet.
        # * DecodedResponsePacket: handle incoming response packet.
        # * DecodedMessagePacket: handle incoming message packet.
        self.__work_queue = asyncio.Queue()
        # Per https://stackoverflow.com/questions/71304329
        self.__background_tasks = []

        self.__create_loop_runner_task(self.__cleanup_task_loop, "cleanup")

        # Create a few worker tasks to process incoming packets.
        logger.debug("Creating [%d] workers tasks", workers)
        for i in range(workers):
            self.__create_loop_runner_task(self.__worker_task_loop, f"rx_task_{i+1:02d}")

    def __str__(self) -> str:
        return f"{self.__port}@{self.__baudrate}"

    def is_connected(self) -> bool:
        """Test if the client is connected to the port."""
        return self.__protocol and self.__protocol.is_connected()

    def _post_event(self, event: PacketsEvent) -> None:
        logger.debug("Posted event: %s", event)
        self.__work_queue.put_nowait(event)

    async def connect(self) -> bool:
        """Connect to serial port. Returns True if connected to port."""
        logger.debug("Connecting to port [%s]", self.__port)
        try:
            self.__transport, self.__protocol = await serial_asyncio.create_serial_connection(
                asyncio.get_event_loop(), _SerialProtocol, self.__port, baudrate=self.__baudrate)
        except Exception as e:
            logger.error("%s", e)
            if logging.DEBUG >= logger.getEffectiveLevel():
                traceback.print_exception(e)
            return False
        self.__protocol.set(self, self.__port, self.__packet_decoder)
        return True

    def __on_decoded_packet(self, decoded_packet: DecodedCommandPacket | DecodedResponsePacket |
                            DecodedMessagePacket):
        """Called from the packet decoder on each receive packet"""
        logger.debug("Queuing incoming packet of type [%s.]", type(decoded_packet).__name__)
        self.__work_queue.put_nowait(decoded_packet)

    def __create_loop_runner_task(self, task_loop, name):
        logger.debug("Creating task '%s'", name)
        task = asyncio.create_task(self.__loop_runner_task(task_loop), name=name)
        self.__background_tasks.append(task)

    async def __loop_runner_task(self, task_loop):
        """Run worker task loops"""
        task_name = asyncio.current_task().get_name()
        logger.debug("Task started '%s'", task_name)
        while True:
            try:
                await task_loop(task_name)
            except Exception as e:
                logger.error("Task [%s] exception:", task_name)
                traceback.print_exception(e)

    async def __cleanup_task_loop(self, task_name):
        """Worker task loop for cleaning outgoing commands that timeout."""
        await asyncio.sleep(0.05)
        # NOTE: Deleting dict elements inside a dict iteration is not allowed.
        # Using a workaround instead.
        keys = list(self.__tx_cmd_contexts.keys())
        for cmd_id in keys:
            tx_context = self.__tx_cmd_contexts.get(cmd_id)
            if tx_context.is_expired():
                logger.error("Command [%d] timeout", cmd_id)
                tx_context.set_command_result(PacketStatus.TIMEOUT.value, PacketData())
                self.__tx_cmd_contexts.pop(cmd_id)

    async def __worker_task_loop(self, task_name):
        """Body of the worker tasks to serve incoming packets."""
        # task_name = asyncio.current_task().get_name()
        # print(f"RX task '{task_name}' started", flush=True)
        # logger.debug("RX worker task [%s] started", task_name)
        # while True:
        work_item = await self.__work_queue.get()
        # Since we call user's callback we want to protect the thread from
        # exceptions.
        if isinstance(work_item, DecodedCommandPacket):
            await self.__handle_incoming_command_packet(work_item)
        elif isinstance(work_item, DecodedResponsePacket):
            await self.__handle_incoming_response_packet(work_item)
        elif isinstance(work_item, DecodedMessagePacket):
            await self.__handle_incoming_message_packet(work_item)
        elif isinstance(work_item, PacketsEvent):
            await self.__handle_packets_event(work_item)
        else:
            logger.error(f"Unknown work item type [%s], dropping", type(work_item))

    async def __handle_incoming_command_packet(self, decoded_cmd_packet: DecodedCommandPacket):
        assert (isinstance(decoded_cmd_packet, DecodedCommandPacket))
        if self.__command_async_callback:
            status, data = await self.__command_async_callback(decoded_cmd_packet.endpoint,
                                                               decoded_cmd_packet.data)
            if data.size() > MAX_DATA_LEN:
                logger.error("Command response data too long (%d), failing command", data.size9)
                status, data = (PacketStatus.LENGTH_ERROR.value, PacketData())
        else:
            status, data = (PacketStatus.UNHANDLED.value, PacketData())
        response_packet = self.__packet_encoder.encode_response_packet(
            decoded_cmd_packet.cmd_id, status, data._internal_bytes_buffer(), self.__interval_tracker.track_packet())
        self.__transport.write(response_packet)

    async def __handle_incoming_response_packet(self, decoded_rsp_packet: DecodedResponsePacket):
        # print(f"Handling resp packet ({len(self.__tx_cmd_contexts)} tx contexts)", flush=True)
        assert (isinstance(decoded_rsp_packet, DecodedResponsePacket))
        tx_context: _TxCommandContext = self.__tx_cmd_contexts.pop(decoded_rsp_packet.cmd_id, None)
        if not tx_context:
            logger.error("Response has no matching command [%d], may timeout. Dropping",
                         decoded_rsp_packet.cmd_id)
            # print(f"Response has no matching context {packet.cmd_id}, dropping", flush=True)
            return
        tx_context.set_command_result(decoded_rsp_packet.status, decoded_rsp_packet.data)

    async def __handle_incoming_message_packet(self, decoded_msg_packet: DecodedMessagePacket):
        assert (isinstance(decoded_msg_packet, DecodedMessagePacket))
        if self.__message_async_callback:
            await self.__message_async_callback(decoded_msg_packet.endpoint,
                                                decoded_msg_packet.data)
        else:
            logger.debug("No message callback, dropping incoming message")

    async def __handle_packets_event(self, packets_event):
        assert (isinstance(packets_event, PacketsEvent))
        if self.__event_async_callback is None:
            logger.debug("No event callback, dropping event: %s", packets_event)
        else:
            logger.debug("Callback with event %s", packets_event)
            await self.__event_async_callback(packets_event)

    async def send_command_blocking(self,
                                    endpoint: int,
                                    data: PacketData,
                                    timeout=DEFAULT_CMD_TIMEOUT) -> Tuple([int, PacketData]):
        """ Sends a command and wait for result or timeout. This is a convenience
        method that calls send_command_future() and then waits on the future
        for command result.

        Args:
        * endpoint: The target endpoint (int [0-MAX_USER_ENDPOINT]) on the receiver side.  
        * data: The command data (PacketData, [0, DATA_MAX_LEN]).
        * timeout: Command timeout in secs (float MIN_CMD_TIMEOUT to MAX_CMD_TIMEOUT, default DEFAULT_CMD_TIMEOUT). 
        If a command response is not received within this period, the command
        is aborted with status PacketStatus.TIMEOUT.value and an empty 
        data PacketData.
        
        Returns:
        * status: The command returned status (int, [0-255]) or PacketStatus.TIMEOUT.value
        in case of a timeout.
        * data: The command's response data (PacketData [0, DATA_MAX_LEN] or an empty PacketData
        in case of a timeout.
        """
        future = self.send_command_future(endpoint, data, timeout=timeout)
        status, data = await future
        return (status, data)

    def send_command_future(self,
                            endpoint: int,
                            data: PacketData,
                            timeout=DEFAULT_CMD_TIMEOUT) -> Tuple([int, PacketData]):
        """ Sends a command and return immediately without blocking. 
        
        Caller should wait on the returned future to receive the command
        response once available. The command response is a Tuple with 
        two values, the status code (int, [0-255]) and  response data
        byte returned from the caller (PacketData [0, MAX_DATA_LEN]). Some status
        code values are defined by PacketStatus enum.

        Args:
        * endpoint: The target endpoint (int [0-255]) on the receiver side.  
        * data: The command's data (PacketData [0, DATA_MAX_LEN]).
        * timeout: Command timeout in secs (float MIN_CMD_TIMEOUT to MAX_CMD_TIMEOUT, default DEFAULT_CMD_TIMEOUT). 
        If a command response is not received within this period, the command
        is aborted with status PacketStatus.TIMEOUT.value and an empty 
        data PacketData.
        
        Returns:
        * A future to wait on for command result. 
        """
        assert (endpoint >= 0 and endpoint <= MAX_USER_ENDPOINT)
        assert (data.size() <= MAX_DATA_LEN)
        assert (timeout >= MIN_CMD_TIMEOUT and timeout <= MAX_CMD_TIMEOUT)
        if not self.is_connected():
            logger.error("Client not connected when trying to send a message")
            future = asyncio.Future()
            future.set_result((PacketStatus.NOT_CONNECTED.value, PacketData()))
            return future
        # Allocate a 32 bit fresh command id. Wrap around are ok since
        # commands are short living.
        self.__command_id_counter = (self.__command_id_counter + 1) & 0xffffffff
        cmd_id = self.__command_id_counter
        assert (not cmd_id in self.__tx_cmd_contexts)
        # Encode packet bytes
        packet = self.__packet_encoder.encode_command_packet(cmd_id, endpoint, data._internal_bytes_buffer(), self.__interval_tracker.track_packet())
        logger.debug("TX command packet [%d]: %s", endpoint, packet.hex(sep=' '))
        # Create command tx context
        expiration_time = time.time() + timeout
        future = asyncio.Future()
        tx_cmd_context = _TxCommandContext(cmd_id, expiration_time, future)
        self.__tx_cmd_contexts[cmd_id] = tx_cmd_context
        # Start sending
        self.__transport.write(packet)
        # Future will be signaled on response or timeout.
        return future

    def send_message(self, endpoint: int, data: PacketData) -> None:
        """ Sends a message. Returns immediately, before sending completed. 

            Args:
            * endpoint: The target endpoint (int [0-255]) on the receiver side.  
            * data: The message's data (PacketData [0, DATA_MAX_LEN]).
            
            Returns:
            * None.
            """
        assert (endpoint >= 0 and endpoint <= MAX_USER_ENDPOINT)
        assert (data.size() <= MAX_DATA_LEN)
        if not self.is_connected():
            logger.warn("Client not connected, ignoring message send")
            return
        # Encode packet bytes
        packet = self.__packet_encoder.encode_message_packet(endpoint, data._internal_bytes_buffer(), self.__interval_tracker.track_packet())
        logger.debug("TX message packet [%d]: %s", endpoint, packet.hex(sep=' '))
        # Start sending
        self.__transport.write(packet)
