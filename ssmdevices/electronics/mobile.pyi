import labbench as lb
from typing import Any


class AndroidDebugBridge(lb.ShellBackend):

    def __init__(self, resource: str='str', binary_path: str='str', timeout: str='int'):
        ...

    def devices(self):
        ...

    def is_device_connected(self, serialNum: Any):
        ...

    def reboot(self, deviceId: Any) -> None:
        ...

    def check_airplane_mode(self, deviceId: Any):
        ...

    def set_airplane_mode(self, deviceId: Any, status: Any) -> None:
        ...

    def push_file(self, deviceId: Any, local_filepath: Any, device_filepath: Any) -> None:
        ...
