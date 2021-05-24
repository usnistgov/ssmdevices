import labbench as lb
from typing import Any, Optional


class SpirentGSS8000(lb.SerialDevice):

    def __init__(
        self,
        resource: str='str',
        timeout: str='int',
        write_termination: str='bytes',
        baud_rate: str='int',
        parity: str='bytes',
        stopbits: str='int',
        xonxoff: str='bool',
        rtscts: str='bool',
        dsrdtr: str='bool'
    ):
        ...
    resource: Any = ...

    def get_key(self, key: Any, trait_name: Optional[Any]=...):
        ...

    def load_scenario(self, path: Any) -> None:
        ...

    def save_scenario(self, folderpath: Any) -> None:
        ...

    @staticmethod
    def fix_path_name(path: Any):
        ...

    def write(self, key: Any, returns: Optional[Any]=...):
        ...

    def query(self, command: Any):
        ...

    def run(self) -> None:
        ...

    def end(self) -> None:
        ...

    def rewind(self) -> None:
        ...

    def abort(self) -> None:
        ...

    def reset(self) -> None:
        ...

    def utc_time(self):
        ...

    def running(self):
        ...

    def status(self):
        ...