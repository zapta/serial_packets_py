# Python Serial Packets

Python implementations of the Serial Packets protocol.

AS OF MAY 2023, THIS IS WORK IN PROGRESS, NOT READY YET FOR PUBLIC RELEASE.

* PYPI: <https://pypi.org/project/serial-packets/>
* Github: <https://github.com/zapta/serial_packets_py>

Related works:
* Simple HDLC: <https://github.com/wuttem/simple-hdlc>
* ArduHDLC: <https://github.com/jarkko-hautakorpi/Arduhdlc>
* Firmata: <https://github.com/firmata/arduino>

## Protocol Description

The Serial Packets protocol provides packet based point-to-point serial transport for communication between devices. For example, it can be used for communication between an Arduino device and a PC, where the PC controls the device and the device sends data in real time back to the PC. The protocol is symmetrical and both sides to the communication   have the same capabilities with no designation of master/slave at the transport level.

### Highlights

* Protocol is packet oriented, saving the need to implement framing in the application.
* The protocol is Efficient with low per-packet overhead, and requires minimal computation and memory.
* The protocol is symmetrical, and both sides can initiate or response to interactions.
* The protocol is full duplex, and works independently on each direction.
* The protocol support endpoint addressing to simplify routing of messages within the application.
* The protocol supports both one way and two way request/response interactions.
* Each packet is verified with a 16 bits CRC.
* The protocol uses the HDLC byte stuffing algorithm which allow to resync on next frame despite communication errors.
* The wire representation is intuitive which simplifies debugging.
* The protocol is connectionless and stateless, though application can implement the notion of connection and state at their layer..

### Commands

Commands are round-trip interactions where one node send a 'command' packet and the other node sends back 'response' packet that references the original command packet. Commands are useful to control a device and to retrieve information by polling the device using a RPC like
API.

The following tables lists the fields of command request and response  packets, before converting to wire representation as explained later:

#### Command packet

| Field     | Size [bytes] | Source   | Description                                            |
| :-------- | :----------- | :------- | :----------------------------------------------------- |
| PACKET_TYPE      | 1            | Auto     | The value 0x01                                         |
| CMD_ID    | 4            | Auto     | A unique command id for response matching. Big Endian. |
| END_POINT | 1            | **User** | The target endpoint of this command.                   |
| DATA      | 0 to 1024    | **User** | Command data.                                          |
| CRC       | 2            | Auto     | Packet CRC. Big endian.                                |

#### Response packet

| Field  | Size [bytes] | Source   | Description                                 |
| :----- | :----------- | :------- | :------------------------------------------ |
| PACKET_TYPE   | 1            | Auto     | The value 0x02                              |
| CMD_ID | 4            | Auto     | The ID of the original command. Big Endian. |
| STATUS | 1            | **User** | Response status.                            |
| DATA   | 0 to 1024    | **User** | Response data.                              |
| CRC    | 2            | Auto     | Packet CRC. Big endian.                     |

#### Sending a command

The SerialPacketsClient class provides two methods for sending commands.
*send_command_future(...)* for sending using a future that provides the response and *send_command_blocking(...)* which is a convenience method that blocks internally on the future.

Future base command sending:

```python
client = SerialPacketsClient("COM1", my_command_async_callback, my_message_async_callback,  my_event_async_callback)
is_connected = await client.connect()
assert(is_connected)

cmd_endpoint = 20
cmd_data = bytearray([0x01, 0x02, 0x03])
future =  client.send_command_future(cmd_endpoint, cmd_data, timeout=0.2)

# Sometime later
status, data = await future
```

Blocking style command sending:

```python
client = SerialPacketsClient("COM1", my_command_async_callback, my_message_async_callback, my_event_async_callback)
is_connected = await client.connect()
assert(is_connected)

cmd_endpoint = 20
cmd_data = bytearray([0x01, 0x02, 0x03])
rx_status, rx_data = await client.send_command_blocking(cmd_endpoint, cmd_data, timeout=0.2)
```

#### Receiving a command

Incoming commands are received via a callback function that is passed to the SerialPacketsClient when it's created. The callback is an async function that receives the target endpoint and the data of the command and returns the status and data of the response. The client maintains a pool of asyncio workers tasks that serves incoming packets such it's processing one command doesn't block reception of new commands,and command execution can be performed in parallel. If the command is not handled, the callback function should return an empty response with the status UNHANDLED.value.

```python
async def my_command_async_callback(endpoint: int, data: bytearray) -> Tuple[int, bytearray]:
    logger.info(f"Received command: [%d] %s", endpoint, data.hex(sep=' '))
    if (endpoint == 20):
        return handle_command_endpoint_20(data)
    # Add here handling of other end points.
    return (PacketStatus.UNHANDLED.value, bytearray())

def handle_command_endpoint_20(data: bytearray) -> Tuple[int, bytearray]:
    status, response_data = (PacketStatus.OK.value, bytearray([1, 2, 3, 4]))
    logger.info(f"Command response: [%d] %s", status, response_data.hex(sep=' '))
    return (status, response_data)

client = SerialPacketsClient(args.port, my_command_async_callback, my)message_async_callback, my_event_async_callback)
is_connected = await client.connect()
assert(is_connected)
```

### Messages

Messages are a simpler case of a commands with no response. They are useful for periodic notifications, for example for data reporting, and have lower overhead than commands.

#### Message packet

| Field     | Size [bytes] | Source   | Description                          |
| :-------- | :----------- | :------- | :----------------------------------- |
| PACKET_TYPE      | 1            | Auto     | The value 0x03                       |
| END_POINT | 1            | **User** | The target endpoint of this command. |
| DATA      | 0 to 1024    | **User** | Command data.                        |
| CRC       | 2            | Auto     | Packet CRC. Big endian.              |

#### Sending a message

The *SerialPacketsClient* class provides a method for sending a command. The method is non blocking and merely queues the message for sending.
two methods for sending commands.

```python
client = SerialPacketsClient("COM1", my_command_async_callback my_event_async_callback)
is_connected = await client.connect()
assert(is_connected)
...
msg_endpoint = 20
msg_data = bytearray([0x01, 0x02, 0x03])
client.send_message(msg_endpoint, msg_data)
```

#### Receiving a message

Incoming messages are received via a callback function that is passed to the SerialPacketsClient when it's created. The callback is an async function that receives the target endpoint and the data of the message and returns no value.

```python
async def my_message_async_callback(endpoint: int, data: bytearray) -> Tuple[int, bytearray]:
    logger.info(f"Received message: [%d] %s", endpoint, data.hex(sep=' '))

client = SerialPacketsClient(args.port, my_command_async_callback, my_message_async_callback, my_event_async_callback)
is_connected = await client.connect()
assert(is_connected)
```

## Events

The SerialPacketsClient signals the application about certain events via an events callback that the use pass to it upon initialization.

```python
async def my_event_async_callback(event: PacketsEvent) -> None:
    logger.info("Event %s: %s", event.event_type(), event.description())
    logger.info("%s event", event)

client = SerialPacketsClient(args.port, my_command_async_callback, my_message_async_callback, my_event_async_callback)
is_connected = await client.connect()
assert(is_connected)
```

```python
```

As of May 2023 only a couple of events are supported.  

```python
class PacketsEventType(Enum):
    CONNECTED = 1
    DISCONNECTED = 2
```

## Wire representation

### Packet flag byte

The Serial Packets protocol uses packet flags similar to the HDLC protocol, with the special flag byte 0x7E inserted in the serial stream to mark packet ends. A flag byte is always inserted immediately after the
last byte of each packet, and also optionally just before the first byte of packets, if the interval from the previous packet was longer than a certain time period.

### Byte stuffing

To make the flag byte 0x7E unique in the serial stream, the Serial Packet uses 'byte stuffing' borrowed from the HDLC protocol. This allows the protocol to resync on next packet boundary, in case of line errors. This byte stuffing is done using the escape byte 0X7D

| Packet byte | Wire bytes | Comments            |
| :---------- | :--------- | :------------------ |
| 0x7E        | 0x7D, 0x5E | Escaped flag byte   |
| 0x7D        | 0x7D, 0x5D | Escaped escape byte |
| Other bytes | No change  | The common case     |

## Status codes

The Serial Packets protocol uses 1 byte status codes where 0x00 indicates success and all other values indicate errors. These status codes are used in the command responses, and optionally also by the implementation API for other reasons.

As of May 2023, these are the predefined status codes. For the updated list, look at the *serial_packets.packets.PacketStatus* enum.

| Status Value | Status name      | Comments                             |
| :----------- | :--------------- | :----------------------------------- |
| 0            | OK               | The only non error status.           |
| 1            | GENERAL_ERROR    | Unspecified error.                   |
| 2            | TIMEOUT          | A request timed out.                 |
| 3            | UNHANDLED        | No handler for this command.         |
| 4            | INVALID_ARGUMENT | Invalid argument value in a request. |
| 5            | LENGTH_ERROR     | Data has invalid length.             |
| 6            | OUT_OF_RANGE     | A more specific invalid argument.    |
| 7 - 99       | Reserved         | For future protocol definitions.     |
| 100-255      | Custom           | For user's application specific use. |

## Endpoints

Endpoints represent the destinations of commands and messages on the receiving node and allows the application to distinguish between command and message types. End points are identified by a single byte, where the values 0-199 are available for the application, and the values 200-255 are reserved for future expansions of the protocol.

## Data

Commands, responses and messages pass  data which is a sequence of zero to 1024 bytes. These bytes are opaque to the protocol which treat them as a blob. It's up to the application to determine the semantic of these bytes and to encode and decode them as needed.

## Application Example

The repository contains and example with two main programs that communicate between them via serial port. One program called 'master' periodically sends a command and waits for a response and the other one called 'slave' sends a message periodically. To run the example, use two USB/Serial adapters and connect the TX of the first to the RX of the second and vice versa. Also, make sure to connect the gwo grounds. Then run each of the two program, providing the respective port in the command line. Make sure to replace the serial port ids in the example below with the actual port id of your system.

<https://github.com/zapta/serial_packets_py/tree/main/src/examples>

Running the master:

```python
python -u  master.py --port="COM21" 
```

Running the slave (in another shell, or another computer):

```python
python -u  slave.py --port="COM22" 
```

## FAQ

**Q**: What other Serial Packets implementations are available?

A: This Python implementation is the first. As of May 2023, we are actively developing an Arduino implementation.

---

**Q**: What platforms are supported by this Python implementation?

A: The package is implemented using the [pyserial-asyncio](https://pypi.org/project/pyserial-asyncio/) package which as of May 2023 supports Max OSX, Windows, and Linux.

---

**Q**: Can I contribute new implementations?

A: Of course. We would love to list your implementation here.

---

**Q**: Can I contribute fixes and protocol extensions?

A: Of course. Please feel free to contact us on github.

---

**Q**: Why asyncio based implementation, doesn't it complicate things?

A: Asyncio may make simple programs more complicated but it allows for more responsive programs with efficient parallel I/O.

---

**Q**: Do you plan to provide also cross platform APIs for data serialization/deserialization?

A: This is a good idea, but we are not working on it as of May 2023. We would any recommendations or implementations of such a portable API.

---

**Q**: Is there a serial sniffer for the Serial Packets protocol?

A: Note at the moment, but if you will implement one, we would love to a reference it here. It can be implemented for example with a Python program or with an Arduino sketch.
