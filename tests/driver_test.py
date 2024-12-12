import time
import pytest
import logging

from argus.driver import ArgusDriver


log = logging.getLogger(__file__)


def test_set_motor_speed():
    driver = ArgusDriver(com='COM6')
    driver.set_motor_speed(0, 5, 0, 5)


def test_set_car_motion():
    driver = ArgusDriver(com='COM6')
    driver.set_car_motion(0.3, 0.3)


def test_set_pid_param():
    driver = ArgusDriver(com='COM6')
    
    kp = 0.8
    ki = 0.06
    kd = 0.5
    
    driver.set_pid_param(kp, ki, kd)
    driver.set_car_motion(v_l=0.1, v_r=0.1)
    time.sleep(1)
    for _ in range(10):
        vel = driver.get_motion_data()
        log.info(f"vel: {vel}")
        time.sleep(0.25)
    time.sleep(3)
    driver.set_car_motion(0, 0)


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