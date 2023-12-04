import labbench as lb
from labbench import paramattr as attr
from _typeshed import Incomplete

class SwiftNavPiksi(lb.SerialLoggingDevice):
    def __init__(
        self,
        resource: str = "str",
        timeout: str = "int",
        write_termination: str = "bytes",
        baud_rate: str = "int",
        parity: str = "bytes",
        stopbits: str = "int",
        xonxoff: str = "bool",
        rtscts: str = "bool",
        dsrdtr: str = "bool",
        poll_rate: str = "float",
        data_format: str = "bytes",
        stop_timeout: str = "float",
        max_queue_size: str = "int",
    ): ...
    baud_rate: Incomplete
