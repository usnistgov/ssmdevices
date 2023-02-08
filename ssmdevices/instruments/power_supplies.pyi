import labbench as lb
from _typeshed import Incomplete

class RigolDP800Series(lb.VISADevice):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
    ): ...
    REMAP_BOOL: Incomplete
    enable1: Incomplete
    enable2: Incomplete
    enable3: Incomplete
    voltage_setting1: Incomplete
    voltage_setting2: Incomplete
    voltage_setting3: Incomplete
    voltage1: Incomplete
    voltage2: Incomplete
    voltage3: Incomplete
    current1: Incomplete
    current2: Incomplete
    current3: Incomplete

    def open(self) -> None: ...
    def get_key(self, scpi_key, trait_name: Incomplete | None = ...): ...
    def set_key(self, scpi_key, value, trait_name: Incomplete | None = ...): ...
