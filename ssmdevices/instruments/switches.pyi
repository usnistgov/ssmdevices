from labbench import DotNetDevice
from typing import Any


class MiniCircuitsUSBSwitch(DotNetDevice):

    def __init__(self, resource: str='str'):
        ...
    backend: Any = ...

    def open(self) -> None:
        ...

    def close(self) -> None:
        ...

    def port(self, value: Any) -> None:
        ...
