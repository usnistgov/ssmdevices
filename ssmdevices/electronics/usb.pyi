import labbench as lb
from _typeshed import Incomplete

class AcronameUSBHub2x4(lb.Device):
    def __init__(self, resource: str = "NoneType"): ...
    model: int
    data0_enabled: Incomplete
    data1_enabled: Incomplete
    data2_enabled: Incomplete
    data3_enabled: Incomplete
    power0_enabled: Incomplete
    power1_enabled: Incomplete
    power2_enabled: Incomplete
    power3_enabled: Incomplete
    resource: Incomplete
    backend: Incomplete

    def open(self) -> None: ...
    def close(self) -> None: ...
    def set_key(self, key, value, name: Incomplete | None = ...) -> None: ...
    def enable(
        self, data: bool = ..., power: bool = ..., channel: str = ...
    ) -> None: ...
