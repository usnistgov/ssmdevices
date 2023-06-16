import labbench as lb
from _typeshed import Incomplete


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
    resource: Incomplete

    def get_key(self, key, trait_name: Incomplete | None=...):
        ...

    def load_scenario(self, path) -> None:
        ...

    def save_scenario(self, folderpath) -> None:
        ...

    @staticmethod
    def fix_path_name(path):
        ...

    def write(self, key, returns: Incomplete | None=...):
        ...

    def query(self, command):
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
