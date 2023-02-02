import labbench as lb
from _typeshed import Incomplete


class RigolOscilloscope(lb.VISADevice):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str'
    ):
        ...
    time_offset: Incomplete
    time_scale: Incomplete

    def open(self, horizontal: bool=...) -> None:
        ...

    def fetch(self):
        ...

    def fetch_rms(self):
        ...
