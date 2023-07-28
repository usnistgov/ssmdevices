import labbench as lb


class AndroidDebugBridge(lb.ShellBackend):

    def __init__(self, resource: str='str', binary_path: str='NoneType', timeout: str='int'):
        ...

    def devices(self):
        ...

    def is_device_connected(self, serialNum):
        ...

    def reboot(self, deviceId) -> None:
        ...

    def check_airplane_mode(self, deviceId):
        ...

    def set_airplane_mode(self, deviceId, status) -> None:
        ...

    def push_file(self, deviceId, local_filepath, device_filepath) -> None:
        ...
