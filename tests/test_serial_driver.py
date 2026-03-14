import time
import pytest
import logging

from argus.driver import SerialDriver


log = logging.getLogger(__file__)


tty = "/dev/tty.usbserial-2130"


def test_ping():
    driver = SerialDriver(tty, report=True)
    msg = driver.ping()

    assert msg is not None
    assert msg.get_value() == "OK!"

    log.info(msg)

    driver.close()


def test_double_ping():
    driver = SerialDriver(tty, report=True)

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


def test_set_motor_speed():
    driver = SerialDriver(tty, report=True)

    driver.set_motor_speed(0, 2000)

    time.sleep(5)

    driver.motor_stop(0)

    driver.close()


def test_motor_stop():
    driver = SerialDriver(tty, report=True)
    driver.motor_stop(1)
    time.sleep(1)
    driver.close()


def test_move_serial_servo():
    driver = SerialDriver(tty, report=True)

    driver.move_serial_servo(1, 2000, 500)

    msg = driver.get_servo_angle(1)

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_get_encoder_values_not_none():
    driver = SerialDriver(tty, report=True)

    msg = driver.get_encoder_values()

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_get_encoder_values_with_motor_forward():
    driver = SerialDriver(tty, report=True)

    driver.set_motor_speed(0, 2000)

    time.sleep(2)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] != 0.0

    log.info(msg)

    driver.motor_stop(0)

    time.sleep(1)

    driver.close()


def test_set_motor_speed_500_and_get_encoder_values():
    driver = SerialDriver(tty, report=True)

    driver.set_motor_speed(0, 500)

    time.sleep(2)

    msg = driver.get_encoder_values()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert values[0] != 0.0

    log.info(msg)

    driver.motor_stop(0)

    time.sleep(1)

    driver.close()


def test_move_pwm_servo():
    driver = SerialDriver(tty, report=True)

    driver.move_pwm_servo(1, 90)

    time.sleep(1)

    driver.close()


def test_move_pwm_servo_boundary_angles():
    driver = SerialDriver(tty, report=True)

    driver.move_pwm_servo(1, 0)

    time.sleep(1)

    driver.move_pwm_servo(1, 90)

    time.sleep(1)

    driver.move_pwm_servo(1, 180)

    time.sleep(1)

    driver.close()


def test_move_pwm_servo_multiple_servos():
    driver = SerialDriver(tty, report=True)

    driver.move_pwm_servo(1, 45)

    time.sleep(1)

    driver.move_pwm_servo(2, 135)

    time.sleep(1)

    driver.close()


def test_get_imu_values_not_none():
    driver = SerialDriver(tty, report=True)

    msg = driver.get_imu_values()

    assert msg is not None

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_get_imu_values_twice():
    driver = SerialDriver(tty, report=True)

    msg1 = driver.get_imu_values()

    assert msg1 is not None

    log.info(msg1)

    msg2 = driver.get_imu_values()

    assert msg2 is not None

    log.info(msg2)

    time.sleep(1)

    driver.close()


def test_double_move_serial_servo():
    driver = SerialDriver(tty, report=True)

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
    driver = SerialDriver(tty, report=True)

    msg = driver.get_battery_data()

    assert msg is not None

    values = msg.get_value()

    assert isinstance(values, tuple)
    assert len(values) == 2

    log.info(msg)

    time.sleep(1)

    driver.close()


def test_get_battery_data_twice():
    driver = SerialDriver(tty, report=True)

    msg1 = driver.get_battery_data()

    assert msg1 is not None

    log.info(msg1)

    msg2 = driver.get_battery_data()

    assert msg2 is not None

    log.info(msg2)

    time.sleep(1)

    driver.close()


def test_pid_set_rpm():
    driver = SerialDriver(tty, report=True)

    driver.pid_set_rpm(0, 100.0)

    time.sleep(5)

    driver.pid_motor_stop(0)

    driver.close()


def test_pid_set_rpm_with_encoder():
    driver = SerialDriver(tty, report=True)

    driver.pid_set_rpm(0, 100.0)

    time.sleep(2)

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
    driver = SerialDriver(tty, report=True)

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
    driver = SerialDriver(tty, report=True)

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


def test_pid_set_gains():
    driver = SerialDriver(tty, report=True)

    driver.pid_set_gains(0, kp=1.0, ki=0.1, kd=0.01)

    driver.pid_set_rpm(0, 100.0)

    time.sleep(2)

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
    driver = SerialDriver(tty, report=True)

    driver.pid_set_gains(0, kp=1.0, ki=0.1, kd=0.01)
    driver.pid_set_gains(1, kp=2.0, ki=0.2, kd=0.02)

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
