"""
Motor open-loop step experiment.

Drives motor 1 at a series of PWM pulse values, recording (time, pwm, rpm)
for DURATION seconds per step. Output is written to a CSV compatible with
the adjust_gains.ipynb notebook.

Usage (serial):
    uv run python scripts/motor_experiment.py --driver serial --tty /dev/tty.usbserial-2130

Usage (CAN bus):
    uv run python scripts/motor_experiment.py --driver canbus --tty /dev/tty.usbmodem206B358043331

Optional flags:
    --motor-id   Motor channel to drive (default: 1)
    --pulses     Space-separated PWM pulse values (default: 200 400 600 800 1000)
    --duration   Seconds to record per pulse step (default: 10)
    --interval   Seconds between encoder polls (default: 0.2)
    --output     Output CSV path (default: motor_data.csv)
"""

import argparse
import csv
import time
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def build_driver(args):
    if args.driver == "serial":
        from argus.driver import SerialDriver

        return SerialDriver(args.tty, report=True)
    else:
        from argus.driver import CanbusDriver

        return CanbusDriver(interface="slcan", channel=args.tty, bitrate=500000)


def run_experiment(
    driver,
    motor_id: int,
    pulses: list[int],
    duration: float,
    interval: float,
    output: str,
):
    rows: list[dict] = []
    t_origin = time.monotonic()

    for pwm in pulses:
        log.info(f"Step: PWM={pwm}  ({duration}s)")

        driver.set_motor_speed(motor_id, pwm)
        t_step_end = time.monotonic() + duration

        while True:
            now = time.monotonic()
            if now >= t_step_end:
                break
            elapsed = now - t_origin

            msg = driver.get_encoder_values()
            if msg is not None:
                values = msg.get_value()
                rpm = values[motor_id - 1]
                rows.append(
                    {"time": round(elapsed, 4), "pwm": pwm, "rpm": round(rpm, 4)}
                )
                log.debug(f"  t={elapsed:.2f}s  pwm={pwm}  rpm={rpm:.2f}")
            elapsed = time.monotonic() - t_origin

            time.sleep(interval)

    driver.motor_stop(motor_id)

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["time", "pwm", "rpm"])
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"Saved {len(rows)} samples to '{output}'")


def main():
    parser = argparse.ArgumentParser(description="Motor open-loop step experiment")
    parser.add_argument("--driver", choices=["serial", "canbus"], default="serial")
    parser.add_argument("--tty", required=True, help="Serial port or CAN channel")
    parser.add_argument("--motor-id", type=int, default=1, dest="motor_id")
    parser.add_argument(
        "--pulses",
        type=int,
        nargs="+",
        default=[200, 400, 600, 800, 1000],
        help="PWM pulse values to sweep (default: 200 400 600 800 1000)",
    )
    parser.add_argument(
        "--duration", type=float, default=10.0, help="Seconds per step (default: 10)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.2,
        help="Encoder poll interval in seconds (default: 0.2)",
    )
    parser.add_argument(
        "--output",
        default="motor_data.csv",
        help="Output CSV file (default: motor_data.csv)",
    )
    args = parser.parse_args()

    log.info(f"Driver: {args.driver}  TTY: {args.tty}")
    log.info(f"Motor ID: {args.motor_id}  Pulses: {args.pulses}")
    log.info(f"Duration: {args.duration}s/step  Poll interval: {args.interval}s")

    driver = build_driver(args)

    try:
        run_experiment(
            driver,
            motor_id=args.motor_id,
            pulses=args.pulses,
            duration=args.duration,
            interval=args.interval,
            output=args.output,
        )
    except KeyboardInterrupt:
        log.warning("Interrupted — stopping motor and closing driver")
        driver.motor_stop(args.motor_id)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
