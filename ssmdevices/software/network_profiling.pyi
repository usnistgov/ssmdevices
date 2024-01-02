"""
@authors: Dan Kuester <daniel.kuester@nist.gov>,
         Michael Voecks <michael.voecks@nist.gov>
"""
__all__ = ['IPerf2', 'IPerf3', 'IPerf2OnAndroid', 'IPerf2BoundPair', 'TrafficProfiler_ClosedLoopTCP']
import datetime
import re
import socket
import subprocess as sp
import time
import traceback
from io import StringIO
from queue import Empty, Queue
from threading import Event, Thread
from time import perf_counter
from contextlib import AbstractContextManager, suppress
from ._networking import find_free_port
import labbench as lb
from labbench import paramattr as attr
import pandas as pd
import psutil
import ssmdevices.lib
if __name__ == '__main__':
    from _networking import get_ipv4_address, get_ipv4_occupied_ports, list_network_interfaces
else:
    from ._networking import get_ipv4_address, get_ipv4_occupied_ports, list_network_interfaces
if '_tcp_port_offset' not in dir():
    _tcp_port_offset = 0
perf_counter()


@attr.adjust('timeout', default=5)
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
        time: str='Undefined',
        number: str='Undefined',
        interval: str='Undefined',
        udp: str='bool',
        bit_rate: str='Undefined',
        buffer_size: str='Undefined',
        tcp_window_size: str='Undefined',
        nodelay: str='bool',
        mss: str='Undefined'
    ):
        ...
    FLAGS = dict(
        resource='-c',
        server='-s',
        port='-p',
        interval='-i',
        bind='-B',
        udp='-u',
        bit_rate='-b',
        time='-t',
        number='-n',
        tcp_window_size='-w',
        buffer_size='-l',
        nodelay='-N',
        mss='-M'
    )
    resource: str = attr.value.NetworkAddress(
        None,
        accept_port=False,
        allow_none=True,
        help='client host address (set None if server=True)'
    )
    server: bool = attr.value.bool(default=False, help='True to run as a server')
    port: int = attr.value.int(default=5201, min=0, help='network port')
    bind: str = attr.value.str(default=None, allow_none=True, help='bind connection to specified IP')
    format: str = attr.value.str(
        default=None,
        only=(None, 'k', 'm', 'g', 'K', 'M', 'G'),
        allow_none=True,
        help='data unit prefix in bits (k, m, g), bytes (K, M, G), or None for auto'
    )
    time: float = attr.value.float(
        min=0,
        max=16535,
        allow_none=True,
        help='send duration (s) before quitting (default: 10)'
    )
    number: int = attr.value.int(
        min=-1,
        allow_none=True,
        help='the number of bytes to transmit before quitting'
    )
    interval: float = attr.value.float(
        min=0.01,
        allow_none=True,
        label='s',
        help='seconds between throughput reports'
    )
    udp: bool = attr.value.bool(default=False, help='if True, to use UDP instead of TCP')
    bit_rate: str = attr.value.str(
        allow_none=True,
        label='bits/s',
        help='maximum bit rate, accepts KMG unit suffix; defaults 1Mbit/s UDP, no limit for TCP'
    )
    buffer_size: int = attr.value.int(
        min=1,
        allow_none=True,
        help='buffer size when generating traffic',
        label='bytes'
    )
    tcp_window_size: int = attr.value.int(
        min=1,
        allow_none=True,
        help='window / socket size (default OS dependent?)',
        label='bytes'
    )
    nodelay: bool = attr.value.bool(default=False, help='set True to use nodelay (TCP traffic only)')
    mss: int = attr.value.int(
        min=10,
        allow_none=True,
        help='minimum segment size=MTU-40, TCP only',
        label='bytes'
    )

    def profile(self, block=True):
        self._validate_flags()
        duration = 0 if self.time is None else self.time + 2
        timeout = max((self.timeout, duration))
        return self.run(
            self.FLAGS,
            background=not block,
            pipe=True,
            respawn=not block,
            check_stderr=True,
            timeout=timeout
        )

    def _validate_flags(self):
        """update and validate value traits"""
        if self.server:
            busy_ports = get_ipv4_occupied_ports(self.server)
            while self.port in busy_ports:
                prev_port = self.ports
                if self.port >= self._traits['port'].max:
                    self.port = self._traits['port'].min
                else:
                    self.port = self.port + 1
                self._logger.info(f'requested port {prev_port} is in use - changing to {self.port}')
        if self.resource is not None and self.server:
            raise ValueError(
                'must set exactly one of (a) client operation by setting resource="(hostname here)", or (b) server operation by setting server=True'
            )
        if self.udp:
            if self.mss is not None:
                raise ValueError('the TCP MSS setting is incompatible with UDP')
            if self.nodelay:
                raise ValueError('the TCP nodelay setting is incompatible with UDP')
            if self.buffer_size is not None:
                self._logger.warning(
                    'iperf may work improperly when setting udp=True with buffer_size'
                )
        if not self.udp and self.bit_rate is not None:
            raise ValueError('iperf does not support setting bit_rate in TCP')
        if self.server:
            if self.time is not None:
                raise ValueError('iperf server does not support the `time` argument')
            if self.number is not None:
                raise ValueError('iperf server does not support the `number` argument')


@attr.adjust('binary_path', ssmdevices.lib.path('iperf3.exe'))
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
        time: str='Undefined',
        number: str='Undefined',
        interval: str='Undefined',
        udp: str='bool',
        bit_rate: str='Undefined',
        buffer_size: str='Undefined',
        tcp_window_size: str='Undefined',
        nodelay: str='bool',
        mss: str='Undefined',
        reverse: str='bool',
        json: str='bool',
        zerocopy: str='bool'
    ):
        ...
    """Run an instance of iperf3, collecting output data in a background thread.
    When running as an iperf client (server=False),
    The default value is the path that installs with 64-bit cygwin.
    """
    FLAGS = dict(_IPerfBase.FLAGS, json='-J', reverse='-R', zerocopy='-Z')
    reverse: bool = attr.value.bool(
        default=False,
        help='run in reverse mode (server sends, client receives)'
    )
    json: bool = attr.value.bool(default=False, help='output data in JSON format')
    zerocopy: bool = attr.value.bool(
        default=False,
        help='use a \'zero copy\' method of sending data'
    )


@attr.adjust('binary_path', ssmdevices.lib.path('iperf.exe'))
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
        time: str='Undefined',
        number: str='Undefined',
        interval: str='Undefined',
        udp: str='bool',
        bit_rate: str='Undefined',
        buffer_size: str='Undefined',
        tcp_window_size: str='Undefined',
        nodelay: str='bool',
        mss: str='Undefined',
        bidirectional: str='bool',
        report_style: str='str'
    ):
        ...
    """Run an instance of iperf to profile data transfer speed. It can
    operate as a server (listener) or client (sender), operating either
    in the foreground or as a background thread.
    When running as an iperf client (server=False).
    """
    FLAGS = dict(_IPerfBase.FLAGS, bidirectional='-d', report_style='-y')
    DATAFRAME_COLUMNS = (
        'jitter_milliseconds',
        'datagrams_lost',
        'datagrams_sent',
        'datagrams_loss_percentage',
        'datagrams_out_of_order',
    )
    bidirectional: bool = attr.value.bool(
        default=False,
        key='-d',
        help='send and receive simultaneously'
    )
    report_style: str = attr.value.str(
        default='C',
        only=('C', None),
        allow_none=True,
        help='"C" for DataFrame table output, None for formatted text'
    )

    def profile(self, block=True):
        ret = super().profile(block)
        if block:
            return self._format_output(ret)
        else:
            return ret

    def read_stdout(self):
        """retreive text from standard output, and parse into a pandas DataFrame if self.report_style is None"""
        return self._format_output(super().read_stdout())

    def _format_output(self, stdout):
        """pack stdout into a pandas DataFrame if self.report_style == 'C'"""
        if self.report_style is None:
            return stdout.decode()
        columns = (
            'timestamp',
            'source_address',
            'source_port',
            'destination_address',
            'destination_port',
            'test_id',
            'interval',
            'transferred_bytes',
            'bits_per_second',
        )
        if self.udp:
            columns = columns + self.DATAFRAME_COLUMNS
        if isinstance(stdout, bytes):
            stdout = stdout.decode()
        data = pd.read_csv(StringIO(stdout), header=None, index_col=False, names=columns)
        if data.shape[1] > 0:
            data.drop(['interval', 'transferred_bytes', 'test_id'], inplace=True, axis=1)
        data['timestamp'] = pd.to_datetime(data['timestamp'], format='%Y%m%d%H%M%S')
        data['timestamp'] = data['timestamp'] + pd.TimedeltaIndex(
            data.index * self.interval % 1,
            's'
        )
        return data


@attr.adjust('binary_path', ssmdevices.lib.path('adb.exe'))
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
        time: str='Undefined',
        number: str='Undefined',
        interval: str='Undefined',
        udp: str='bool',
        bit_rate: str='Undefined',
        buffer_size: str='Undefined',
        tcp_window_size: str='Undefined',
        nodelay: str='bool',
        mss: str='Undefined',
        bidirectional: str='bool',
        report_style: str='str',
        remote_binary_path: str='str'
    ):
        ...
    remote_binary_path: str = attr.value.str(default='/data/local/tmp/iperf', cache=True)

    def profile(self, block=True):
        self._validate_flags()
        duration = 0 if self.time is None else self.time + 3
        timeout = max((self.timeout, duration))
        ret = self.run(
            'shell',
            self.remote_binary_path,
            self.FLAGS,
            background=not block,
            pipe=True,
            respawn=not block,
            check_stderr=True,
            timeout=timeout
        )
        if block:
            return self._format_output(ret)
        else:
            test = self.read_stdout(1)
            if 'network' in test:
                self._logger.warning('no network connectivity in UE')
            return ret

    def open(self):
        """Open an adb connection to the handset, copy the iperf binary onto the phone, and
        verify that iperf executes.
        """
        self._logger.debug('awaiting USB connection to handset')
        self.wait_for_device(30)
        lb.sleep(0.1)
        self._logger.debug('copying iperf onto phone')
        self.run('push', ssmdevices.lib.path('android', 'iperf'), self.remote_binary_path)
        self.wait_for_device(2)
        self.run('shell', 'chmod', '777', self.remote_binary_path, check=False)
        self.wait_for_device(2)
        stdout = self.run('shell', self.remote_binary_path, '--help', timeout=2, pipe=True)
        if stdout.startswith(b'/system/bin/sh'):
            raise OSError(f'adb shell iperf --help failed: {stdout}')
        self._logger.debug('phone is ready to execute iperf')

    def kill(self, wait_time=3):
        """Kill the local process and the iperf process on the UE."""
        super().kill()
        out = self.run('shell', 'ps')
        for line in out.splitlines():
            line = line.decode(errors='replace')
            if self.remote_binary_path in line.lower():
                pid = line.split()[1]
                stdout = self.pipe('shell', 'kill', '-9', pid)
                self._logger.debug(f'killing zombie iperf: {stdout}')
            lb.sleep(0.1)
            t0 = time.time()
            while time.time() - t0 < wait_time and wait_time != 0:
                out = self.pipe('shell', 'ps').lower()
                if b'iperf' not in out:
                    break
                lb.sleep(0.25)
            else:
                raise TimeoutError('timeout waiting for iperf process termination on UE')

    def read_stdout(self):
        """adb seems to forward stderr as stdout. Filter out some undesired
        resulting status messages.
        """
        txt = lb.ShellBackend.read_stdout(self)
        out = []
        for line in txt.splitlines():
            if b':' not in line:
                out.append(line)
            else:
                self._logger.warning('stdout: {}'.format(repr(line)))
        out = b'\n'.join(out)
        return self._format_output(out)

    def wait_for_cell_data(self, timeout=60):
        """Block until cellular data is available

        :param timeout: how long to wait for a connection before raising a Timeout error
        :return: None
        """
        self._logger.debug('waiting for cellular data connection')
        t0 = time.time()
        out = ''
        while time.time() - t0 < timeout or timeout is None:
            out = sp.run(
                [self.binary_path, 'shell', 'dumpsys', 'telephony.registry'],
                stdout=sp.PIPE,
                check=True,
                timeout=timeout
            ).stdout
            con = re.findall('mDataConnectionState=([\\-0-9]+)', out.decode(errors='replace'))
            if len(con) > 0:
                if con[0] == '2':
                    break
        else:
            raise TimeoutError('phone did not connect for cellular data before timeout')
        self._logger.debug('cellular data available after {} s'.format(time.time() - t0))

    def reboot(self, block=True):
        """Reboot the device.

        :param block: if truey, block until the device is ready to accept commands.
        """
        self._logger.info('rebooting')
        self.run('reboot')
        if block:
            self.wait_for_device()

    def wait_for_device(self, timeout=30):
        """Block until the device is ready to accept commands

        :return: None
        """
        self.run('wait-for-device')


class IPerf2BoundPair(IPerf2):

    def __init__(
        self,
        binary_path: str='NoneType',
        timeout: str='int',
        server: str='Undefined',
        port: str='int',
        bind: str='NoneType',
        format: str='NoneType',
        time: str='Undefined',
        number: str='Undefined',
        interval: str='Undefined',
        udp: str='bool',
        bit_rate: str='Undefined',
        buffer_size: str='Undefined',
        tcp_window_size: str='Undefined',
        nodelay: str='bool',
        mss: str='Undefined',
        bidirectional: str='bool',
        report_style: str='str',
        client: str='Undefined'
    ):
        ...
    """Configure and run an iperf client and a server pair on the host.

    Outputs from  to interfaces in order to ensure that data is routed between them, not through
    localhost or any other interface.
    """
    resource: str = attr.value.str(help='unused - use sender and receiver instead', sets=False)
    server: str = attr.value.NetworkAddress(
        accept_port=False,
        help='the ip address where the server listens'
    )
    client: str = attr.value.NetworkAddress(
        accept_port=False,
        help='the ip address from which the client sends data'
    )
    children = {}

    def open(self):
        self.children = dict()
        self.backend = None

    def close(self):
        try:
            self.kill()
        except TypeError as e:
            if 'NoneType' not in str(e):
                raise

    def kill(self):
        for name in ('client', 'server'):
            child = self.children.pop(name, None)
            if child is not None:
                child.kill()

    def running(self):
        for name in ('client', 'server'):
            child = self.children.get(name, None)
            if child is None:
                continue
            if child.running():
                return True
        return False

    def profile(self, block=True, **kws):
        if not block:
            kws['time'] = 0
            kws['number'] = -1
        self._setup_pair(**kws)
        self.children['server'].profile(block=False)
        ret = self.children['client'].profile(block=block)
        if block:
            ret = self.read_stdout(client_ret=ret)
            self.kill()
            return ret

    def read_stdout(self, client_ret=None):
        if client_ret is None:
            client = self.children['client'].read_stdout()
        else:
            client = client_ret
        server = self.children['server'].read_stdout()
        if isinstance(client, pd.DataFrame):
            return self._merge_dataframes(client, server)
        else:
            return dict(client=client, server=server)

    def _merge_dataframes(self, client, server):
        client.columns = [('client_' if n != 'timestamp' else '') + str(n) for n in client.columns]
        server.columns = [('server_' if n != 'timestamp' else '') + str(n) for n in server.columns]
        return client.merge(server, how='outer', on='timestamp')

    def _setup_pair(self, **kws):
        if self.running():
            raise BlockingIOError(f'{self} is already running')
        base_values = {
            k: getattr(self, k)
            for k in self.FLAGS.keys() if getattr(self, k) is not self._traits[k].default
        }
        base_values.update(kws)
        self.children['client'] = IPerf2(
            **dict(
                base_values,
                resource=self.client,
                bind=f'{self.client}:{find_free_port()}',
                server=False
            )
        )
        self.children['server'] = IPerf2(
            **dict(base_values, resource=None, bind=self.server, server=True, time=None, number=None)
        )
        self.children['client']._validate_flags()
        self.children['server']._validate_flags()
        self.backend = lb.sequentially(self.children['server'], self.children['client']).__enter__()
m1 = 6148914691236517205
m2 = 3689348814741910323
m4 = 1085102592571150095
m8 = 71777214294589695
m16 = 281470681808895
m32 = 4294967295
h01 = 72340172838076673

def bit_errors(x):
    """See: https://en.wikipedia.org/wiki/Hamming_weight"""
    import numpy as np
    if x is None:
        return None
    x = np.frombuffer(x[:len(x) // 8 * 8], dtype='uint64').copy()
    x -= x >> 1 & m1
    x = (x & m2) + (x >> 2 & m2)
    x = x + (x >> 4) & m4
    return (x * h01 >> 56).sum()


class TrafficProfiler_ClosedLoop(lb.Device):

    def __init__(
        self,
        resource: str='Undefined',
        server: str='Undefined',
        client: str='Undefined',
        receive_side: str='Undefined',
        port: str='int',
        timeout: str='int',
        tcp_nodelay: str='bool',
        sync_each: str='bool',
        delay: str='int'
    ):
        ...
    """Profile closed-loop traffic between two network interfaces
    on this computer. Takes advantage of the system clock as a common
    basis for traffic delay measurement, with uncertainty approximately
    equal to the system time resolution.
    """
    server: str = attr.value.str(help='the name of the network interface that will send data')
    client: str = attr.value.str(help='the name of the network interface that will receive data')
    receive_side: str = attr.value.str(
        help='which of the server or the client does the receiving',
        only=('server', 'client')
    )
    port: int = attr.value.int(
        default=0,
        min=0,
        help='TCP or UDP port for networking, or 0 to let the operating system choose'
    )
    resource: str = attr.value.str(help='skipd - use sender and receiver instead', cache=True)
    timeout: float = attr.value.float(
        default=2,
        min=0.001,
        help='timeout before aborting the test',
        cache=True
    )
    tcp_nodelay: bool = attr.value.bool(default=True, help='set True to disable Nagle\'s algorithm')
    sync_each: bool = attr.value.bool(
        default=False,
        help='synchronize the start times of the send and receive threads for each buffer at the cost of throughput'
    )
    delay: float = attr.value.float(default=0, min=0, help='wait time before profiling', cache=True)

    def __repr__(self):
        return '{name}(server=\'{server}\',client=\'{client}\')'.format(
            name=self.__class__.__name__,
            server=self.server,
            client=self.client
        )

    def close(self):
        if self.is_running():
            self.stop_traffic()

    def start(self, buffer_size, count=None, duration=None):
        """Start a background thread that runs a one-way traffic test.

        It will end when `count` buffers have been tested, `duration`
        time has elapsed, or `stop_traffic` is called. To retrieve the
        traffic data, call `stop_traffic`.
        """
        self._background_event = Event()
        self._background_queue = Queue()
        server_sock, client_sock, listener = self._open_sockets(buffer_size)
        try:
            self._run(
                client_sock=client_sock,
                server_sock=server_sock,
                buffer_size=buffer_size,
                end_event=self._background_event,
                count=count,
                duration=duration
            )
        except:
            self._close_sockets(client_sock, server_sock, listener)
            raise

    def is_running(self):
        return hasattr(self, '_background_event') and not self._background_event.is_set()

    def get(self):
        if not hasattr(self, '_background_queue'):
            raise ChildProcessError('no traffic history, start a run first')
        try:
            ret = self._background_queue.get(timeout=self.timeout)
        except Empty:
            ret = {}
        if isinstance(ret, BaseException):
            raise ret
        else:
            return self._make_dataframe(ret)

    def stop(self):
        if not hasattr(self, '_background_queue'):
            raise ChildProcessError('no traffic running, start a run first')
        self._background_event.set()
        return self.get()

    def _make_dataframe(self, data):
        raise NotImplementedError


class suppress_matching_arg0(AbstractContextManager):
    """Context manager to suppress specified exceptions that must also match
        a specified first argument.

    After the exception is suppressed, execution proceeds with the next
    statement following the with statement.

         with suppress(FileNotFoundError):
             os.remove(somefile)
         # Execution still resumes here if the file was already removed
    """

    def __init__(self, *exceptions, arg0=None):
        self._exceptions = exceptions
        self._arg0 = arg0

    def __enter__(self):
        pass

    def __exit__(self, exctype, excinst, exctb):
        if exctype is None:
            return False
        if not issubclass(exctype, self._exceptions):
            return True
        if self._arg0 is None or self._arg0 == excinst.args[0]:
            return False
        else:
            return True


class ServerConnectionError(ConnectionError):
    pass


class ClientConnectionError(ConnectionError):
    pass


class PortBusyError(ConnectionError):
    pass


class TrafficProfiler_ClosedLoopTCP(TrafficProfiler_ClosedLoop):

    def __init__(
        self,
        resource: str='Undefined',
        server: str='Undefined',
        client: str='Undefined',
        receive_side: str='Undefined',
        port: str='int',
        timeout: str='int',
        tcp_nodelay: str='bool',
        sync_each: str='bool',
        delay: str='int'
    ):
        ...
    _server = None
    PORT_WINERRS = 10013, 10048
    CONN_WINERRS = 10051,

    def _close_sockets(self, *sockets, bytes_=0):
        for sock in sockets:
            try:
                sock.settimeout(0.1)
            except OSError:
                continue
            with suppress_matching_arg0(OSError, arg0=10057):
                sock.send(b'')
            with suppress(OSError):
                t0 = perf_counter()
                while perf_counter() - t0 < 1:
                    try:
                        buf = sock.recv(bytes_)
                    except socket.timeout:
                        break
                    if len(buf) == 0:
                        break
                else:
                    self._logger.warning('failed to flush socket before closing')
            with suppress_matching_arg0(OSError, arg0=10057), suppress_matching_arg0(
                OSError,
                arg0='timed out'
            ):
                sock.shutdown(socket.SHUT_RDWR)
            with suppress_matching_arg0(OSError, arg0=10057):
                sock.close()

    @property
    def _receive_interface(self):
        if self.receive_side == 'server':
            return self.server
        else:
            return self.client

    def _open_sockets(self, buffer_size):
        """Connect the supplied client socket to the server."""
        global _tcp_port_offset
        server_ip = get_ipv4_address(self.server)
        client_ip = get_ipv4_address(self.client)
        listen_sock = None
        timeout = self.timeout
        bytes_ = buffer_size
        tcp_nodelay = self.tcp_nodelay
        client_done = Event()
        server_done = Event()

        def listener(port):
            """Run a listener at the socket"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, bytes_)
                self._logger.info(f'created server socket with recv buffer size {bytes_}')
                bufsize = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                if bufsize < bytes_:
                    msg = f'recv buffer size is {bufsize}, but need at least {self.bytes}'
                    raise OSError(msg)
                self._logger.info(f'binding listener to {server_ip}:{port}')
                sock.bind((server_ip, port))
                sock.listen(5)
            except OSError as e:
                if hasattr(e, 'winerror') and e.winerror in self.PORT_WINERRS:
                    raise PortBusyError()
                else:
                    raise
            return sock

        def client(listen_sock):
            port = listen_sock.getsockname()[1]
            sock = None
            self._logger.warning('client start')
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, tcp_nodelay)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, bytes_)
                bytes_actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                if bytes_actual != bytes_:
                    msg = f'client buffer size is {bytes_actual}, but requested {self.bytes}'
                    raise OSError(msg)
                try:
                    sock.bind((client_ip, 0))
                except OSError as e:
                    ex = e
                else:
                    ex = None
                if ex is not None:
                    raise ConnectionRefusedError(*ex.args)
                sock.connect((server_ip, port))
            except socket.timeout:
                if sock is not None:
                    self._close_sockets(sock, bytes_=bytes_)
                msg = f'client socket timed out in attempt to connect to the server at {server_ip}:{port}'
                ex = ConnectionRefusedError(msg)
            except OSError as e:
                msg = f'connection failed between server {server_ip} and client {client_ip}'
                if hasattr(e, 'winerror') and e.winerror in self.PORT_WINERRS:
                    self._logger.debug(msg)
                    ex = PortBusyError(msg)
                elif hasattr(e, 'winerror') and e.winerror in self.CONN_WINERRS:
                    self._logger.debug(msg)
                    ex = ConnectionError(msg)
                else:
                    raise
            except BaseException:
                if sock is not None:
                    self._close_sockets(sock, bytes_=bytes_)
                raise
            else:
                ex = None
            if ex is not None:
                raise ex
            client_done.set()
            if not server_done.wait(timeout):
                self._close_sockets(sock, bytes_=bytes_)
            return sock

        def server(listen_sock):
            self._logger.warning('server start')
            conn = None
            ex = None
            t0 = perf_counter()
            try:
                while perf_counter() - t0 < timeout:
                    try:
                        listen_sock.settimeout(0.051 + timeout - (perf_counter() - t0))
                        self._sock = listen_sock
                        conn, (other_ip, _) = listen_sock.accept()
                    except socket.timeout:
                        continue
                    if other_ip == client_ip:
                        break
                    else:
                        port = listen_sock.getsockname()[1]
                        self._logger.warning(
                            f'connection attempt from unexpected ip {other_ip} instead of {client_ip}:{port}'
                        )
                        if conn is not None:
                            self._close_sockets(conn, bytes_=bytes_)
                            conn = None
                else:
                    port = listen_sock.getsockname()[1]
                    raise TimeoutError(
                        f'socket server received no connection attempt on {server_ip}:{port}'
                    )
            except BaseException as e:
                listen_sock.settimeout(timeout)
                ex = e
            else:
                listen_sock.settimeout(timeout)
                conn.settimeout(timeout)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, tcp_nodelay)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, bytes_)
                bytes_actual = conn.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                if bytes_actual != bytes_:
                    msg = f'server buffer size is {bytes_actual}, but requested {self.bytes}'
                    raise OSError(msg)
            if not client_done.wait(timeout):
                if ex is not None:
                    self._logger.debug(
                        f'server connection exception: {repr(ex)} (superceded by client exception)'
                    )
                    ex = None
                if conn is not None:
                    self._close_sockets(conn, bytes_=bytes_)
            server_done.set()
            if ex is not None:
                raise ex
            return conn

        def open_():
            global _tcp_port_offset, listen_sock
            if self.port != 0:
                port = self.port + _tcp_port_offset
            else:
                port = 0
            listen_sock = listener(port)
            try:
                ret = lb.concurrently(
                    lb.Call(server, listen_sock=listen_sock),
                    lb.Call(client, listen_sock=listen_sock)
                )
            except:
                self._close_sockets(listen_sock, bytes_=0)
                raise
            finally:
                if self.port != 0:
                    _tcp_port_offset = (_tcp_port_offset + 1) % 5000
            ret['listener'] = listen_sock
            return ret
        try:
            t0 = perf_counter()
            if self.port == 0:
                ret = open_()
            else:
                ret = lb.retry(PortBusyError, 100)(open_)()
            p = ret['client'].getsockname()[1]
            self._logger.debug(
                f'server {server_ip}:{p} accepted connection from client {client_ip}:{p} in {perf_counter() - t0:0.3f}s'
            )
        except PortBusyError:
            raise ConnectionError('failed to connect on {retries} ports')
        return ret['server'], ret['client'], ret['listener']

    def _run(self, client_sock, server_sock, buffer_size, duration=None, count=None, end_event=None):
        if duration is count is end_event is None:
            raise ValueError(
                'must pass at least one of duration, count, and end_event to specify end condition'
            )
        if self.tcp_nodelay and buffer_size < self.mss():
            raise ValueError(
                f'with tcp_nodelay enabled, set buffer_size at least as large as the MSS ({self.mss()})'
            )
        if self.server == self._receive_interface:
            send_sock, recv_sock = client_sock, server_sock
        else:
            send_sock, recv_sock = server_sock, client_sock
        t_start = perf_counter()
        background = end_event is not None
        if background:
            count = 1
        timeout = self.timeout
        bytes_ = buffer_size
        sync = self.sync_each
        delay = self.delay
        rx_ready = Event()
        tx_ready = Event()
        if end_event is None:
            end_event = Event()
        except_event = Event()

        def check_status():
            lb.sleep(0)
            if except_event.is_set():
                raise lb.util.ThreadEndedByMaster()

        def traffic_done(i):
            if background and end_event.is_set():
                return True
            elif count is not None and i >= count:
                return True
            elif duration is not None and perf_counter() - t_start >= duration:
                return True
            else:
                return False

        def receiver():
            buf = bytearray(bytes_)
            starts = []
            finishes = []
            rx_buffer0_finishes = []
            rx_buffer_sizes = []
            rx_buffers = []

            def do_sync():
                check_status()
                if sync:
                    t_sync = perf_counter()
                    rx_ready.set()
                    while not tx_ready.is_set():
                        if perf_counter() - t_sync > timeout:
                            except_event.set()
                            raise TimeoutError('timeout waiting for sender sync')
                    tx_ready.clear()

            def single():
                """Receive a single buffer of data"""
                bytes_left = int(bytes_)
                do_sync()
                t0 = t1 = t2 = perf_counter()
                i = 0
                while bytes_left > 0:
                    if t2 - t0 > timeout:
                        msg = f'timeout while waiting to receive {bytes_left} of {bytes_} bytes'
                        raise TimeoutError(msg)
                    try:
                        bytes_left -= recv_sock.recv_into(buf[-bytes_left:], bytes_left)
                        if i == 0:
                            rx_buffer0_size = int(bytes_) - bytes_left
                            t1 = t2 = perf_counter()
                        else:
                            t2 = perf_counter()
                        i += 1
                    except socket.timeout as e:
                        raise TimeoutError(' '.join(e.args))
                return t0, t1, t2, rx_buffer0_size, i
            try:
                do_sync()
                single()
                rx_ready.set()
                i = 0
                while not traffic_done(i):
                    t0, t1, t2, rx_buffer0_size, rx_buffer_count = single()
                    starts.append(t0)
                    rx_buffer0_finishes.append(t1)
                    finishes.append(t2)
                    rx_buffer_sizes.append(rx_buffer0_size)
                    rx_buffers.append(rx_buffer_count)
                    i += 1
            except lb.util.ThreadEndedByMaster:
                self._logger.debug(f'{self.__class__.__name__}() ended by master thread')
                except_event.set()
            except BaseException:
                if not (end_event is not None and end_event.is_set()):
                    except_event.set()
                    raise
            return {
                't_rx_start': starts,
                't_rx_end_buffer0': rx_buffer0_finishes,
                't_rx_end': finishes,
                'rx_buffer0_size': rx_buffer_sizes,
                'rx_buffer_count': rx_buffers,
            }

        def sender():
            """This runs in the receive thread, with the socket connected."""
            start_timestamps = []
            finish_timestamps = []
            start = None

            def do_sync():
                check_status()
                if sync:
                    t_sync = perf_counter()
                    while not rx_ready.is_set():
                        if perf_counter() - t_sync > timeout:
                            except_event.set()
                            raise TimeoutError('timeout waiting for receive sync')
                    rx_ready.clear()
                    tx_ready.set()

            def single():
                import numpy as np
                data = np.random.bytes(bytes_)
                do_sync()
                t0 = t1 = perf_counter()
                try:
                    send_sock.sendall(data)
                    t1 = perf_counter()
                    if delay > 0:
                        time.sleep(delay)
                except socket.timeout:
                    ex = IOError('timed out attempting to send data')
                else:
                    ex = None
                return t0, t1, ex
            try:
                do_sync()
                single()
                tx_ready.set()
                i = 0
                while not traffic_done(i):
                    if i == 0:
                        start = datetime.datetime.now()
                    t0, t1, ex = single()
                    if ex is not None:
                        raise ex
                    start_timestamps.append(t0)
                    finish_timestamps.append(t1)
                    i += 1
            except lb.util.ThreadEndedByMaster:
                self._logger.debug(f'{self.__class__.__name__}() ended by master thread')
                except_event.set()
            except BaseException as e:
                if not (end_event is not None and end_event.is_set()):
                    self._logger.debug(f'suppressed exception in sender: {e}')
                    except_event.set()
            return {
                'start': start,
                'bytes': bytes_,
                't_tx_start': start_timestamps,
                't_tx_end': finish_timestamps,
            }

        def background_thread():
            try:
                ret = None
                i = 0
                while not end_event.is_set():
                    ret = lb.concurrently(sender, receiver, traceback_delay=True)
                    self._background_queue.put(ret)
                    i += 1
                self._logger.debug(f'finished traffic test of {i} buffers of {bytes_} bytes')
            except BaseException as e:
                if not self._background_event.is_set():
                    self._logger.warning(
                        f'background thread exception - traceback: {traceback.format_exc()}'
                    )
                    self._background_queue.put(e)
                self._close_sockets(send_sock, recv_sock, listen_sock, bytes_=buffer_size)
            finally:
                self._logger.debug('background thread finished')
        if background:
            thread = Thread(target=background_thread)
            thread.start()
            tx_ready.wait_for_device(timeout=self.timeout)
            rx_ready.wait_for_device(timeout=self.timeout)
            self._logger.debug(f'first buffer sent after {perf_counter() - t_start:0.3f}s')
        else:
            ret = lb.concurrently(sender, receiver, traceback_delay=True)
            i = len(ret['t_tx_start'])
            self._logger.debug(f'finished traffic test of {i} buffers of {bytes_} bytes')
            return ret

    def profile_count(self, buffer_size: int, count: int):
        """sends `count` buffers of size `buffer_size` bytes
        and returns profiling information"

        Arguments:

            buffer_size (int): number of bytes to send in each buffer

            count (int): the number of buffers to send

        :returns: a DataFrame indexed on PC time containing columns 'bits_per_second', 'duration', 'delay', 'queuing_duration'
        """
        server_sock, client_sock, listener = self._open_sockets(buffer_size)
        try:
            ret = self._run(
                client_sock=client_sock,
                server_sock=server_sock,
                count=count,
                buffer_size=buffer_size
            )
        finally:
            self._close_sockets(client_sock, server_sock, listener)
        return self._make_dataframe(ret)

    def profile_duration(self, buffer_size: int, duration: float):
        """sends buffers of size `buffer_size` bytes until
        `duration` seconds have elapsed, and returns profiling information"

        Arguments:

            buffer_size (int): number of bytes to send in each buffer

            duration (float): the minimum number of seconds to spend profiling

        :returns: a DataFrame indexed on PC time containing columns 'bits_per_second', 'duration', 'delay', 'queuing_duration'
        """
        server_sock, client_sock, listener = self._open_sockets(buffer_size)
        try:
            ret = self._run(
                client_sock=client_sock,
                server_sock=server_sock,
                buffer_size=buffer_size,
                duration=duration
            )
        finally:
            self._close_sockets(client_sock, server_sock, listener)
        return self._make_dataframe(ret)

    def _make_dataframe(self, worker_data):
        self._logger.debug('making dataframe')
        start = worker_data.pop('start', None)
        if start is None:
            raise IOError('the run did not return data')
        buffer_size = worker_data.pop('bytes')
        count = min(len(worker_data['t_tx_start']), len(worker_data['t_rx_start']))
        for k in worker_data.keys():
            worker_data[k] = worker_data[k][:count]
        ret = pd.DataFrame(worker_data)
        timestamp = pd.TimedeltaIndex(ret.t_tx_start, unit='s') + start
        duration = ret.t_rx_end - ret.t_rx_start
        late_rate = (buffer_size - ret.rx_buffer0_size) / (ret.t_rx_end - ret.t_rx_end_buffer0)
        est_rx_buffer0_start = ret.t_rx_end_buffer0 - ret.rx_buffer0_size / late_rate
        ret = pd.DataFrame(
            {
                'bits_per_second': 8 * buffer_size / duration,
                'duration': duration,
                'delay': est_rx_buffer0_start - ret.t_tx_start,
                'queuing_duration': ret.t_tx_end - ret.t_tx_start,
                'rx_buffer_count': ret.rx_buffer_count,
                't_rx_end_buffer0': ret.t_rx_end_buffer0,
                'timestamp': timestamp,
            }
        )
        return ret.set_index('timestamp')

    def mss(self):
        return self.mtu() - 40

    def mtu(self):
        iface = list_network_interfaces('interface')[self._receive_interface]['interface']
        return psutil.net_if_stats()[iface].mtu

    def wait_for_interfaces(self, timeout):
        errors = TimeoutError, ConnectionRefusedError
        t0 = time.perf_counter()
        socks = lb.until_timeout(errors, timeout)(self._open_sockets)()
        self._close_sockets(*socks)
        elapsed = perf_counter() - t0
        self._logger.debug(f'interfaces ready after {elapsed:0.2f}s')
        return elapsed
if __name__ == '__main__':
    lb.show_messages('debug')
    net = TrafficProfiler_ClosedLoopTCP(
        server='Ethernet',
        client='Ethernet',
        receive_side='server',
        port=0,
        tcp_nodelay=True,
        timeout=2
    )
    with net:
        print(net.acquire(10 * net.mtu(), count=10))
