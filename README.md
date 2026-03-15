# Argus

A robotics control system for the [Transbot](https://www.yahboom.net/study/Transbot) robot. Argus provides hardware abstraction for controlling DC motors, servos, and reading encoders via Serial or CAN Bus (ISO-TP) communication protocols.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Connected Transbot hardware (serial port or CAN interface)

## Installation

```bash
uv sync
```

## Usage

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
└── isotp_receiver.py   # ISO-TP multi-frame receiver over CAN
```

### Driver Layer

An abstract `Driver` base class defines the hardware interface:

| Method | Description |
|---|---|
| `ping()` | Check connection |
| `set_motor_speed(motor_id, speed)` | Set DC motor speed (±2000) |
| `motor_stop(motor_id, brake)` | Stop a motor |
| `move_serial_servo(servo_id, pulse, time2move)` | Move serial servo (pulse 100–3900) |
| `get_servo_angle(servo_id)` | Read servo angle |
| `get_encoder_values()` | Read RPM for all 4 motors |
| `move_pwm_servo(servo_id, angle)` | Move PWM servo by angle |
| `get_imu_values()` | Read IMU sensor data |
| `pid_set_rpm(motor_id, rpm)` | Set motor RPM via PID |
| `pid_motor_stop(motor_id, brake)` | Stop PID-controlled motor |
| `pid_set_gains(motor_id, kp, ki, kd, save)` | Configure PID gains |
| `get_battery_data()` | Read battery voltage and percentage |
| `close()` | Close the connection |

Two concrete implementations are provided:

- **SerialDriver** — Custom binary protocol over serial at 115200 baud. Messages use header `0xAA`, function code, length, payload, CRC16-CCITT checksum, and footer `0x55`. Incoming messages are processed on a daemon thread and buffered in a queue.
- **CanbusDriver** — ISO-TP over CAN bus (TX `0x700`, RX `0x702`, FC `0x701`). Uses integrated `IsoTpSender`/`IsoTpReceiver`.

### Response Types

- `Response` — Base message wrapper
- `EncoderResponse` — RPM tuple for 4 motors (little-endian 32-bit floats)
- `ServoResponse` — Servo angle (32-bit float)
- `ImuResponse` — IMU sensor data
- `BatteryResponse` — Voltage and percentage

### ISO-TP

A minimal ISO-TP implementation supporting 11-bit CAN IDs. Handles Single Frames (≤7 bytes) and First/Consecutive Frames for larger payloads, with configurable STmin flow control delays. Thread-safe.

### Utilities

- `Iter.consume()` — Generator that blocks on queue until a matching message type arrives, requeuing non-matching messages
- `_crc16_ccitt()` — CRC-16 CCITT (polynomial `0x1021`, initial `0xFFFF`)
- `_validate_bolt_frame()` — Validates bolt frame structure and checksum

## Scripts

```bash
uv run python scripts/motor_experiment.py \
  --driver canbus \
  --tty /dev/tty.usbmodem206B358043331 \
  --pulses 300 900 600 1200 \
  --duration 10 \
  --output motor_data.csv
```

## License

See [LICENSE](LICENSE) for details.
