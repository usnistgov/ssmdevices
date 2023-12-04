import labbench as lb
from labbench import paramattr as attr
from _typeshed import Incomplete

class RohdeSchwarzZMBSeries(lb.VISADevice):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        open_timeout: str = "NoneType",
        identity_pattern: str = "NoneType",
        timeout: str = "NoneType",
    ): ...
    initiate_continuous: Incomplete

    def clear(self) -> None: ...
    def save_trace_to_csv(self, path, trace: int = ...) -> None: ...
    def trigger(self) -> None: ...
