import labbench as lb
from _typeshed import Incomplete

class ETSLindgrenAzi2005(lb.VISADevice):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        timeout: str = "int",
        baud_rate: str = "int",
        parity: str = "bytes",
        stopbits: str = "int",
        xonxoff: str = "bool",
        rtscts: str = "bool",
        dsrdtr: str = "bool",
    ): ...
    timeout: Incomplete
    baud_rate: Incomplete
    parity: Incomplete
    stopbits: Incomplete
    xonxoff: Incomplete
    rtscts: Incomplete
    dsrdtr: Incomplete
    read_termination: Incomplete
    write_termination: Incomplete

    def config(self, mode) -> None: ...
    def whereami(self): ...
    def wheredoigo(self): ...
    def set_speed(self, value) -> None: ...
    def set_limits(self, side, value) -> None: ...
    def set_position(self, value) -> None: ...
    def seek(self, value) -> None: ...
    def stop(self) -> None: ...
    speed: Incomplete
    cwlimit: Incomplete
    cclimit: Incomplete
    define_position: Incomplete
    position: Incomplete

    def set_key(self, key, value, trait_name: Incomplete | None = ...) -> None: ...
