import labbench as lb
from typing import Any, Optional


class TM500Error(ValueError):
    errcode: Any = ...

    def __init__(self, msg: Any, errcode: Optional[Any]=...) -> None:
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
    timeout: Any = ...
    ack_timeout: Any = ...
    busy_retries: Any = ...
    remote_ip: Any = ...
    remote_ports: Any = ...
    min_acquisition_time: Any = ...
    port: Any = ...
    config_root: Any = ...
    data_root: Any = ...
    convert_files: Any = ...

    def arm(self, scenario_name: Any):
        ...

    def trigger(self):
        ...

    def stop(self, convert: bool=...):
        ...

    def reboot(self, timeout: int=...) -> None:
        ...

    @staticmethod
    def command_log_to_script(path: Any) -> None:
        ...

    def close(self) -> None:
        ...

    def open(self) -> None:
        ...
