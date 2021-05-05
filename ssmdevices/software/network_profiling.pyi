import labbench as lb
from contextlib import AbstractContextManager
from typing import Any, Optional


class _IPerfBase(lb.ShellBackend):

    def __init__(
        self,
        resource: str='NoneType',
        binary_path: str='NoneType',
        timeout: str='int',
        server: str='bool',
        port: str='int',
        bind: str='NoneType',
        format: str='NoneType',
        time: str='NoneType',
        number: str='NoneType',
        interval: str='NoneType',
        udp: str='bool',
        bit_rate: str='NoneType',
        buffer_size: str='NoneType',
        tcp_window_size: str='NoneType',
        nodelay: str='bool',
        mss: str='NoneType'
    ):
        ...
    FLAGS: Any = ...
    resource: Any = ...
    server: Any = ...
    port: Any = ...
    bind: Any = ...
    format: Any = ...
    time: Any = ...
    number: Any = ...
    interval: Any = ...
    udp: Any = ...
    bit_rate: Any = ...
    buffer_size: Any = ...
    tcp_window_size: Any = ...
    nodelay: Any = ...
    mss: Any = ...

    def acquire(self, block: bool=...):
        ...


class IPerf3(_IPerfBase):

    def __init__(
        self,
        resource: str='NoneType',
        binary_path: str='str',
        timeout: str='int',
        server: str='bool',
        port: str='int',
        bind: str='NoneType',
        format: str='NoneType',
        time: str='NoneType',
        number: str='NoneType',
        interval: str='NoneType',
        udp: str='bool',
        bit_rate: str='NoneType',
        buffer_size: str='NoneType',
        tcp_window_size: str='NoneType',
        nodelay: str='bool',
        mss: str='NoneType',
        reverse: str='bool',
        json: str='bool',
        zerocopy: str='bool'
    ):
        ...
    FLAGS: Any = ...
    reverse: Any = ...
    json: Any = ...
    zerocopy: Any = ...


class IPerf2(_IPerfBase):

    def __init__(
        self,
        resource: str='NoneType',
        binary_path: str='str',
        timeout: str='int',
        server: str='bool',
        port: str='int',
        bind: str='NoneType',
        format: str='NoneType',
        time: str='NoneType',
        number: str='NoneType',
        interval: str='NoneType',
        udp: str='bool',
        bit_rate: str='NoneType',
        buffer_size: str='NoneType',
        tcp_window_size: str='NoneType',
        nodelay: str='bool',
        mss: str='NoneType',
        bidirectional: str='bool',
        report_style: str='str'
    ):
        ...
    FLAGS: Any = ...
    bidirectional: Any = ...
    report_style: Any = ...

    def acquire(self, block: bool=...):
        ...

    def read_stdout(self):
        ...


class IPerf2OnAndroid(IPerf2):

    def __init__(
        self,
        resource: str='NoneType',
        binary_path: str='str',
        timeout: str='int',
        server: str='bool',
        port: str='int',
        bind: str='NoneType',
        format: str='NoneType',
        time: str='NoneType',
        number: str='NoneType',
        interval: str='NoneType',
        udp: str='bool',
        bit_rate: str='NoneType',
        buffer_size: str='NoneType',
        tcp_window_size: str='NoneType',
        nodelay: str='bool',
        mss: str='NoneType',
        bidirectional: str='bool',
        report_style: str='str',
        remote_binary_path: str='str'
    ):
        ...
    remote_binary_path: Any = ...

    def acquire(self, block: bool=...):
        ...

    def open(self) -> None:
        ...

    def kill(self, wait_time: int=...) -> None:
        ...

    def read_stdout(self):
        ...

    def wait_for_cell_data(self, timeout: int=...) -> None:
        ...

    def reboot(self, block: bool=...) -> None:
        ...

    def wait_for_device(self, timeout: int=...) -> None:
        ...


class IPerf2BoundPair(IPerf2):

    def __init__(
        self,
        binary_path: str='str',
        timeout: str='int',
        server: str='str',
        port: str='int',
        bind: str='NoneType',
        format: str='NoneType',
        time: str='NoneType',
        number: str='NoneType',
        interval: str='NoneType',
        udp: str='bool',
        bit_rate: str='NoneType',
        buffer_size: str='NoneType',
        tcp_window_size: str='NoneType',
        nodelay: str='bool',
        mss: str='NoneType',
        bidirectional: str='bool',
        report_style: str='str',
        client: str='str'
    ):
        ...
    resource: Any = ...
    server: Any = ...
    client: Any = ...
    children: Any = ...
    backend: Any = ...

    def open(self) -> None:
        ...

    def close(self) -> None:
        ...

    def kill(self) -> None:
        ...

    def running(self):
        ...

    def start(self) -> None:
        ...

    def read_stdout(self):
        ...


class ClosedLoopBenchmark(lb.Device):

    def __init__(
        self,
        resource: str='str',
        server: str='str',
        client: str='str',
        receiver: str='str',
        port: str='int',
        timeout: str='int',
        tcp_nodelay: str='bool',
        sync_each: str='bool',
        delay: str='int'
    ):
        ...
    server: Any = ...
    client: Any = ...
    receiver: Any = ...
    port: Any = ...
    resource: Any = ...
    timeout: Any = ...
    tcp_nodelay: Any = ...
    sync_each: Any = ...
    delay: Any = ...

    def close(self) -> None:
        ...

    def start(self, buffer_size: Any, count: Optional[Any]=..., duration: Optional[Any]=...) -> None:
        ...

    def is_running(self):
        ...

    def get(self):
        ...

    def stop(self):
        ...


class suppress_matching_arg0(AbstractContextManager):

    def __init__(self, *exceptions: Any, arg0: Optional[Any]=...) -> None:
        ...

    def __enter__(self) -> None:
        ...

    def __exit__(self, exctype: Any, excinst: Any, exctb: Any):
        ...


class ServerConnectionError(ConnectionError):
    ...


class ClientConnectionError(ConnectionError):
    ...


class PortBusyError(ConnectionError):
    ...


class ClosedLoopTCPBenchmark(ClosedLoopBenchmark):

    def __init__(
        self,
        resource: str='str',
        server: str='str',
        client: str='str',
        receiver: str='str',
        port: str='int',
        timeout: str='int',
        tcp_nodelay: str='bool',
        sync_each: str='bool',
        delay: str='int'
    ):
        ...
    port_winerrs: Any = ...
    conn_winerrs: Any = ...

    def acquire(self, buffer_size: Any, count: Optional[Any]=..., duration: Optional[Any]=...):
        ...

    def mss(self):
        ...

    def mtu(self):
        ...

    def wait_for_interfaces(self, timeout: Any):
        ...
