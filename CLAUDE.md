# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Argus is a robotics control system for the Transbot robot. It provides hardware abstraction for controlling DC motors, servos, and reading encoders via Serial or CAN Bus (ISO-TP) communication protocols, with a Tkinter-based UI for real-time control.

## Commands

```bash
# Install dependencies
uv sync

# Run all tests (requires connected hardware)
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_serial_driver.py::test_ping -v

# Launch the control UI
uv run ui
```

## Architecture

### Driver Layer (`src/argus/driver.py`)

Abstract `Driver` base class defines the hardware interface: `ping()`, `set_motor_speed()`, `motor_stop()`, `move_serial_servo()`, `get_servo_angle()`, `get_encoder_values()`, `move_pwm_servo()`, `get_imu_values()`, `pid_set_rpm()`, `pid_motor_stop()`, `pid_set_gains()`, `get_battery_data()`, `close()`.

Two implementations:

- **SerialDriver** — Custom binary protocol over serial (115200 baud). Messages use header `0xAA`, function code, length, payload, CRC16-CCITT checksum, footer `0x55`. Async receive via daemon thread with queue-based message buffering.
- **CanbusDriver** — ISO-TP over CAN bus. TX ID `0x700`, RX ID `0x702`, Flow Control ID `0x701`. Uses integrated `IsoTpSender`/`IsoTpReceiver`.

### ISO-TP (`src/argus/isotp_sender.py`, `src/argus/isotp_receiver.py`)

Minimal ISO-TP implementation supporting 11-bit CAN IDs. Handles Single Frames (≤7 bytes), First/Consecutive Frames for multi-frame messages, and Flow Control with STmin delays. Thread-safe with daemon threads.

### Response Types (`src/argus/driver.py`)

- `Response` — Base message wrapper
- `EncoderResponse` — RPM tuple for 4 motors (little-endian 32-bit floats)
- `ServoResponse` — Servo angle (32-bit float)
- `ImuResponse` — IMU sensor data
- `BatteryResponse` — Voltage and percentage

### Utilities (`src/argus/driver.py`)

- `Iter.consume()` — Generator that blocks on queue until matching message type arrives, requeues non-matching messages
- `_crc16_ccitt()` — CRC-16 CCITT (polynomial 0x1021, initial 0xFFFF)

## Testing

Tests require physical hardware (serial port or CAN interface). Pytest is configured with DEBUG-level CLI logging and file logging to `logs/pytest_run.log`.
