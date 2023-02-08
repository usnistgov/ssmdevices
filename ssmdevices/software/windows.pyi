import labbench as lb
from _typeshed import Incomplete


class WLANInfo(lb.ShellBackend):

    def __init__(
        self,
        resource: str='str',
        binary_path: str='str',
        timeout: str='int',
        only_bssid: str='bool',
        interface: str='NoneType'
    ):
        ...
    FLAGS: Incomplete
    only_bssid: Incomplete
    interface: Incomplete

    def wait(self) -> None:
        ...

    def get_wlan_ssids(self, interface):
        ...

    def get_wlan_interfaces(self, name: Incomplete | None=..., param: Incomplete | None=...):
        ...


class WLANClient(lb.Device):

    def __init__(self, resource: str='str', ssid: str='NoneType', timeout: str='int'):
        ...
    resource: Incomplete
    ssid: Incomplete
    timeout: Incomplete
    backend: Incomplete

    def open(self) -> None:
        ...

    @classmethod
    def list_available_clients(cls, by: str=...):
        ...

    @classmethod
    def __imports__(cls) -> None:
        ...

    def interface_connect(self):
        ...

    def interface_disconnect(self):
        ...

    def interface_reconnect(self):
        ...

    def state(self):
        ...

    def isup(self):
        ...

    def transmit_rate_mbps(self):
        ...

    def signal(self):
        ...

    def description(self):
        ...

    def channel(self):
        ...

    def refresh(self) -> None:
        ...
