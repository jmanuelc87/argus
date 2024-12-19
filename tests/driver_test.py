import time
import pytest
import logging

import pandas as pd

from argus.driver import ArgusDriver


log = logging.getLogger(__file__)


def test_set_motor_speed():
    driver = ArgusDriver(com='COM6')
    driver.set_motor_speed(0, 5, 0, 5)


def test_set_car_motion():
    driver = ArgusDriver(com='COM6')
    driver.set_car_motion(0.3, 0.3)


def test_set_car_motion_with_pos_neg_feedback():
    driver = ArgusDriver(com='COM6', report=True)
    driver.set_motor_speed(0, 100, 0, 100)
    
    for _ in range(10):
        time.sleep(1)
        vel = driver.get_motion_data()
        enc = driver.get_motor_encoder()
        
        log.info(f"{vel}")
        log.info(f"{enc[0]}, {enc[1]}, {enc[2]}, {enc[3]}")
        
    driver.set_motor_speed(0, 0, 0, 0)
    
    time.sleep(0.2)
    
    driver.set_motor_speed(0, -100, 0, -100)
    
    for i in range(10):
        time.sleep(1)
        vel = driver.get_motion_data()
        enc = driver.get_motor_encoder()
        
        log.info(f"{vel}")
        log.info(f"{enc[0]}, {enc[1]}, {enc[2]}, {enc[3]}")

    driver.set_motor_speed(0, 0, 0, 0)


def test_set_car_motion_with_feedback():
    driver = ArgusDriver(com='COM6', report=True)
    driver.set_motor_speed(0, 100, 0, 0)
    
    for _ in range(10):
        time.sleep(1)
        vel = driver.get_motion_data()
        enc = driver.get_motor_encoder()
        
        log.info(f"vl={vel[0]}, vr={vel[1]}, v={vel[2]}, wz={vel[3]}, rpm_l={vel[4]}, rpm_r={vel[5]}")
        log.info(f"m2={enc[1]}, m4={enc[3]}")
        
    driver.set_motor_speed(0, 0, 0, 0)


def test_move_arm_servo():
    driver = ArgusDriver(com='COM6')
    driver.move_arm_servo(3, 1000)


def test_set_id_servo():
    driver = ArgusDriver(com='COM6')
    driver.set_arm_servo_id(3)


def test_linear_interpolation_motors():
    driver = ArgusDriver(com='COM6', report=True)

    motion_data = []

    for i in range(-100, 0, 5):
        driver.set_motor_speed(0, i, 0, i)
        time.sleep(3)
        vel = driver.get_motion_data()
        motion_data.append(list(vel) + [i])

    for i in range(0, 105, 5):
        driver.set_motor_speed(0, i, 0, i)
        time.sleep(3)
        vel = driver.get_motion_data()
        motion_data.append(list(vel) + [i])

    driver.set_motor_speed(0,0,0,0)

    datadf = pd.DataFrame(data=motion_data, columns=['vl', 'vr', 'v', 'wz', 'rpm_l', 'rpm_r', 'pwm'])
    datadf.to_csv("linear_interpolation_motor.csv")
    