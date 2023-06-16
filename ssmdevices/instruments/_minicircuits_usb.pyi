import labbench as lb
from _typeshed import Incomplete

class MiniCircuitsUSBDevice(lb.Device):
    def __init__(
        self,
        resource: str = "NoneType",
        usb_path: str = "NoneType",
        timeout: str = "int",
    ): ...
    resource: Incomplete
    usb_path: Incomplete
    timeout: Incomplete
    backend: Incomplete

    def open(self) -> None: ...
    def close(self) -> None: ...

class SwitchAttenuatorBase(MiniCircuitsUSBDevice):
    def __init__(
        self,
        resource: str = "NoneType",
        usb_path: str = "NoneType",
        timeout: str = "int",
    ): ...
    CMD_GET_PART_NUMBER: int
    CMD_GET_SERIAL_NUMBER: int

    def model(self): ...
    def serial_number(self): ...
