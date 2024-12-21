import time
import serial
import logging
import traceback
import struct as s
import threading as t

class ArgusDriver:
    
    __log = logging.getLogger(__file__)
    __running = False
    
    __HEAD = 0xFF
    __DEVICE_ID = 0xFC
    __COMPLEMENT = 257 - __DEVICE_ID
    
    __FUNC_REPORT_SPEED = 0x0A
    __FUNC_REPORT_ENCODER = 0x0D
    __FUNC_MOTOR = 0x10
    __FUNC_MOTION = 0x12
    __FUNC_SET_MOTOR_PID = 0x13
    __FUNC_UART_SERVO = 0x20
    __FUNC_UART_SERVO_ID = 0x21


    def __init__(self, com="/dev/myserial", delay=.002, report=False):
        # Open serial
        try:
            self.conn = serial.Serial(com, 115200)
            self.__delay = delay
        
            self.__encoder_m1 = 0
            self.__encoder_m2 = 0
            self.__encoder_m3 = 0
            self.__encoder_m4 = 0
            
            self.__vl = 0.0
            self.__vr = 0.0
            self.__rpml = 0.0
            self.__rpmr = 0.0
            self.__v = 0.0
            self.__wz = 0.0
            
            if self.conn.isOpen():
                self.__log.info(f"open serial with {com}")
            else:
                self.__log.info(f"serial open failed!")
                
            if report:
                self.setup_receive_thread()
        except Exception as e:
            self.__log.error(f"Error {e} -- {traceback.format_exc()}")
            exit(1)

        time.sleep(self.__delay)

    def set_motor_speed(self, speed1, speed2, speed3, speed4):
        try:
            a = bytearray(s.pack('b', self.__limit_motor_value(speed1)))
            b = bytearray(s.pack('b', self.__limit_motor_value(speed2)))
            c = bytearray(s.pack('b', self.__limit_motor_value(speed3)))
            d = bytearray(s.pack('b', self.__limit_motor_value(speed4)))
            
            cmd = [self.__HEAD, self.__DEVICE_ID, 0x00, self.__FUNC_MOTOR, a[0], b[0], c[0], d[0]]
            cmd[2] = len(cmd) - 2
            checksum = sum(cmd, self.__COMPLEMENT) & 0xFF
            cmd.append(checksum)
            self.__send_data(cmd)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def set_motion_speed(self, v_l: float, v_r: float):
        try:
            a = bytearray(s.pack('f', v_l))
            b = bytearray(s.pack('f', v_r))
            
            cmd = [self.__HEAD, self.__DEVICE_ID, 0x00, self.__FUNC_MOTION, a[0], a[1], a[2], a[3], b[0], b[1], b[2], b[3]]
            cmd[2] = len(cmd) - 2
            checksum = sum(cmd, self.__COMPLEMENT) & 0xFF
            cmd.append(checksum)
            self.__send_data(cmd)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def set_arm_servo_id(self, servo_id):
        try:
            if servo_id < 1 or servo_id > 250:
                return
            
            cmd = [self.__HEAD, self.__DEVICE_ID, 0x04, self.__FUNC_UART_SERVO_ID, int(servo_id)]
            checksum = sum(cmd, self.__COMPLEMENT) & 0xff
            cmd.append(checksum)
            self.__send_data(cmd)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def move_arm_servo(self, servo_id, pulse_value, runtime=500):
        try:
            if servo_id < 1 or pulse_value < 96 or pulse_value > 4000 or runtime < 0:
                return
            
            if runtime > 2000:
                runtime = 2000
            if runtime < 0:
                runtime = 0
            
            s_id = int(servo_id) & 0xff
            value = bytearray(s.pack('h', int(pulse_value)))
            r_time = bytearray(s.pack('h', int(runtime)))
            
            cmd = [self.__HEAD, self.__DEVICE_ID, 0x00, self.__FUNC_UART_SERVO, s_id, value[0], value[1], r_time[0], r_time[1]]
            cmd[2] = len(cmd) - 1
            checksum = sum(cmd, self.__COMPLEMENT) & 0xff
            cmd.append(checksum)
            self.__send_data(cmd)
            time.sleep(self.__delay)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def get_motor_encoder(self):
        m1, m2, m3, m4 = self.__encoder_m1, self.__encoder_m2, self.__encoder_m3, self.__encoder_m4
        return m1, m2, m3, m4

    def get_motion_data(self):
        vl, vr, v, wz, rpml, rpmr = self.__vl, self.__vr, self.__v, self.__wz, self.__rpml, self.__rpmr
        return vl, vr, v, wz, rpml, rpmr

    def __limit_motor_value(self, value):
        if value > 100:
            value = 100
        elif value < -100:
            value = -100

        return int(value)

    def __send_data(self, data):
        self.__log.debug(f"Data: {bytes(data)}")
        self.conn.write(bytes(data))

    def __parse_data(self, function, ext_data):
        if function == self.__FUNC_REPORT_SPEED:
            self.__vl = round(s.unpack('f', bytearray(ext_data[0:4]))[0], 3)
            self.__vr = round(s.unpack('f', bytearray(ext_data[4:8]))[0], 3)
            self.__v = round(s.unpack('f', bytearray(ext_data[8:12]))[0], 3)
            self.__wz = round(s.unpack('f', bytearray(ext_data[12:16]))[0], 3)
            self.__rpml = round(s.unpack('f', bytearray(ext_data[16:20]))[0], 3)
            self.__rpmr = round(s.unpack('f', bytearray(ext_data[20:24]))[0], 3)
        
        elif function == self.__FUNC_REPORT_ENCODER:
            self.__encoder_m1 = s.unpack('i', bytearray(ext_data[0:4]))[0]
            self.__encoder_m2 = s.unpack('i', bytearray(ext_data[4:8]))[0]
            self.__encoder_m3 = s.unpack('i', bytearray(ext_data[8:12]))[0]
            self.__encoder_m4 = s.unpack('i', bytearray(ext_data[12:16]))[0]

    def __receive_data(self):
        while True:
            head1 = bytearray(self.conn.read())[0]
            if head1 == self.__HEAD:
                head2 = bytearray(self.conn.read())[0]
                check_sum = 0
                rx_check_sum = 0
                if head2 == self.__DEVICE_ID - 1:
                    ext_len = bytearray(self.conn.read())[0]
                    ext_type = bytearray(self.conn.read())[0]
                    ext_data = []
                    check_sum = ext_len + ext_type
                    data_len = ext_len - 2
                    
                    while len(ext_data) < data_len:
                        value = bytearray(self.conn.read())[0]
                        ext_data.append(value)
                        if len(ext_data) == data_len:
                            rx_check_sum = value
                        else:
                            check_sum = check_sum + value
                            
                    if check_sum % 256 == rx_check_sum:
                        self.__parse_data(ext_type, ext_data)

    def setup_receive_thread(self):
        try:
            if not self.__running:
                self.__receive_task = t.Thread(target=self.__receive_data, name="receive_data_task")
                self.__receive_task.setDaemon(True)
                self.__receive_task.start()
                self.__running = True
                self.__log.info("started `receive_data_task` thread!")
                time.sleep(.05)
        except:
            self.__log.error("create receiver thread with error!")

    def close(self):
        self.conn.close()
        self.__log.info("bye bye!")

    def __del__(self):
        self.close()
