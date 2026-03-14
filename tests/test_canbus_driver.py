import time
import pytest
import logging

from argus.driver import CanbusDriver


log = logging.getLogger(__file__)


tty = "/dev/tty.usbmodem206B358043331"


def test_ping():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    msg1 = driver.ping()

    assert msg1 is not None
    assert msg1.get_value() == "OK!"

    log.info(msg1)

    time.sleep(1)

    driver.close()


def test_double_ping():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

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


def test_move_motor():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.set_motor_speed(0, 500)

    time.sleep(5)

    driver.motor_stop(0)

    driver.close()


def test_move_serial_servo():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.move_serial_servo(1, 2000, 500)

    msg = driver.get_servo_angle(1)

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_get_encoder_values_not_none():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    msg = driver.get_encoder_values()

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_set_motor_speed_500_and_get_encoder_values():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.set_motor_speed(0, 500)

    time.sleep(5)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] != 0.0

    log.info(msg)

    time.sleep(2)

    driver.motor_stop(0)

    time.sleep(1)

    driver.close()


def test_move_pwm_servo():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.move_pwm_servo(0, 90)

    time.sleep(1)

    driver.close()


def test_move_pwm_servo_boundary_angles():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.move_pwm_servo(0, 0)

    time.sleep(1)

    driver.move_pwm_servo(0, 90)

    time.sleep(1)

    driver.move_pwm_servo(0, 180)

    time.sleep(1)

    driver.close()


def test_move_pwm_servo_multiple_servos():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.move_pwm_servo(0, 45)

    time.sleep(1)

    driver.move_pwm_servo(3, 135)

    time.sleep(1)

    driver.close()


def test_get_imu_values_not_none():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    msg = driver.get_imu_values()

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_get_imu_values_twice():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    msg1 = driver.get_imu_values()

    assert msg1 is not None

    log.info(msg1)

    msg2 = driver.get_imu_values()

    assert msg2 is not None

    log.info(msg2)

    time.sleep(1)

    driver.close()


def test_double_move_serial_servo():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

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


def test_get_battery_data_not_none():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    msg = driver.get_battery_data()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert len(values) == 2

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_get_battery_data_twice():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    msg1 = driver.get_battery_data()

    assert msg1 is not None

    log.info(msg1)

    msg2 = driver.get_battery_data()

    assert msg2 is not None

    log.info(msg2)

    time.sleep(1)

    driver.close()


def test_pid_set_gains():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.pid_set_gains(0, kp=7.8049, ki=10.5174, kd=0.0)


def test_pid_set_rpm():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.pid_set_rpm(0, 30.0)

    time.sleep(5)

    driver.pid_motor_stop(0)

    driver.close()


def test_pid_set_rpm_with_encoder():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.pid_set_rpm(0, 90.0)

    time.sleep(10)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] != 0.0

    log.info(msg)

    driver.pid_motor_stop(0)

    time.sleep(1)

    driver.close()


def test_pid_motor_stop():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.pid_set_rpm(0, 100.0)

    time.sleep(2)

    driver.pid_motor_stop(0)

    time.sleep(2)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] == pytest.approx(0.0, abs=5.0)

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_pid_motor_stop_with_brake():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.pid_set_rpm(0, 100.0)

    time.sleep(2)

    driver.pid_motor_stop(0, brake=1)

    time.sleep(2)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] == pytest.approx(0.0, abs=5.0)

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_pid_move_forward_with_gains():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.pid_set_gains(0, kp=7.8049, ki=10.5174, kd=0.0)

    driver.pid_set_rpm(0, 30.0)

    time.sleep(5)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] != 0.0

    log.info(msg)

    driver.pid_motor_stop(0)

    time.sleep(1)

    driver.close()


def test_pid_set_gains_multiple_motors():
    driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

    driver.pid_set_gains(0, kp=7.8049, ki=10.5174, kd=0.0)
    driver.pid_set_gains(1, kp=7.8049, ki=10.5174, kd=0.02)

    driver.pid_set_rpm(0, 100.0)
    driver.pid_set_rpm(1, 100.0)

    time.sleep(2)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] != 0.0
    assert values[1] != 0.0

    log.info(msg)

    driver.pid_motor_stop(0)
    driver.pid_motor_stop(1)

    time.sleep(1)

    driver.close()
