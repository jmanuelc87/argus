import can
import time
import struct
import logging
import traceback


from argus.isotp_receiver import IsoTpReceiver
from argus.isotp_sender import IsoTpSender


class Driver:
    __log = logging.getLogger(__file__)

    __latest_message = ""
    __latest_rpm = [0.0] * 4

    def __init__(self, interface: str, channel: str, bitrate: int) -> None:
        self.interface = interface
        self.channel = channel
        self.bitrate = bitrate

        self.__log.info(
            f"Opening CAN bus: {self.interface} {self.channel} @ {self.bitrate}"
        )
        self.canbus = self._make_canbus()

        self.sender = IsoTpSender(self.canbus, tx_id=0x700, fc_id=0x701)
        self.receiver = IsoTpReceiver(
            self.canbus, rx_id=0x702, fc_id=0x701, on_message=self.on_msg
        )

        self.receiver.start()

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

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
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

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
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

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
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

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def get_encoder_values(self):
        try:
            payload = [
                0x07,
                0x00,
            ]

            crc = self.__crc16_ccitt(payload)

            data = bytes([0xAA, *payload, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])

            self.sender.send(data)
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def get_latest_message(self):
        try:
            return self.__latest_message
        finally:
            self.__latest_message = ""

    def get_latest_rpm(self):
        return self.__latest_rpm

    def on_msg(self, payload: bytes):
        if payload[1] == 0x01:
            len = payload[2]
            self.__latest_message = "".join(chr(h) for h in payload[3 : 3 + len])

        if payload[1] == 0x02 and payload[2] == 16:
            self.__latest_rpm[0] = struct.unpack("<f", bytes(payload[3:7]))[0]
            self.__latest_rpm[1] = struct.unpack("<f", bytes(payload[7:11]))[0]
            self.__latest_rpm[2] = struct.unpack("<f", bytes(payload[11:15]))[0]
            self.__latest_rpm[3] = struct.unpack("<f", bytes(payload[15:19]))[0]

    def close(self):
        try:
            if self.receiver:
                self.receiver.stop()
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

        time.sleep(0.01)

        try:
            if self.canbus and not self.canbus._is_shutdown:
                self.canbus.shutdown()
        except Exception as e:
            self.__log.error(f"Ex: {e} -- {traceback.format_exc()}")

    def __del__(self):
        self.close()

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
