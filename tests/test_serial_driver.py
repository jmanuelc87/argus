import time
import logging

from argus.driver import SerialDriver


log = logging.getLogger(__file__)


def test_ping():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    msg = driver.ping()

    assert msg == "OK!"

    log.info(msg)

    driver.close()


def test_set_motor_speed1():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    msg = driver.set_motor_speed(2, 600)

    assert msg == "OK!"

    log.info(msg)

    driver.close()


def test_motor_stop():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    msg = driver.motor_stop(2)

    assert msg == "OK!"

    log.info(msg)

    driver.close()


def test_move_serial_servo1():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    msg = driver.move_serial_servo(1, 2000, 500)

    assert msg == "OK!"

    log.info(msg)

    driver.close()


def test_move_serial_servo2():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    msg = driver.move_serial_servo(1, 3999, 500)

    assert msg == "OK!"

    log.info(msg)

    driver.close()


def test_get_serial_servo_angle():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    driver.get_serial_servo_angle(1)

    time.sleep(0.1)

    # msg = driver.get_latest_message()

    # log.info(msg)


def test_get_get_encoder_values():
    driver = SerialDriver("/dev/tty.usbserial-2130", report=True)
    msg = driver.get_encoder_values()

    log.info(msg)
