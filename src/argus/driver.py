import time
import serial
import logging
import traceback
import threading as t


class Driver:
    __log = logging.getLogger(__file__)
    __running = False
    __HEAD = 0xAA

    __MESSAGE = 0x01

    __latest_message = ""

    def __init__(
        self,
        com="/dev/tty.usbserial-2130",
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
                (speed >> 8) & 0xFF,
                speed & 0xFF,
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

    def get_latest_message(self):
        return self.__latest_message

    def __send_data(self, data):
        self.__log.debug(f"Data: {bytes(data)}")
        self.conn.write(bytes(data))

    def close(self):
        self.conn.close()
        self.__log.info("bye bye!")

    def __del__(self):
        self.close()

    def __parse_data(self, function, ext_data):
        if function == self.__MESSAGE:
            self.__latest_message = "".join(chr(h) for h in ext_data)

    def __receive_data(self):
        while True:
            head = bytearray(self.conn.read())[0]
            if head == self.__HEAD:
                type = bytearray(self.conn.read())[0]
                crc = 0
                rx_crc = 0
                if type == self.__MESSAGE:
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
                        self.__parse_data(type, payload)
            else:
                time.sleep(0.05)

    def setup_receive_thread(self):
        try:
            if not self.__running:
                self.__receive_task = t.Thread(
                    target=self.__receive_data, name="receive_data_task"
                )
                self.__receive_task.daemon = True
                self.__receive_task.start()
                self.__running = True
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
