import time
import logging

from argus.driver import Driver


log = logging.getLogger(__file__)


def test_ping():
    driver = Driver("/dev/tty.usbserial-2130", report=True)
    driver.ping()

    time.sleep(0.1)

    msg = driver.get_latest_message()

    assert msg == "OK!"

    log.info(msg)


def test_set_motor_speed1():
    driver = Driver("/dev/tty.usbserial-2130", report=True)
    driver.set_motor_speed(2, 600)

    time.sleep(0.1)

    msg = driver.get_latest_message()

    assert msg == "OK!"

    log.info(msg)


def test_motor_stop():
    driver = Driver("/dev/tty.usbserial-2130", report=True)
    driver.motor_stop(2)

    time.sleep(0.5)

    msg = driver.get_latest_message()

    assert msg == "OK!"

    log.info(msg)


def test_move_serial_servo1():
    driver = Driver("/dev/tty.usbserial-2130", report=True)
    driver.move_serial_servo(1, 2000, 500)

    time.sleep(0.1)

    msg = driver.get_latest_message()

    assert msg == "OK!"

    log.info(msg)


def test_move_serial_servo2():
    driver = Driver("/dev/tty.usbserial-2130", report=True)
    driver.move_serial_servo(1, 3999, 500)

    time.sleep(0.1)

    msg = driver.get_latest_message()

    assert msg == "OK!"

    log.info(msg)


def test_get_serial_servo_angle():
    driver = Driver("/dev/tty.usbserial-2130", report=True)
    driver.get_serial_servo_angle(1)

    time.sleep(0.1)

    msg = driver.get_latest_message()

    log.info(msg)


def test_get_get_encoder_values():
    driver = Driver("/dev/tty.usbserial-2130", report=True)
    driver.get_encoder_values()

    time.sleep(0.1)

    rpms = driver.get_latest_rpm()
    log.info(rpms)
