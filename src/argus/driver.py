import can
import time
import queue
import struct
import serial
import logging
import threading as t


from abc import ABC, abstractmethod

from argus.isotp_receiver import IsoTpReceiver
from argus.isotp_sender import IsoTpSender


def __crc16_ccitt(data, crc: int = 0xFFFF) -> int:
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


def __consume(instance, queue):
    time.sleep(0.1)

    while True:
        item = queue.get()
        if isinstance(item, instance):
            yield item
            break
        if item is None:
            break
        queue.task_done()
    queue.task_done()


class Response:

    def __init__(self, message) -> None:
        self.message = message

    def get_value(self):
        return self.message

    def __str__(self) -> str:
        return f"Message: {self.message}"


class EncoderResponse(Response):
    pass


class Driver(ABC):

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def ping(self) -> Response:
        pass

    @abstractmethod
    def set_motor_speed(self, motor_id: int, speed: int) -> Response:
        pass

    @abstractmethod
    def motor_stop(self, motor_id: int) -> Response:
        pass

    @abstractmethod
    def move_serial_servo(self, servo_id: int, pulse: int, time: int) -> Response:
        pass

    @abstractmethod
    def get_serial_servo_angle(self, servo_id: int):
        pass

    @abstractmethod
    def get_encoder_values(self) -> EncoderResponse:
        pass

    @abstractmethod
    def close(self):
        pass


class SerialDriver(Driver):
    __log = logging.getLogger(__file__)
    __running = False
    __HEAD = 0xAA

    __MESSAGE = [0x01, 0x02]

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

            self.messages = queue.Queue(-1)

            if report:
                self.setup_receive_thread()
            self.connected = True
        except Exception as e:
            self.__log.error(f"Error {e}")
            raise Exception("Error connecting to serial")

        time.sleep(self.__delay)

    def is_connected(self) -> bool:
        return self.connected

    def ping(self) -> Response:
        try:
            data = [0xAA, 0x01, 0x00, 0x2E, 0x3E, 0x55]
            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        return next(__consume(Response, self.messages))

    def set_motor_speed(self, motor_id: int, speed: int):
        try:
            payload = [
                0x02,
                0x03,
                motor_id & 0xFF,
                (int(speed) >> 8) & 0xFF,
                int(speed) & 0xFF,
            ]

            crc = __crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        return next(__consume(Response, self.messages))

    def motor_stop(self, motor_id: int):
        try:
            payload = [
                0x03,
                0x02,
                motor_id & 0xFF,
                0x00,
            ]

            crc = __crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        return next(__consume(Response, self.messages))

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

            crc = __crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        return next(__consume(Response, self.messages))

    def get_serial_servo_angle(self, servo_id: int):
        try:
            payload = [
                0x06,
                0x01,
                servo_id & 0xFF,
            ]

            crc = __crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

    def get_encoder_values(self) -> EncoderResponse:
        try:
            payload = [
                0x07,
                0x00,
            ]

            crc = __crc16_ccitt(payload)

            data = [0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55]

            self.__send_data(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        return next(__consume(EncoderResponse, self.messages))

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
        if hasattr(self, "conn") and self.conn is not None:
            self.conn.close()
        self.__log.info("bye bye!")

    def __del__(self):
        self.close()

    def __parse_data(self, function, ext_data):
        if function == 0x01:
            msg = Response("".join(chr(h) for h in ext_data))
            self.messages.put(msg)

        if function == 0x02 and len(ext_data) == 16:
            latest_rpm = [0.0] * 4
            latest_rpm[0] = struct.unpack("<f", bytes(ext_data[:4]))[0]
            latest_rpm[1] = struct.unpack("<f", bytes(ext_data[4:8]))[0]
            latest_rpm[2] = struct.unpack("<f", bytes(ext_data[8:12]))[0]
            latest_rpm[3] = struct.unpack("<f", bytes(ext_data[12:16]))[0]

            msg = EncoderResponse(tuple(latest_rpm))
            self.messages.put(msg)

        # TODO: Implement the response for get_serial_servo_angle

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
                        crc = __crc16_ccitt([type, lenx, *payload])

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
            self.__log.error(f"Error: {e}")


class CanbusDriver(ABC):
    __log = logging.getLogger(__file__)

    def __init__(self, interface: str, channel: str, bitrate: int) -> None:
        self.interface = interface
        self.channel = channel
        self.bitrate = bitrate

        self.__log.info(
            f"Opening CAN bus: {self.interface} {self.channel} @ {self.bitrate}"
        )

        try:
            self.canbus = self._make_canbus()

            self.sender = IsoTpSender(self.canbus, tx_id=0x700, fc_id=0x701)
            self.receiver = IsoTpReceiver(
                self.canbus, rx_id=0x702, fc_id=0x701, on_message=self.on_msg
            )

            self.messages = queue.Queue(-1)
            self.receiver.start()
        except Exception as e:
            self.__log.error(f"Ex: {e}")
            raise Exception("Error connecting to canbus")

    def _make_canbus(self):
        kwargs = dict(interface=self.interface, channel=self.channel)
        if self.interface.lower() in ("slcan", "pcan", "kvaser"):
            kwargs["bitrate"] = str(self.bitrate)
        return can.Bus(**kwargs, ignore_config=False)

    def ping(self):
        try:
            data = bytes([0xAA, 0x01, 0x00, 0x2E, 0x3E, 0x55])
            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        return next(__consume(Response, self.messages))

    def set_motor_speed(self, motor_id: int, speed: int):
        try:
            payload = [
                0x02,
                0x03,
                motor_id & 0xFF,
                (int(speed) >> 8) & 0xFF,
                int(speed) & 0xFF,
            ]

            crc = __crc16_ccitt(payload)

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

    def motor_stop(self, motor_id: int):
        try:
            payload = [
                0x03,
                0x02,
                motor_id & 0xFF,
                0x00,
            ]

            crc = __crc16_ccitt(payload)

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

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

            crc = __crc16_ccitt(payload)

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

    def get_serial_servo_angle(self, servo_id: int):
        try:
            payload = [
                0x06,
                0x01,
                servo_id & 0xFF,
            ]

            crc = __crc16_ccitt(payload)

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

    def get_encoder_values(self):
        try:
            payload = [
                0x07,
                0x00,
            ]

            crc = __crc16_ccitt(payload)

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        return next(__consume(EncoderResponse, self.messages))

    def on_msg(self, payload: bytes):
        if payload[1] == 0x01:
            len = payload[2]
            msg = Response("".join(chr(h) for h in payload[3 : 3 + len]))
            self.messages.put(msg)

        if payload[1] == 0x02 and payload[2] == 16:
            latest_rpm = [0.0] * 4
            latest_rpm[0] = struct.unpack("<f", bytes(payload[3:7]))[0]
            latest_rpm[1] = struct.unpack("<f", bytes(payload[7:11]))[0]
            latest_rpm[2] = struct.unpack("<f", bytes(payload[11:15]))[0]
            latest_rpm[3] = struct.unpack("<f", bytes(payload[15:19]))[0]

            msg = EncoderResponse(tuple(latest_rpm))
            self.messages.put(msg)

    def close(self):
        try:
            if hasattr(self, "receiver") and self.receiver:
                self.receiver.stop()
        except Exception as e:
            self.__log.error(f"Ex: {e}")

        time.sleep(0.01)

        try:
            if hasattr(self, "canbus") and self.canbus and not self.canbus._is_shutdown:
                self.canbus.shutdown()
        except Exception as e:
            self.__log.error(f"Ex: {e}")

    def __del__(self):
        self.close()
