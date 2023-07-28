import labbench as lb
from _typeshed import Incomplete


class QPST(lb.Win32ComDevice):

    def __init__(self, resource: str='str'):
        ...
    PORT_LIST_CODES: Incomplete
    API_ATTR_MAP: Incomplete

    def open(self) -> None:
        ...

    def close(self) -> None:
        ...

    def add_port(self, port):
        ...

    def remove_port(self, port) -> None:
        ...


class QXDM(lb.Win32ComDevice):

    def __init__(self, resource: str='int', cache_path: str='str', connection_timeout: str='int'):
        ...
    resource: Incomplete
    cache_path: Incomplete
    connection_timeout: Incomplete

    def open(self) -> None:
        ...
    ue_model_number: Incomplete
    ue_mode: Incomplete
    ue_imei: Incomplete
    ue_esn: Incomplete
    ue_build_id: Incomplete

    def get_key(self, key, trait_name: Incomplete | None=...):
        ...

    def close(self) -> None:
        ...

    def configure(self, config_path, min_acquisition_time: Incomplete | None=...) -> None:
        ...

    def save(self, path: Incomplete | None=..., saveNm: Incomplete | None=...):
        ...

    def start(self, wait: bool=...) -> None:
        ...

    def version(self):
        ...

    def reconnect(self) -> None:
        ...
