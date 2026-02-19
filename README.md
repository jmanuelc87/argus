# Argus

A robotics control system for the [Transbot](https://www.yahboom.net/study/Transbot) robot. Argus provides hardware abstraction for controlling DC motors, servos, and reading encoders via Serial or CAN Bus (ISO-TP) communication protocols, along with a Tkinter-based UI for real-time control.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Connected Transbot hardware (serial port or CAN interface)

## Installation

```bash
uv sync
```

## Usage

### Launch the control UI

```bash
uv run ui
```

The UI provides tabbed panels for:

- **Settings** — Select transport (Serial or CAN), connect/disconnect
- **Servo Controller** — Control 3 servos with pulse range 100–3900
- **Motor Controller** — Control 4 DC motors (speed ±2000) with live encoder feedback

### Run tests

Tests require physical hardware to be connected.

```bash
# Run all tests
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_serial_driver.py::test_ping -v
```

## Architecture

```
src/argus/
├── driver.py           # Abstract Driver + SerialDriver & CanbusDriver
├── isotp_sender.py     # ISO-TP multi-frame sender over CAN
├── isotp_receiver.py   # ISO-TP multi-frame receiver over CAN
└── ui.py               # Tkinter control UI
```

### Driver Layer

An abstract `Driver` base class defines the hardware interface (`ping`, `set_motor_speed`, `motor_stop`, `move_serial_servo`, `get_servo_angle`, `get_encoder_values`, `close`). Two concrete implementations are provided:

- **SerialDriver** — Custom binary protocol over serial at 115200 baud. Messages use a header/footer framing with CRC16-CCITT checksums. Incoming messages are processed on a daemon thread and buffered in a queue.
- **CanbusDriver** — ISO-TP over CAN bus (TX `0x700`, RX `0x702`, FC `0x701`). Supports single and multi-frame messages with flow control.

### ISO-TP

A minimal ISO-TP implementation supporting 11-bit CAN IDs. Handles Single Frames (≤7 bytes) and First/Consecutive Frames for larger payloads, with configurable STmin flow control delays. Thread-safe.

## License

See [LICENSE](LICENSE) for details.
