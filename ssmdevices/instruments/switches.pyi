from _typeshed import Incomplete
from labbench import DotNetDevice


class MiniCircuitsUSBSwitch(DotNetDevice):

    def __init__(self, resource: str='str'):
        ...
    backend: Incomplete

    def open(self) -> None:
        ...

    def close(self) -> None:
        ...
