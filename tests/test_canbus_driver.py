import time
import logging

from argus.driver import CanbusDriver


log = logging.getLogger(__file__)


def test_ping():
    driver = CanbusDriver(
        interface="slcan", channel="/dev/tty.usbmodem206B358043331", bitrate=500000
    )

    msg = driver.ping()

    assert msg == "OK!"

    log.info(msg)

    time.sleep(1)

    driver.close()
