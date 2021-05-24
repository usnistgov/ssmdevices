import labbench as lb
from typing import Any


class RigolOscilloscope(lb.VISADevice):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str'
    ):
        ...
    time_offset: Any = ...
    time_scale: Any = ...

    def open(self, horizontal: bool=...) -> None:
        ...

    def fetch(self):
        ...

    def fetch_rms(self):
        ...