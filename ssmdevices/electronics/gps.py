"""
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
"""
import labbench as lb
from labbench import paramattr as param

__all__ = ["SwiftNavPiksi"]


class SwiftNavPiksi(lb.SerialLoggingDevice):
    baud_rate = param.value.int(
        default=1000000,
        min=1,
    )


if __name__ == "__main__":
    import labbench as lb
    from labbench import paramattr as param
    import time

    lb.debug_to_screen(lb.DEBUG)
    with SwiftNavPiksi.from_hwid(r"USB VID:PID=0403:6014 SER=5") as piksi:
        piksi.start()
        lb.sleep(5)
        piksi.stop()
        result = piksi.fetch()
        print("Received:\n", result)
