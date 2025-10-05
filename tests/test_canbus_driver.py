import time
import logging

from argus.canbus import Driver


log = logging.getLogger(__file__)


def test_ping():
    driver = Driver(
        interface="slcan", channel="/dev/tty.usbmodem206B358043331", bitrate=500000
    )
    driver.ping()

    time.sleep(0.1)

    msg = driver.get_latest_message()

    assert msg == "OK!"

    log.info(msg)

    time.sleep(1)

    driver.close()
