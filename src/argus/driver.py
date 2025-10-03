import time
import struct
import serial
import logging
import traceback
import threading as t


class Driver:
    __log = logging.getLogger(__file__)
    __running = False
    __HEAD = 0xAA

    __MESSAGE = [0x01, 0x02]

    __latest_message = ""
    __latest_rpm = [0.0] * 4

    def __init__(
        self,
        com,
        delay=0.002,
        report=False,
    ) -> None:
        try:
            self.conn = serial.Serial(com, 115200)
            self.__delay = delay

            if self.conn.is_open:
                self.__log.info(f"open serial with {com}")
            else:
                self.__log.info("serial open failed!")

            if report:
                self.setup_receive_thread()
        except Exception as e:
            self.__log.error(f"Error {e} -- {traceback.format_exc()}")
            exit(1)

        time.sleep(self.__delay)

    def ping(self):
        try:
            data = [0xAA, 0x01, 0x00, 0x2E, 0x3E, 0x55]
            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def set_motor_speed(self, motor_id: int, speed: int):
        try:
            payload = [
                0x02,
                0x03,
                motor_id & 0xFF,
                (int(speed) >> 8) & 0xFF,
                int(speed) & 0xFF,
            ]

            crc = self.__crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def motor_stop(self, motor_id: int):
        try:
            payload = [
                0x03,
                0x02,
                motor_id & 0xFF,
                0x00,
            ]

            crc = self.__crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def move_serial_servo(self, servo_id: int, pulse: int, time: int):
        try:
            payload = [
                0x05,
                0x05,
                servo_id & 0xFF,
                (pulse >> 8) & 0xFF,
                pulse & 0xFF,
                (time >> 8) & 0xFF,
                time & 0xFF,
            ]

            crc = self.__crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def get_serial_servo_angle(self, servo_id: int):
        try:
            payload = [
                0x06,
                0x01,
                servo_id & 0xFF,
            ]

            crc = self.__crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def get_encoder_values(self):
        try:
            payload = [
                0x07,
                0x00,
            ]

            crc = self.__crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def get_latest_message(self):
        return self.__latest_message

    def get_latest_rpm(self):
        return self.__latest_rpm

    def __send_data(self, data):
        if self.conn.is_open:
            try:
                self.__log.debug(f"Data: {[hex(d) for d in data]}")
                self.conn.write(bytes(data))
            except Exception as e:
                self.__log.error(f"Ex: {e}")

    def close(self):
        self.__running = False
        time.sleep(0.1)
        self.conn.close()
        self.__log.info("bye bye!")

    def __del__(self):
        self.close()

    def __parse_data(self, function, ext_data):
        if function == 0x01:
            self.__latest_message = "".join(chr(h) for h in ext_data)

        if function == 0x02 and len(ext_data) == 16:
            self.__latest_rpm[0] = struct.unpack("<f", bytes(ext_data[:4]))[0]
            self.__latest_rpm[1] = struct.unpack("<f", bytes(ext_data[4:8]))[0]
            self.__latest_rpm[2] = struct.unpack("<f", bytes(ext_data[8:12]))[0]
            self.__latest_rpm[3] = struct.unpack("<f", bytes(ext_data[12:16]))[0]

    def __receive_data(self):
        while self.__running:
            if not self.conn.is_open:
                time.sleep(0.5)
                continue

            try:
                head = bytearray(self.conn.read())[0]
                if head == self.__HEAD:
                    type = bytearray(self.conn.read())[0]
                    crc = 0
                    rx_crc = 0
                    if type in self.__MESSAGE:
                        lenx = bytearray(self.conn.read())[0]

                        payload = []

                        while len(payload) < lenx:
                            value = bytearray(self.conn.read())[0]
                            payload.append(value)

                        crc1 = bytearray(self.conn.read())[0]
                        crc2 = bytearray(self.conn.read())[0]

                        rx_crc = (crc1 << 8) | crc2
                        crc = self.__crc16_ccitt([type, lenx, *payload])

                        if crc == rx_crc:
                            self.__log.debug(payload)
                            self.__parse_data(type, payload)
                else:
                    time.sleep(0.05)
            except Exception as e:
                self.__log.error(f"Ex: {e}")

    def setup_receive_thread(self):
        try:
            if not self.__running:
                self.__running = True
                self.__receive_task = t.Thread(
                    target=self.__receive_data, name="receive_data_task"
                )
                self.__receive_task.daemon = True
                self.__receive_task.start()
                self.__log.info("started `receive_data` thread!")
                time.sleep(0.05)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def __crc16_ccitt(self, data, crc: int = 0xFFFF) -> int:
        """
        Compute CRC16-CCITT (polynomial 0x1021, initial value 0xFFFF).
        """
        for i in data:
            crc ^= i << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc
