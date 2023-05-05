# Python Serial Packets

Python implementations of the Serial Packets protocol.

WORK IN PROGRESS, NOT READY FOR PUBLIC RELEASE.

PYPI: https://pypi.org/project/serial-packets/
Github: https://github.com/zapta/serial_packets_py


## Protocol Description
The Serial Packets protocol is packet based point-to-point serial transport for communication between devices. For example, it can be used for communication between an Arduino device and a PC, such that the PC controls the device and the device can send data back to the PC. The protocol is symmetrical such that both nodes have the same capabilities with no notion of master/slave at the protocol level.

### Highlights
* Packet oriented. Users don't need to parse a serial stream.
* Efficient, with low per-packet overhead.
* Symmetrical, both ends have the same capabilities.
* Full duplex.
* Supports endpoint addressing.
* Supports one way messages and round trip command/response. 
* Packets are verified with CRC.
* Automatic detection on next packet, in case of line errors, via HDLC stuffing. 
* Intuitive wire representation.

### Commands
Commands are round-trip interactions where one node send a 'command' packet to the other and receives back a 'response' packet that is associated with that specific command. Commands are useful to control a device and to retrieve information by polling the device.

The following tables lists the parts of a command request and response  packets, before converting to wire representation (explained later):

#### Command packet

| Field     | Size [bytes] | Source   | Description                                |
| :-------- | :----------- | :------- | :----------------------------------------- |
| TYPE      | 1            | Auto     | The value 0x01                             |
| CMD_ID    | 4            | Auto     | A unique command id for response matching. |
| END_POINT | 1            | **User** | The target endpoint of this command.       |
| DATA      | 0 to 1024    | **User** | Command data.                              |
| CRC       | 2            | Auto     | Packet CRC.                                |

#### Response packet

| Field  | Size [bytes] | Source   | Description                     |
| :----- | :----------- | :------- | :------------------------------ |
| TYPE   | 1            | Auto     | The value 0x02                  |
| CMD_ID | 4            | Auto     | The ID of the original command. |
| STATUS | 1            | **User** | Response status.                |
| DATA   | 0 to 1024    | **User** | Response data.                  |
| CRC    | 2            | Auto     | Packet CRC.                     |

#### Sending a command

The SerialPacketsClient class provides two methods for sending commands.
*send_command_future(...)* for sending using a future that provides the response and *send_command_blocking(...)* which is a convenience method that blocks internally on the future.


**Future based API**
```python
client = SerialPacketsClient("COM1", my_command_async_callback my_event_async_callback)
await client.connect()
...
cmd_endpoint = 20
cmd_data = bytearray([0x01, 0x02, 0x03])
future =  client.send_command_future(cmd_endpoint, cmd_data, timeout=0.2)
...
status, data = await future
```

**Blocking API**
```python
client = SerialPacketsClient("COM1", my_command_async_callback my_event_async_callback)
await client.connect()
...
cmd_endpoint = 20
cmd_data = bytearray([0x01, 0x02, 0x03])
rx_status, rx_data = await client.send_command_blocking(cmd_endpoint, cmd_data, timeout=0.2)
```
#### Receiving a command
Incoming commands are received via a single callback function that is passed to the SerialPacketsClient when it's created. The call back is an async function that receives the endpoint and data of the command and returns the status and data of the response. The client maintains a pool of asyncio tasks that serves incoming packets such it's possible to have  multiple commands processed in parallel. If the command is not handled, the callback should return an empty response with the status UNHANDLED.value.

```python
async def my_command_async_callback(endpoint: int, data: bytearray) -> Tuple[int, bytearray]:
    logger.info(f"Received command: [%d] %s", endpoint, data.hex(sep=' '))
    if (endpoint == 20):
        return handle_command_endpoint_20(data)
    # Add here handling of other end points.
    return (PacketStatus.UNHANDLED.value, bytearray())
...
def handle_command_endpoint_20(data: bytearray) -> Tuple[int, bytearray]:
    status, response_data = (PacketStatus.OK.value, bytearray([1, 2, 3, 4]))
    logger.info(f"Command response: [%d] %s", status, response_data.hex(sep=' '))
    return (status, response_data)
...
client = SerialPacketsClient(args.port, my_command_async_callback, my_event_async_callback)
await client.connect()
```

### Messages
Message are a simpler case of a commands with no response. They are useful for notifications such as a periodic data reporting, and have lower overhead than commands.

#### Message packet

| Field     | Size [bytes] | Source   | Description                          |
| :-------- | :----------- | :------- | :----------------------------------- |
| TYPE      | 1            | Auto     | The value 0x03                       |
| END_POINT | 1            | **User** | The target endpoint of this command. |
| DATA      | 0 to 1024    | **User** | Command data.                        |
| CRC       | 2            | Auto     | Packet CRC.                          |

#### Sending a message

The SerialPacketsClient class provides two methods for sending commands.
*send_command_future(...)* for sending using a future that provides the response and *send_command_blocking(...)* which is a convenience method that blocks internally on the future.


**API**
Sending a message is simpler than sending a command because it doesn't involves waiting and handling a response.

```python
client = SerialPacketsClient("COM1", my_command_async_callback my_event_async_callback)
await client.connect()
...
msg_endpoint = 20
msg_data = bytearray([0x01, 0x02, 0x03])
client.send_message(msg_endpoint, msg_data)
```

#### Receiving a message
TBD

**API**
TBD

## Events

TBD

## Wire representation

### Packet flag byte
The Serial Packets protocol uses packet flags similar to the HDLC protocol, with the special flag byte 0x7E inserted in the serial stream to mark packet ends. A flag byte is always inserted immediately after the 
last byte of each packet, and also optionally just before the first byte of packets, if the interval from the previous packet was longer than a certain time period.

### Byte stuffing
To make the flag byte 0x7E unique in the serial stream, the Serial Packet uses 'byte stuffing' borrowed from the HDLC protocol. This allows the protocol to resync on next packet boundary, in case of line errors. This byte stuffing is done using the escape byte 0X7D

| Packet byte | Wire sequence | Comments            |
| :---------- | :------------ | :------------------ |
| 0x7E        | 0x7D, 0x5E    | Escaped flag byte   |
| 0x7D        | 0x75, 0x5D    | Escaped escape byte |
| Other bytes | No change     | The common case     |


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
| 5            | OUT_OF_RANGE     | A more specific invalid argument.    |
| 6 - 99       | Reserved         | For future protocol definitions.     |
| 100-255      | Custom           | For user's application specific use. |

## Example

TBD

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




