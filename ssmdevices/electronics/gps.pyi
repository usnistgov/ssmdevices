"""
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
"""
import labbench as lb
from labbench import paramattr as attr
__all__ = ['SwiftNavPiksi']


class SwiftNavPiksi(lb.SerialLoggingDevice):

    def __init__(
        self,
        resource: str='NoneType',
        timeout: str='int',
        write_termination: str='bytes',
        baud_rate: str='int',
        parity: str='bytes',
        stopbits: str='int',
        xonxoff: str='bool',
        rtscts: str='bool',
        dsrdtr: str='bool',
        poll_rate: str='float',
        data_format: str='bytes',
        stop_timeout: str='float',
        max_queue_size: str='int'
    ):
        ...
    baud_rate: int = attr.value.int(default=1000000, min=1)
if __name__ == '__main__':
    import labbench as lb
    from labbench import paramattr as attr
    import time
    lb.debug_to_screen(lb.DEBUG)
    with SwiftNavPiksi.from_hwid('USB VID:PID=0403:6014 SER=5') as piksi:
        piksi.start()
        lb.sleep(5)
        piksi.stop()
        result = piksi.fetch()
        print('Received:\n', result)
