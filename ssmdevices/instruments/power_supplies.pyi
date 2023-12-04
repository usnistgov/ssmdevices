import labbench as lb
from labbench import paramattr as attr
from _typeshed import Incomplete

class rigol_property_adapter(attr.property.visa_keying):
    def get(self, device: lb.Device, scpi_key: str, trait_name: Incomplete | None = ...): ...
    def set(
        self,
        device: lb.Device,
        scpi_key: str,
        value,
        trait_name: Incomplete | None = ...,
    ): ...

class RigolDP800Series(lb.VISADevice):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        open_timeout: str = "NoneType",
        identity_pattern: str = "NoneType",
        timeout: str = "NoneType",
    ): ...
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
