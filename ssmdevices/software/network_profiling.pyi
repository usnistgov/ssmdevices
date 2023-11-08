import labbench as lb
from labbench import paramattr as param
from _typeshed import Incomplete
from contextlib import AbstractContextManager

class _IPerfBase(lb.ShellBackend):
    def __init__(
        self,
        resource: str = "NoneType",
        binary_path: str = "NoneType",
        timeout: str = "int",
        server: str = "bool",
        port: str = "int",
        bind: str = "NoneType",
        format: str = "NoneType",
        time: str = "NoneType",
        number: str = "NoneType",
        interval: str = "NoneType",
        udp: str = "bool",
        bit_rate: str = "NoneType",
        buffer_size: str = "NoneType",
        tcp_window_size: str = "NoneType",
        nodelay: str = "bool",
        mss: str = "NoneType",
    ): ...
    FLAGS: Incomplete
    resource: Incomplete
    server: Incomplete
    port: Incomplete
    bind: Incomplete
    format: Incomplete
    time: Incomplete
    number: Incomplete
    interval: Incomplete
    udp: Incomplete
    bit_rate: Incomplete
    buffer_size: Incomplete
    tcp_window_size: Incomplete
    nodelay: Incomplete
    mss: Incomplete

    def profile(self, block: bool = ...): ...

class IPerf3(_IPerfBase):
    def __init__(
        self,
        resource: str = "NoneType",
        binary_path: str = "str",
        timeout: str = "int",
        server: str = "bool",
        port: str = "int",
        bind: str = "NoneType",
        format: str = "NoneType",
        time: str = "NoneType",
        number: str = "NoneType",
        interval: str = "NoneType",
        udp: str = "bool",
        bit_rate: str = "NoneType",
        buffer_size: str = "NoneType",
        tcp_window_size: str = "NoneType",
        nodelay: str = "bool",
        mss: str = "NoneType",
        reverse: str = "bool",
        json: str = "bool",
        zerocopy: str = "bool",
    ): ...
    FLAGS: Incomplete
    reverse: Incomplete
    json: Incomplete
    zerocopy: Incomplete

class IPerf2(_IPerfBase):
    def __init__(
        self,
        resource: str = "NoneType",
        binary_path: str = "str",
        timeout: str = "int",
        server: str = "bool",
        port: str = "int",
        bind: str = "NoneType",
        format: str = "NoneType",
        time: str = "NoneType",
        number: str = "NoneType",
        interval: str = "NoneType",
        udp: str = "bool",
        bit_rate: str = "NoneType",
        buffer_size: str = "NoneType",
        tcp_window_size: str = "NoneType",
        nodelay: str = "bool",
        mss: str = "NoneType",
        bidirectional: str = "bool",
        report_style: str = "str",
    ): ...
    FLAGS: Incomplete
    DATAFRAME_COLUMNS: Incomplete
    bidirectional: Incomplete
    report_style: Incomplete

    def profile(self, block: bool = ...): ...
    def read_stdout(self): ...

class IPerf2OnAndroid(IPerf2):
    def __init__(
        self,
        resource: str = "NoneType",
        binary_path: str = "str",
        timeout: str = "int",
        server: str = "bool",
        port: str = "int",
        bind: str = "NoneType",
        format: str = "NoneType",
        time: str = "NoneType",
        number: str = "NoneType",
        interval: str = "NoneType",
        udp: str = "bool",
        bit_rate: str = "NoneType",
        buffer_size: str = "NoneType",
        tcp_window_size: str = "NoneType",
        nodelay: str = "bool",
        mss: str = "NoneType",
        bidirectional: str = "bool",
        report_style: str = "str",
        remote_binary_path: str = "str",
    ): ...
    remote_binary_path: Incomplete

    def profile(self, block: bool = ...): ...
    def open(self) -> None: ...
    def kill(self, wait_time: int = ...) -> None: ...
    def read_stdout(self): ...
    def wait_for_cell_data(self, timeout: int = ...) -> None: ...
    def reboot(self, block: bool = ...) -> None: ...
    def wait_for_device(self, timeout: int = ...) -> None: ...

class IPerf2BoundPair(IPerf2):
    def __init__(
        self,
        binary_path: str = "NoneType",
        timeout: str = "int",
        server: str = "str",
        port: str = "int",
        bind: str = "NoneType",
        format: str = "NoneType",
        time: str = "NoneType",
        number: str = "NoneType",
        interval: str = "NoneType",
        udp: str = "bool",
        bit_rate: str = "NoneType",
        buffer_size: str = "NoneType",
        tcp_window_size: str = "NoneType",
        nodelay: str = "bool",
        mss: str = "NoneType",
        bidirectional: str = "bool",
        report_style: str = "str",
        client: str = "str",
    ): ...
    resource: Incomplete
    server: Incomplete
    client: Incomplete
    children: Incomplete
    backend: Incomplete

    def open(self) -> None: ...
    def close(self) -> None: ...
    def kill(self) -> None: ...
    def running(self): ...
    def profile(self, block: bool = ..., **kws): ...
    def read_stdout(self, client_ret: Incomplete | None = ...): ...

class TrafficProfiler_ClosedLoop(lb.Device):
    def __init__(
        self,
        resource: str = "str",
        server: str = "str",
        client: str = "str",
        receive_side: str = "str",
        port: str = "int",
        timeout: str = "int",
        tcp_nodelay: str = "bool",
        sync_each: str = "bool",
        delay: str = "int",
    ): ...
    server: Incomplete
    client: Incomplete
    receive_side: Incomplete
    port: Incomplete
    resource: Incomplete
    timeout: Incomplete
    tcp_nodelay: Incomplete
    sync_each: Incomplete
    delay: Incomplete

    def close(self) -> None: ...
    def start(
        self,
        buffer_size,
        count: Incomplete | None = ...,
        duration: Incomplete | None = ...,
    ) -> None: ...
    def is_running(self): ...
    def get(self): ...
    def stop(self): ...

class suppress_matching_arg0(AbstractContextManager):
    def __init__(self, *exceptions, arg0: Incomplete | None = ...) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self, exctype, excinst, exctb): ...

class ServerConnectionError(ConnectionError): ...
class ClientConnectionError(ConnectionError): ...
class PortBusyError(ConnectionError): ...

class TrafficProfiler_ClosedLoopTCP(TrafficProfiler_ClosedLoop):
    def __init__(
        self,
        resource: str = "str",
        server: str = "str",
        client: str = "str",
        receive_side: str = "str",
        port: str = "int",
        timeout: str = "int",
        tcp_nodelay: str = "bool",
        sync_each: str = "bool",
        delay: str = "int",
    ): ...
    PORT_WINERRS: Incomplete
    CONN_WINERRS: Incomplete

    def profile_count(self, buffer_size: int, count: int): ...
    def profile_duration(self, buffer_size: int, duration: float): ...
    def mss(self): ...
    def mtu(self): ...
    def wait_for_interfaces(self, timeout): ...
