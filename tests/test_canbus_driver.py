import time
import pytest
import logging

from argus.driver import CanbusDriver


log = logging.getLogger(__file__)


def test_ping():
    driver = CanbusDriver(
        interface="slcan", channel="/dev/tty.usbmodem206B358043331", bitrate=500000
    )

    msg1 = driver.ping()

    assert msg1 is not None
    assert msg1.get_value() == "OK!"

    log.info(msg1)

    time.sleep(1)

    driver.close()


def test_double_ping():
    driver = CanbusDriver(
        interface="slcan", channel="/dev/tty.usbmodem206B358043331", bitrate=500000
    )

    msg1 = driver.ping()

    assert msg1 is not None
    assert msg1.get_value() == "OK!"

    log.info(msg1)

    msg2 = driver.ping()

    assert msg2 is not None
    assert msg2.get_value() == "OK!"

    log.info(msg2)

    time.sleep(1)

    driver.close()


def test_move_serial_servo():
    driver = CanbusDriver(
        interface="slcan", channel="/dev/tty.usbmodem206B358043331", bitrate=500000
    )

    driver.move_serial_servo(1, 2000, 500)

    msg = driver.get_servo_angle(1)

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_double_move_serial_servo():
    driver = CanbusDriver(
        interface="slcan", channel="/dev/tty.usbmodem206B358043331", bitrate=500000
    )

    driver.move_serial_servo(1, 2000, 500)

    msg = driver.get_servo_angle(1)

    assert msg is not None

    log.info(msg)

    driver.move_serial_servo(2, 2000, 500)

    msg = driver.get_servo_angle(2)

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()
