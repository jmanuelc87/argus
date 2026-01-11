import time
import logging

from argus.driver import SerialDriver


log = logging.getLogger(__file__)


def test_ping():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    msg = driver.ping()

    assert msg.get_value() == "OK!"

    log.info(msg)

    driver.close()


def test_set_motor_speed1():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    driver.set_motor_speed(2, 600)
    time.sleep(1)
    driver.close()


def test_motor_stop():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    driver.motor_stop(2)
    time.sleep(1)
    driver.close()


def test_move_serial_servo1():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    driver.move_serial_servo(1, 2000, 500)
    time.sleep(1)
    driver.close()


def test_move_serial_servo2():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    driver.move_serial_servo(1, 3999, 500)
    time.sleep(1)
    driver.close()
