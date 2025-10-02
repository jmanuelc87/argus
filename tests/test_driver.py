import time
import logging

from argus.driver import Driver


log = logging.getLogger(__file__)


def test_ping():
    driver = Driver(report=True)
    driver.ping()

    time.sleep(0.1)

    msg = driver.get_latest_message()

    assert msg == "OK!"

    log.info(msg)
