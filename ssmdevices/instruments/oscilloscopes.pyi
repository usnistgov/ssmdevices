import labbench as lb
from _typeshed import Incomplete

class RigolOscilloscope(lb.VISADevice):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        open_timeout: str = "NoneType",
        identity_pattern: str = "NoneType",
        timeout: str = "NoneType",
    ): ...
    time_offset: Incomplete
    time_scale: Incomplete

    def open(self, horizontal: bool = ...) -> None: ...
    def fetch(self): ...
    def fetch_rms(self): ...
