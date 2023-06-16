import labbench as lb
from _typeshed import Incomplete


class TM500Error(ValueError):
    errcode: Incomplete

    def __init__(self, msg, errcode: Incomplete | None=...) -> None:
        ...


class AeroflexTM500(lb.TelnetDevice):

    def __init__(
        self,
        resource: str='str',
        timeout: str='int',
        ack_timeout: str='int',
        busy_retries: str='int',
        remote_ip: str='str',
        remote_ports: str='str',
        min_acquisition_time: str='int',
        port: str='int',
        config_root: str='str',
        data_root: str='str',
        convert_files: str='list'
    ):
        ...
    timeout: Incomplete
    ack_timeout: Incomplete
    busy_retries: Incomplete
    remote_ip: Incomplete
    remote_ports: Incomplete
    min_acquisition_time: Incomplete
    port: Incomplete
    config_root: Incomplete
    data_root: Incomplete
    convert_files: Incomplete

    def arm(self, scenario_name):
        ...

    def trigger(self):
        ...

    def stop(self, convert: bool=...):
        ...

    def reboot(self, timeout: int=...) -> None:
        ...

    @staticmethod
    def command_log_to_script(path) -> None:
        ...

    def close(self) -> None:
        ...

    def open(self) -> None:
        ...
