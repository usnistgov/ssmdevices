import labbench as lb
from typing import Any


class RohdeSchwarzZMBSeries(lb.VISADevice):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str'
    ):
        ...
    initiate_continuous: Any = ...

    def clear(self) -> None:
        ...

    def save_trace_to_csv(self, path: Any, trace: int=...) -> None:
        ...

    def trigger(self) -> None:
        ...
