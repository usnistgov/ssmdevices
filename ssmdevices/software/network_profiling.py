# -*- coding: utf-8 -*-
"""
@author: Dan Kuester <daniel.kuester@nist.gov>,
         Michael Voecks <michael.voecks@nist.gov>
"""
__all__ = ['IPerf', 'IPerfOnAndroid', 'IPerfBoundPair',
           'ClosedLoopTCPBenchmark']

import datetime
import labbench as lb
import numpy as np
import psutil
import socket
import ssmdevices.lib
import subprocess as sp
import sys
import time
import traceback

from time import perf_counter
from queue import Queue, Empty
from threading import Event, Thread
from io import StringIO

if __name__ == '__main__':
    from _networking import get_ipv4_address, list_network_interfaces, get_ipv4_occupied_ports
else:
    from ._networking import get_ipv4_address, list_network_interfaces, get_ipv4_occupied_ports

if '_tcp_port_offset' not in dir():
    _tcp_port_offset = 0

# Make sure the performance counter is initialized
perf_counter()


class IPerf(lb.ShellBackend):
    ''' Run an instance of iperf, collecting output data in a background thread.
        When running as an iperf client (server=False), 
        The default value is the path that installs with 64-bit cygwin.
    '''

    binary_path: ssmdevices.lib.path('iperf.exe')
    timeout: 5 # seconds

    resource: lb.Unicode(
        default=None,
        key='-c',
        allow_none=True,
        help='client host address (leave None, with server=True, to run as a server)'
    )

    server: lb.Bool(
        default=False,
        key='-s',
        help='True to run as a server'
    )

    port: lb.Int(
        default=5001,
        key='-p',
        min=0,
        help='network port'
    )

    bind: lb.Unicode(
        default=None,
        key='-B',
        allow_none=True,
        help='bind connection to specified IP'
    )

    tcp_window_size: lb.Int(
        default=None,
        key='-w',
        min=1,
        help='(bytes)',
        allow_none=True
    )

    buffer_size: lb.Int(
        default=None,
        key='-l',
        min=1, allow_none=True,
        help='Size of data buffer that generates traffic (bytes)'
    )

    interval: lb.Float(
        default=0.25,
        key='-i',
        min=0.01,
        help='Interval between throughput reports (s)'
    )

    bidirectional: lb.Bool(
        default=False,
        key='-d',
        help='send and receive simultaneously'
    )

    udp: lb.Bool(
        default=False,
        key='-u',
        help='set True to use UDP instead of TCP'
    )

    bit_rate: lb.Unicode(
        default=None,
        key='-b',
        allow_none=True,
        help='maximum bit rate (append unit for unit suffix, e.g. 10K)'
    )

    time: lb.Int(
        default=None,
        key='-t',
        min=0,
        max=16535,
        allow_none=True,
        help='time in seconds to transmit before quitting (instead of `number`) (default 10s)'
    )

    report_style: lb.Unicode(
        default='C',
        key='-y',
        only=('C', None),
        allow_none=True,
        help='"C" to work with CSV outputs (and fetch pandas DataFrame tables), '\
             'or None to return and fetch formatted text output'
    )

    number: lb.Int(
        default=None,
        key='-n',
        min=-1,
        allow_none=True,
        help='the number of bytes to transmit (instead of time)'
    )
    
    nodelay: lb.Bool(
        default=False,
        key='-N',
        help='set True to use nodelay (TCP traffic only)'
    )

    mss: lb.Int(
        default=None,
        key='-M',
        min=10,
        allow_none=True,
        help='minimum segment size, in bytes (= MTU - 40 bytes, TCP traffic only)'
    )
    
    def fetch(self):
        ''' retreive text from standard output, and parse into a pandas DataFrame.
        '''
        stdout = self.read_stdout()

        if self.settings.report_style is None:
            # human readable table output
            return stdout
        else:
            # csv output
            return self._make_dataframe(stdout)

    def background(self, **flags):
        # respawn background calls
        with self.respawn:
            super().background(**flags)

    def foreground(self, **flags):
        stdout = super().foreground(**flags).decode()

        if self.settings.report_style is None:
            # human readable table output
            return stdout
        else:
            # csv output
            return self._make_dataframe(stdout)

    def _commandline(self, **flags):
        self._update_settings(flags)

        # super()._commandline updates self.settings from flags -
        # now it is time to check for conflicts between parameters
        if self.settings.resource is not None and self.settings.server:
            raise ValueError('must set exactly one of (a) client operation by setting resource="(hostname here)", '
                             'or (b) server operation by setting server=True')
        if self.settings.udp:
            if self.settings.mss is not None:
                raise ValueError('the TCP MSS setting is incompatible with UDP')
            if self.settings.nodelay:
                raise ValueError('the TCP nodelay setting is incompatible with UDP')
            if self.settings.buffer_size is not None:
                self._console.warning('iperf may work improperly when setting udp=True with buffer_size')

        if not self.settings.udp and self.settings.bit_rate is not None:
            raise ValueError('iperf does not support setting bit_rate in TCP')

        if self.settings.server:
            if self.settings.time is not None:
                raise ValueError('iperf server does not support the `time` argument')
            if self.settings.number is not None:
                raise ValueError('iperf server does not support the `number` argument')

        return super()._commandline()
        
    def _make_dataframe(self, stdout):
        columns = 'timestamp', 'source_address', \
                  'source_port', 'destination_address', 'destination_port', \
                  'test_id', 'interval', 'transferred_bytes', 'bits_per_second'

        if self.settings.udp:
            columns = columns + ('jitter_milliseconds',
                                 'datagrams_lost',
                                 'datagrams_sent',
                                 'datagrams_loss_percentage',
                                 'datagrams_out_of_order')
        #
        # columns = ['iperf_' + c for c in columns]

        data = pd.read_csv(StringIO(stdout), header=None, index_col=False,
                           names=columns)

        # throw out the last row (potantially a summary of the previous rows)
        if len(data) == 0:
            data = data.append([None])
        data.drop(['interval', 'transferred_bytes', 'test_id'], inplace=True, axis=1)
        data['timestamp'] = pd.to_datetime(data['timestamp'], format='%Y%m%d%H%M%S')
        data['timestamp'] = data['timestamp'] + \
                                  pd.TimedeltaIndex((data.index * self.settings.interval) % 1, 's')

        return data

    @classmethod
    def __imports__(cls):
        global pd
        import pandas as pd


class IPerfOnAndroid(IPerf):
    remote_binary_path = '/data/local/tmp/iperf'

    binary_path: lb.Unicode(ssmdevices.lib.path('adb.exe'))
    remote_binary_path: lb.Unicode(remote_binary_path)
    arguments: lb.List(['shell', remote_binary_path,
                        # '-y', 'C'
                        ])

    def open(self):
        with self.no_state_arguments:
            #            self._console.warning('TODO: need to fix setup for android iperf, but ok for now')
            #            devices = self.foreground('devices').strip().rstrip().splitlines()[1:]
            #            if len(devices) == 0:
            #                raise Exception('adb lists no devices. is the UE connected?')
            self._console.debug('waiting for USB connection to phone')
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True,
                   timeout=30)

            lb.sleep(.1)
            self._console.debug('copying iperf onto phone')
            sp.run([self.settings.binary_path, "push", ssmdevices.lib.path('android', 'iperf'),
                    self.settings.remote_binary_path], check=True, timeout=2)
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=2)
            sp.run([self.settings.binary_path, "shell", 'chmod', '777',
                    self.settings.remote_binary_path], timeout=2)
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=2)

            #            # Check that it's executable
            self._console.debug('verifying iperf execution on phone')
            cp = sp.run([self.settings.binary_path, 'shell',
                         self.settings.remote_binary_path, '--help'],
                        timeout=2, stdout=sp.PIPE)
            if cp.stdout.startswith(b'/system/bin/sh'):
                raise Exception('could not execute!!! ', cp.stdout)
            self._console.debug('phone is ready to execute iperf')

    def start(self):
        super(IPerfOnAndroid, self).start()
        test = self.read_stdout(1)
        if 'network' in test:
            self._console.warning('no network connectivity in UE')

    def kill(self, wait_time=3):
        ''' Kill the local process and the iperf process on the UE.
        '''

        # Kill the local adb process as normal
        super(IPerfOnAndroid, self).kill()

        # Now's where the fun really starts
        with self.no_state_arguments:
            # Find and kill processes on the UE
            out = self.foreground('shell', 'ps')
            for line in out.splitlines():
                line = line.decode(errors='replace')
                if self.settings.remote_binary_path in line.lower():
                    pid = line.split()[1]
                    self._console.debug('killing zombie iperf. stdout: {}' \
                                      .format(self.foreground('shell', 'kill', '-9', pid)))
            lb.sleep(.1)
            # Wait for any iperf zombie processes to die
            t0 = time.time()
            while time.time() - t0 < wait_time and wait_time != 0:
                out = self.foreground('shell', 'ps').lower()
                if b'iperf' not in out:
                    break
                lb.sleep(.25)
            else:
                raise TimeoutError('timeout waiting for iperf process termination on UE')

    def read_stdout(self, n=0):
        ''' adb seems to forward stderr as stdout. Filter out some undesired
            resulting status messages.
        '''
        txt = super(IPerfOnAndroid, self).read_stdout(n)
        out = []
        for l in txt.splitlines():
            if ':' not in l:
                out.append(l)
            else:
                self._console.warning('stdout: {}'.format(repr(l)))
        return '\n'.join(out)

    def fetch(self):
        return self.read_stdout()

    def wait_for_cell_data(self, timeout=60):
        ''' Block until cellular data is available

        :param timeout: how long to wait for a connection before raising a Timeout error
        :return: None
        '''
        import subprocess as sp
        import re

        self._console.debug('waiting for cellular data connection')
        t0 = time.time()
        out = ''
        while time.time() - t0 < timeout or timeout is None:
            out = sp.run([self.settings.binary_path, 'shell', 'dumpsys', 'telephony.registry'],
                         stdout=sp.PIPE, check=True, timeout=timeout).stdout

            con = re.findall('mDataConnectionState=([\-0-9]+)',
                             out.decode(errors='replace'))

            if len(con) > 0:
                if con[0] == '2':
                    break
        else:
            raise TimeoutError('phone did not connect for cellular data before timeout')
        self._console.debug('cellular data available after {} s'.format(time.time() - t0))

    def reboot(self, block=True):
        ''' Reboot the device.

        :param block: if this evaluates to True, block until the device is ready to accept commands
        :return:
        '''
        self._console.info('rebooting')
        sp.run([self.settings.binary_path, 'reboot'], check=True, timeout=2)
        self.wait()

    def wait(self, timeout=30):
        ''' Block until the device is ready to accept commands

        :return: None
        '''
        sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=timeout)
        self._console.debug('device is ready')


class IPerfBoundPair(lb.Device):
    ''' Run an iperf client and a server on the host computer at the same time. They are
        bound to interfaces in order to ensure that data is routed between them, not through
        localhost or any other interface.
    '''

    # take the settings from IPerf, which we will pass through to each IPerf instance
    __annotations__ = {
        k: t.copy()
        for k, t in IPerf.settings.__traits__.items()
        if k != 'bind'
    }

    # add other settings
    resource: lb.Unicode(help='unused - use sender and receiver instead', settable=False)

    server: lb.Unicode(
        help='the ip address where the server listens (must match a network interface on the host)'
    )

    client: lb.Unicode(
        help='the ip address from which the client sends data (must match a network interface on the host)'
    )

    port: lb.Int(
        default=5010,
        key='-p',
        min=5010,
        max=32000,
        help='highest port number to use when cycling through ports'
    )

    children = {}

    def close(self):
        try:
            self.kill()
        except TypeError as e:
            if 'NoneType' not in str(e):
                raise

    def kill(self):
        if 'server' in self.children:
            self.children['server'].kill()
        if 'client' in self.children:
            self.children['client'].kill()

    def running(self):
        if set(self.children.keys()) != {'client', 'server'}:
            return False
        return self.children['client'].running() or self.children['server'].running()

    def background(self, **flags):
        self._setup_pair(flags)

        self.children['server'].background()
        self.children['client'].background()

    def fetch(self):
        client=self.children['client'].fetch()
        server=self.children['server'].fetch()

        if isinstance(client, pd.DataFrame):
            return self._merge_dataframes(client, server)
        else:
            return dict(client=client, server=server)

    def foreground(self, **flags):
        ''' Acquire iperf output for the specified duration and return.
            Raises a lb.DeviceConnectionLost if iperf stops before the
            duration has finished.
        '''
        self._setup_pair(flags)

        self.children['server'].background()
        client=self.children['client'].foreground()
        server=self.children['server'].fetch()
        self.kill()

        if isinstance(client, pd.DataFrame):
            return self._merge_dataframes(client, server)
        else:
            return dict(client=client, server=server)
        
    def _merge_dataframes(self, client, server):
        client.columns = [('client_' if n != 'timestamp' else '')+str(n)
                          for n in client.columns]
        server.columns = [('server_' if n != 'timestamp' else '')+str(n)
                          for n in server.columns]
        return client.merge(server, how='outer', on='timestamp')

    def _setup_pair(self, flags):
        if self.running():
            # clear any buffered outputs
            raise Exception("can't start run while a background process is running")

        flags = dict(flags) # make sure we don't do in-place edits on the caller's variable
        
        busy_ports = get_ipv4_occupied_ports(self.settings.server)
        while self.settings.port in busy_ports:
            # find an open server port
            if self.settings.port >= self.settings['port'].max:
                self.settings.port = self.settings['port'].min
            else:
                self.settings.port = self.settings.port + 1
        flags['port'] = self.settings.port

        settings = {k: getattr(self.settings, k)
                    for k, v in self.settings.__traits__.items()
                    if v.key is not lb.Undefined and k not in ('resource', 'bind')}

        self.children['client'] = IPerf(
            resource=self.settings.server,
            bind=self.settings.client,
            **settings
        )
        self.children['client']._update_settings(flags)

        # clear server-incompatible flags
        settings.pop('time', None)
        settings.pop('number', None)
        self.children['server'] = IPerf(
            bind=self.settings.server,
            server=True,
            **settings
        )
        flags = dict(flags)
        flags.pop('time', None)
        flags.pop('number', None)
        self.children['server']._update_settings(flags)

        # cycle the port for the next call, because windows takes a couple of
        # minutes to release bound ports after use

m1 = 0x5555555555555555
m2 = 0x3333333333333333
m4 = 0x0f0f0f0f0f0f0f0f
m8 = 0x00ff00ff00ff00ff
m16 = 0x0000ffff0000ffff
m32 = 0x00000000ffffffff
h01 = 0x0101010101010101


def bit_errors(x):
    ''' See: https://en.wikipedia.org/wiki/Hamming_weight
    '''
    if x is None:
        return None
    #    a1 = np.frombuffer(buf1,dtype='uint64')
    x = np.frombuffer(x[:(len(x) // 8) * 8], dtype='uint64').copy()
    x -= (x >> 1) & m1;
    x = (x & m2) + ((x >> 2) & m2);
    x = (x + (x >> 4)) & m4;
    return ((x * h01) >> 56).sum()


from contextlib import suppress, AbstractContextManager


class ClosedLoopBenchmark(lb.Device):
    ''' Profile closed-loop traffic between two network interfaces
        on this computer. Takes advantage of the system clock as a common
        basis for traffic delay measurement, with uncertainty approximately
        equal to the system time resolution.
    '''

    server: lb.Unicode(help='the name of the network interface that will send data')
    client: lb.Unicode(help='the name of the network interface that will receive data')
    receiver: lb.Unicode(help='the name of the network interface that will send data')
    port: lb.Int(0,
                 min=0,
                 help='TCP or UDP port for networking, or 0 to let the operating system choose')
    resource: lb.Unicode(help='skipd - use sender and receiver instead')
    timeout: lb.Float(2,
                      min=1e-3,
                      help='timeout before aborting the test')
    tcp_nodelay: lb.Bool(True,
                         help='set True to disable Nagle\'s algorithm')
    sync_each: lb.Bool(False,
                       help='synchronize the start times of the send and receive threads for each buffer at the cost of throughput')

    delay: lb.Float(0, min=0, help='wait time between sending buffers')

    def __repr__(self):
        return "{name}(server='{server}',client='{client}')" \
            .format(name=self.__class__.__name__,
                    server=self.settings.server,
                    client=self.settings.client)

    @classmethod
    def __imports__(cls):
        global pd
        import pandas as pd

    def close(self):
        if self.is_running():
            self.stop_traffic()

    def start(self, buffer_size, count=None, duration=None):
        ''' Start a background thread that runs a one-way traffic test.
        
            It will end when `count` buffers have been tested, `duration`
            time has elapsed, or `stop_traffic` is called. To retrieve the
            traffic data, call `stop_traffic`.
        '''
        self._background_event = Event()
        self._background_queue = Queue()

        server_sock, client_sock, listener = self._open_sockets(buffer_size)

        try:
            self._run(client_sock=client_sock,
                      server_sock=server_sock,
                      buffer_size=buffer_size,
                      end_event=self._background_event,
                      count=count,
                      duration=duration)
        except:
            self._close_sockets(client_sock, server_sock, listener)
            raise

    def is_running(self):
        return hasattr(self, '_background_event') \
               and not self._background_event.is_set()

    def get(self):
        if not hasattr(self, '_background_queue'):
            raise ChildProcessError('no traffic history, start a run first')

        try:
            ret = self._background_queue.get(timeout=self.settings.timeout)
        except Empty:
            ret = {}

        if isinstance(ret, BaseException):
            raise ret
        else:
            return self._make_dataframe(ret, )

    def stop(self):
        if not hasattr(self, '_background_queue'):
            raise ChildProcessError('no traffic running, start a run first')

        self._background_event.set()
        return self.get()

    def _make_dataframe(self, data):
        raise NotImplementedError


class suppress_matching_arg0(AbstractContextManager):
    """ Context manager to suppress specified exceptions that must also match
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


class ClosedLoopTCPBenchmark(ClosedLoopBenchmark):
    _server = None
    port_winerrs = (10013, 10048)
    conn_winerrs = (10051,)

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
                    self._console.warning('failed to flush socket before closing')

            with suppress_matching_arg0(OSError, arg0=10057), \
                 suppress_matching_arg0(OSError, arg0='timed out'):
                sock.shutdown(socket.SHUT_RDWR)

            with suppress_matching_arg0(OSError, arg0=10057):
                sock.close()

    def _open_sockets(self, buffer_size):
        ''' Connect the supplied client socket to the server.
        '''
        if self.settings.receiver not in (self.settings.server, self.settings.client):
            raise ValueError(f'the receiver setting must match the client or server interface name')

        global _tcp_port_offset

        server_ip = get_ipv4_address(self.settings.server)
        client_ip = get_ipv4_address(self.settings.client)
        listen_sock = None

        timeout = self.settings.timeout
        bytes_ = buffer_size
        tcp_nodelay = self.settings.tcp_nodelay

        client_done = Event()
        server_done = Event()

        def listener(port):
            ''' Run a listener at the socket
            '''

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                # Set the size of the buffer for this socket
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, bytes_)
                bufsize = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                if bufsize < bytes_:
                    msg = f'recv buffer size is {bufsize}, but need at least {self.settings.bytes}'
                    raise OSError(msg)
                sock.bind((server_ip, port))

                # start listening
                sock.listen(5)
            except OSError as e:
                if hasattr(e, 'winerror') and e.winerror in self.port_winerrs:
                    raise PortBusyError()
                else:
                    raise

            return sock

        def client(listen_sock):
            port = listen_sock.getsockname()[1]
            sock = None

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)

                # Basic flags
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, tcp_nodelay)

                # Set and verify the send buffer size
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, bytes_)
                bytes_actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                if bytes_actual != bytes_:
                    msg = f'client buffer size is {bytes_actual}, but requested {self.bytes}'
                    raise OSError(msg)

                try:
                    sock.bind((client_ip, port))
                except OSError as e:
                    ex = e
                else:
                    ex = None

                if ex is not None:
                    raise ConnectionRefusedError(*ex.args)

                # Do the connect                
                sock.connect((server_ip, port))

            # This exception needs to come first, because it is a subclass
            # of OSError (at least on windows)
            except socket.timeout as e:
                if sock is not None:
                    self._close_sockets(sock, bytes_=bytes_)
                msg = f'client socket timed out in connection attempt to the server at {server_ip}:{port}'
                ex = ConnectionRefusedError(msg)

                # Certain "port busy" errors are raised as OSError. Check whether
            # they match a whitelist of known port errors to map into port busy
            except OSError as e:
                msg = f'connection failed between server {server_ip} and client {client_ip}'
                # Windows-specific errors
                if hasattr(e, 'winerror') and e.winerror in self.port_winerrs:
                    self._console.debug(msg)
                    ex = PortBusyError(msg)
                elif hasattr(e, 'winerror') and e.winerror in self.conn_winerrs:
                    self._console.debug(msg)
                    ex = ConnectionError(msg)
                else:
                    raise

            # For everything else, we still need to clean up
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
            conn = None
            ex = None
            # Try to get a connection
            t0 = perf_counter()
            #            ex = TimeoutError('received no attempted client connections')
            try:
                while perf_counter() - t0 < timeout:
                    try:
                        listen_sock.settimeout(0.01 + timeout - (perf_counter() - t0))
                        conn, (other_ip, _) = listen_sock.accept()
                    except socket.timeout:
                        continue
                    #                    except OSError as e:
                    #                        # Windows-specific errors
                    #                        if hasattr(e, 'winerror') and e.winerror in self.port_winerrs:
                    #                            self._console.debug(f'port {port} is inaccessible')
                    #                            raise PortBusyError
                    #                        else:
                    #                            raise
                    #                    except AttributeError:
                    #                        if listen_sock is None:
                    #                            raise ConnectionError('no listener to provide server connection socket')
                    #                        else:
                    #                            raise

                    if other_ip == client_ip:
                        break
                    else:
                        self._console.warning(f'connection attempt from unexpected ip {other_ip} instead of {client_ip}')
                        if conn is not None:
                            self._close_sockets(conn, bytes_=bytes_)
                            conn = None
                else:
                    raise TimeoutError('no connection attempt seen from the expected client')
            except BaseException as e:
                listen_sock.settimeout(timeout)
                ex = e
            else:
                listen_sock.settimeout(timeout)

                # Basic flags
                conn.settimeout(timeout)
                #            conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, tcp_nodelay)

                # Set and verify the send buffer size
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, bytes_)
                bytes_actual = conn.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                if bytes_actual != bytes_:
                    msg = f'server buffer size is {bytes_actual}, but requested {self.bytes}'
                    raise OSError(msg)

            if not client_done.wait(timeout):
                # Suppress the server exception if the client is already
                # raising one
                if ex is not None:
                    self._console.debug(f'server connection exception: {repr(ex)} (superceded by client exception)')
                    ex = None
                if conn is not None:
                    self._close_sockets(conn, bytes_=bytes_)

            server_done.set()

            if ex is not None:
                raise ex

            return conn

        def open_():
            global _tcp_port_offset, listen_sock

            if self.settings.port != 0:
                port = self.settings.port + _tcp_port_offset
            else:
                port = 0

            listen_sock = listener(port)

            # Keep trying on many ports
            try:
                ret = lb.concurrently(lb.Call(server, listen_sock=listen_sock),
                                      lb.Call(client, listen_sock=listen_sock))
            except:
                self._close_sockets(listen_sock, bytes_=0)
                raise
            finally:
                if self.settings.port != 0:
                    _tcp_port_offset = (_tcp_port_offset + 1) % 5000

            ret['listener'] = listen_sock
            return ret

        try:
            t0 = perf_counter()

            if self.settings.port == 0:
                ret = open_()
            else:
                # Allow chances to try other ports
                ret = lb.retry(PortBusyError, 100)(open_)()
            p = ret['client'].getsockname()[1]
            self._console.debug(
                f'server {server_ip}:{p} connected to client {client_ip}:{p} in {perf_counter() - t0:0.3f}s')
        except PortBusyError:
            raise ConnectionError(r'failed to connect on {retries} ports')

        return ret['server'], ret['client'], ret['listener']

    def _run(self, client_sock, server_sock, buffer_size,
             duration=None, count=None, end_event=None):
        if duration is count is end_event is None:
            raise ValueError('must pass at least one of duration, count, and end_event to specify end condition')

        if self.settings.tcp_nodelay and buffer_size < self.mss():
            raise ValueError(f'with tcp_nodelay enabled, set buffer_size at least as large as the MSS ({self.mss()})')

        if self.settings.server == self.settings.receiver:
            send_sock, recv_sock = client_sock, server_sock
        else:
            send_sock, recv_sock = server_sock, client_sock

        t_start = perf_counter()

        # Are we running in the background?
        background = end_event is not None

        if background:
            count = 1

        # Pull some parameters and thread sync objects into the namespace
        timeout = self.settings.timeout
        bytes_ = buffer_size
        sync = self.settings.sync_each
        delay = self.settings.delay
        rx_ready = Event()
        tx_ready = Event()

        if end_event is None:
            end_event = Event()

        except_event = Event()

        def check_status():
            lb.sleep(0)

            # Bail if the sender hit an exception
            if except_event.is_set():
                raise lb.ThreadEndedByMaster()

        def traffic_done(i):
            if background and end_event.is_set():
                return True
            elif (count is not None) and i >= count:
                return True
            elif (duration is not None) and perf_counter() - t_start >= duration:
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
                ''' Receive a single buffer of data
                '''
                bytes_left = int(bytes_)
                do_sync()
                t0 = t1 = t2 = perf_counter()
                i = 0

                # Receive rx_buffers until we receive the full send buffer
                while bytes_left > 0:
                    if t2 - t0 > timeout:
                        msg = f'timeout while waiting to receive {bytes_left} of {bytes_} bytes'
                        raise TimeoutError(msg)
                    try:
                        bytes_left -= recv_sock.recv_into(buf[-bytes_left:],
                                                          bytes_left)
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

                # One to the wind
                single()
                rx_ready.set()

                i = 0
                # Receive the test data
                while not traffic_done(i):
                    t0, t1, t2, rx_buffer0_size, rx_buffer_count = single()
                    starts.append(t0)
                    rx_buffer0_finishes.append(t1)
                    finishes.append(t2)
                    rx_buffer_sizes.append(rx_buffer0_size)
                    rx_buffers.append(rx_buffer_count)

                    i += 1

                # One to the wind
            #                single()

            except lb.ThreadEndedByMaster:
                self._console.debug(f'{self.__class__.__name__}() ended by master thread')
                except_event.set()
            except BaseException:
                if not (end_event is not None and end_event.is_set()):
                    except_event.set()
                    raise

            return {'t_rx_start': starts,
                    't_rx_end_buffer0': rx_buffer0_finishes,
                    't_rx_end': finishes,
                    'rx_buffer0_size': rx_buffer_sizes,
                    'rx_buffer_count': rx_buffers}

        def sender():
            ''' This runs in the receive thread, with the socket connected.
            '''
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

                # Throwaway buffer
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

                # Throwaway buffer
            #                single()

            except lb.ThreadEndedByMaster:
                self._console.debug(f'{self.__class__.__name__}() ended by master thread')
                except_event.set()
            except BaseException as e:
                if not (end_event is not None and end_event.is_set()):
                    self._console.debug(f'suppressed exception in sender: {e}')
                    except_event.set()

            return {'start': start,
                    'bytes': bytes_,
                    't_tx_start': start_timestamps,
                    't_tx_end': finish_timestamps}

        def background_thread():
            try:
                ret = None
                i = 0
                while not end_event.is_set():
                    ret = lb.concurrently(sender, receiver, traceback_delay=True)
                    self._background_queue.put(ret)
                    i += 1
                self._console.debug(f'finished traffic test of {i} buffers of {bytes_} bytes')
            except BaseException as e:
                if not self._background_event.is_set():
                    self._console.warning(f'background thread exception - traceback: {traceback.format_exc()}')
                    self._background_queue.put(e)
                self._close_sockets(send_sock, recv_sock, listen_sock, bytes_=buffer_size)
            finally:
                self._console.debug('background thread finished')

        if background:
            thread = Thread(target=background_thread)
            thread.start()
            tx_ready.wait(timeout=self.settings.timeout)
            rx_ready.wait(timeout=self.settings.timeout)
            self._console.debug(f'first buffer sent after {perf_counter() - t_start:0.3f}s')
        else:
            ret = lb.concurrently(sender, receiver, traceback_delay=True)
            i = len(ret["t_tx_start"])
            self._console.debug(f'finished traffic test of {i} buffers of {bytes_} bytes')
            return ret

    def acquire(self, buffer_size, count=None, duration=None):
        ''' Repeatedly send traffic in buffers of `buffer_size` bytes. Stop
            when the first of `count` buffers have been sent, or `duration`
            time has elapsed. At least one of `count` or `duration` must be
            set. This call will block until the traffic is done.
            
            :param count: Maximum number of buffers to send, or None to skip this check
            :param duration: Maximum duration of the traffic sent, or None to skip this check

            :returns: a DataFrame indexed on PC time containing columns 'bits_per_second', 'duration', 'delay', 'queuing_duration'
        '''
        #        t0 = perf_counter()

        # Connect all the sockets   
        server_sock, client_sock, listener = self._open_sockets(buffer_size)

        try:
            ret = self._run(client_sock=client_sock,
                            server_sock=server_sock,
                            count=count,
                            buffer_size=buffer_size,
                            duration=duration)

        finally:
            self._close_sockets(client_sock, server_sock, listener)

        return self._make_dataframe(ret)

    def _make_dataframe(self, worker_data):
        self._console.debug('making dataframe')
        start = worker_data.pop('start', None)
        if start is None:
            raise IOError('the run did not return data')

        buffer_size = worker_data.pop('bytes')

        # Race condition may make the lengths different by 1
        count = min(len(worker_data['t_tx_start']), len(worker_data['t_rx_start']))

        for k in worker_data.keys():
            worker_data[k] = worker_data[k][:count]

        # Compute elapsed timings, shift timestamps, etc.
        ret = pd.DataFrame(worker_data)

        timestamp = pd.TimedeltaIndex(ret.t_tx_start, unit='s') + start

        duration = ret.t_rx_end - ret.t_rx_start

        # The average data rate after the first partial receive buffer
        late_rate = (buffer_size - ret.rx_buffer0_size) / (ret.t_rx_end - ret.t_rx_end_buffer0)

        # Estimate the clock value immediately before the data arrived at the 
        # receive socket based on the remainder of the data
        est_rx_buffer0_start = ret.t_rx_end_buffer0 - ret.rx_buffer0_size / late_rate

        ret = pd.DataFrame({'bits_per_second': 8 * buffer_size / duration,
                            'duration': duration,
                            'delay': est_rx_buffer0_start - ret.t_tx_start,  # ret.t_rx_start-ret.t_tx_start,
                            'queuing_duration': ret.t_tx_end - ret.t_tx_start,
                            'rx_buffer_count': ret.rx_buffer_count,
                            't_rx_end_buffer0': ret.t_rx_end_buffer0,
                            'timestamp': timestamp})

        return ret.set_index('timestamp')

    def mss(self):
        return self.mtu() - 40

    def mtu(self):
        iface = list_network_interfaces('physical_address')[self.settings.receiver]['interface']
        return psutil.net_if_stats()[iface].mtu

    def wait_for_interfaces(self, timeout):
        errors = (TimeoutError, ConnectionRefusedError)

        t0 = time.perf_counter()
        socks = lb.until_timeout(errors, timeout)(self._open_sockets)()
        self._close_sockets(*socks)
        elapsed = perf_counter() - t0
        self._console.debug(f'interfaces ready after {elapsed:0.2f}s')
        return elapsed


# Examples
# ClosedLoopNetworkingTest example
# if __name__ == '__main__':
#     lb.show_messages('debug')
#
#     net = ClosedLoopTCPBenchmark(server='WLAN_AP_DUT',
#                                  client='WLAN_Client_DUT',
#                                  receiver='WLAN_Client_DUT',
#                                  port=0,
#                                  tcp_nodelay=True)
#
#     mss_mults = []
#     binary_mults = []
#     with net:
#         for j in range(1):
#             net.start_traffic(1460 * 10)
#             print(net.is_running())
#             lb.sleep(3)
#             print(net.is_running())
#             ret = net.stop_traffic()
#             print(net.is_running())
#            lb.console.info(f'test {j}')
#            ret = mss_mults.append(net.acquire(1460*10,count=1000))
#            net.settings.bytes = 4096*4
#            binary_mults.append(net.acquire(1000))

#            traffic = net.acquire(50)
#            pylab.figure()
#            traffic.hist(bins=51)
#            traffic[['duration','delay']].plot(marker='.', lw=0)
#            traffic['rate'] = net.settings.bytes/traffic.duration*8/1e6
#            print(f'{traffic.rate.median()} +/- {2*traffic.rate.std()} Mbps')
#            print('medians\n',traffic.median(axis=0))

# # IPerf example
# if __name__ == '__main__':
#    lb.show_messages('debug')
#    ips = IPerf(server=True, port=5050, time=10, interval=0.25, udp=True)
#    ipc = IPerf('127.0.0.1', port=5050, time=10, interval=0.25, udp=True, bit_rate='1M')
#    ips.open()
#    ipc.open()
#
#    for i in range(1):
#        ips.background()
#        lb.sleep(1)
#        ipc.background()
#
#        lb.sleep(5)
#
#        ipc.kill()
#        ips.kill()
#
#        ips_result = ips.fetch()
#        ipc_result = ipc.fetch()
#
#    print(ips_result)
#    print(ipc_result)

# IPerfBoundPair example
if __name__ == '__main__':
    lb.show_messages('debug')

    iperf = IPerfBoundPair(
        server='127.0.0.1',
        client='127.0.0.1',
        time=3,
        interval=0.25,
        udp=True
    )

    data = iperf.foreground()