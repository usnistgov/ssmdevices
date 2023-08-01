import labbench as lb
from _typeshed import Incomplete


class AcronamePropertyAdapter(lb.BackendPropertyAdapter):

    def set(self, device, key: tuple, value, trait: Incomplete | None=...):
        ...

    def get(self, device, key: tuple, trait: Incomplete | None=...):
        ...


class AcronameUSBHub2x4(lb.Device):

    def __init__(self, resource: str='NoneType'):
        ...
    MODEL: int
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

    def open(self) -> None:
        ...

    def close(self) -> None:
        ...
