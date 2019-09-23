# -*- coding: utf-8 -*-
"""
@author: Dan Kuester <daniel.kuester@nist.gov>,
         Michael Voecks <michael.voecks@nist.gov>
"""
__all__ = ['IPerfClient','IPerf','IPerfOnAndroid', 'IPerfBoundPair',
           'ClosedLoopTCPBenchmark']

import datetime
import labbench as lb
import numpy as np
import pandas as pd
import socket
import ssmdevices.lib
import time

from time import perf_counter
from threading import Event
from io import StringIO
import psutil

if '_tcp_port_offset' not in dir():
    _tcp_port_offset = 0

# Make sure the performance counter is initialized
perf_counter()

class IPerf(lb.CommandLineWrapper):
    ''' Run an instance of iperf, collecting output data in a background thread.
        When running as an iperf client (server=False), 
        The default value is the path that installs with 64-bit cygwin.
    '''
    
    class settings(lb.CommandLineWrapper.settings):
        binary_path   = lb.Unicode(ssmdevices.lib.path('iperf.exe'))
        timeout       = lb.Float(6, min=0, help='wait time for traffic results before throwing a timeout exception (s)')
        port          = lb.Int(5001, command='-p', min=1, help='connection port')
        bind          = lb.Unicode(None, command='-B', allow_none=True, help='bind connection to specified IP')
        tcp_window_size = lb.Int(None, command='-w', min=1, help='(bytes)', allow_none=True)
        buffer_size   = lb.Int(None, command='-l', min=1, allow_none=True,
                               help='Size of data buffer that generates traffic (bytes)')
        interval      = lb.Float(0.25, command='-i', min=0.01, help='Interval between throughput reports (s)')
        bidirectional = lb.Bool(False, command='-d', help='Send and receive simultaneously')
        udp           = lb.Bool(False, command='-u', help='use UDP instead of the default, TCP')
        bit_rate      = lb.Unicode(None, allow_none=True, command='-b',
                                   help='Maximum bit rate (append unit for size, e.g. 10K)')
        time          = lb.Int(None, min=0, max=16535, command='-t', allow_none=True,
                               help='time in seconds to transmit before quitting (default 10s)')
        arguments     = lb.List(['-n','-1','-y','C'], allow_none=True)

    def fetch (self):
        ''' Retreive csv-formatted text from standard output and parse into
            a pandas DataFrame.
        '''
        result = self.read_stdout()

        columns = 'timestamp','source_address',\
                  'source_port','destination_address','destination_port',\
                  'test_id','interval','transferred_bytes','bits_per_second'

        if self.settings.udp:
            columns = columns + ('jitter_milliseconds',
                                 'datagrams_lost',
                                 'datagrams_sent',
                                 'datagrams_loss_percentage',
                                 'datagrams_out_of_order')

        columns = ['iperf_'+c for c in columns]
        
        data = pd.read_csv(StringIO(result), header=None,index_col=False,
                           names=columns)
        
        # throw out the last row (potantially a summary of the previous rows)
        if len(data)==0:
            data = data.append([None])
        data.drop(['iperf_interval','iperf_transferred_bytes','iperf_test_id'],inplace=True,axis=1)
        data['iperf_timestamp'] = pd.to_datetime(data['iperf_timestamp'], format='%Y%m%d%H%M%S')
        data['iperf_timestamp'] = data['iperf_timestamp']+\
                                  pd.TimedeltaIndex((data.index*self.settings.interval)%1,'s')

        return data

    def background (self, *extra_args, **flags):
        if self.settings.udp and self.settings.buffer_size is not None:
            self.logger.warning('iperf might not behave nicely setting udp=True with buffer_size')
        if not self.settings.udp and self.settings.bit_rate is not None:
            raise ValueError('iperf does not support setting bit_rate in TCP')

        with self.respawn:#, self.exception_on_stderr:
            if self.settings.resource:
                super(IPerf, self).background('-c', str(self.settings.resource), *extra_args, **flags)
            else:
                super(IPerf, self).background('-s', *extra_args, **flags)

    def start(self):
        self.background()

import subprocess as sp

class IPerfOnAndroid(IPerf):
    remote_binary_path = '/data/local/tmp/iperf'

    class settings(IPerf.settings):
        binary_path        = lb.Unicode(ssmdevices.lib.path('adb.exe'))
        remote_binary_path = lb.Unicode('/data/local/tmp/iperf',
                                             )
        arguments          = lb.List(['shell', remote_binary_path.default_value,
                                     # '-y', 'C'
                                          ])

    def connect(self):
        with self.no_state_arguments:
#            self.logger.warning('TODO: need to fix setup for android iperf, but ok for now')
#            devices = self.foreground('devices').strip().rstrip().splitlines()[1:]
#            if len(devices) == 0:
#                raise Exception('adb lists no devices. is the UE connected?')
            self.logger.debug('waiting for USB connection to phone')
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True,
                   timeout=30)

            lb.sleep(.1)
            self.logger.debug('copying iperf onto phone')
            sp.run([self.settings.binary_path, "push", ssmdevices.lib.path('android','iperf'),
                   self.settings.remote_binary_path], check=True, timeout=2)
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=2)
            sp.run([self.settings.binary_path, "shell", 'chmod', '777',
                    self.settings.remote_binary_path], timeout=2)
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=2)
    
#            # Check that it's executable
            self.logger.debug('verifying iperf execution on phone')
            cp = sp.run([self.settings.binary_path, 'shell',
                         self.settings.remote_binary_path, '--help'],
                         timeout=2, stdout=sp.PIPE)
            if cp.stdout.startswith(b'/system/bin/sh'):
                raise Exception('could not execute!!! ', cp.stdout)
            self.logger.debug('phone is ready to execute iperf')

    def start (self):
        super(IPerfOnAndroid,self).start()
        test = self.read_stdout(1)        
        if 'network' in test:
            self.logger.warning('no network connectivity in UE')

    def kill (self, wait_time=3):
        ''' Kill the local process and the iperf process on the UE.
        '''

        # Kill the local adb process as normal
        super(IPerfOnAndroid,self).kill()

        # Now's where the fun really starts
        with self.no_state_arguments:
            # Find and kill processes on the UE
            out = self.foreground('shell', 'ps')
            for line in out.splitlines():
                line = line.decode(errors='replace')
                if self.settings.remote_binary_path in line.lower():
                    pid = line.split()[1]
                    self.logger.debug('killing zombie iperf. stdout: {}'\
                                      .format(self.foreground('shell', 'kill', '-9', pid)))
            lb.sleep(.1)
            # Wait for any iperf zombie processes to die
            t0 = time.time()
            while time.time()-t0 < wait_time and wait_time != 0:
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
                self.logger.warning('stdout: {}'.format(repr(l)))
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
        
        self.logger.debug('waiting for cellular data connection')
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
        self.logger.debug('cellular data available after {} s'.format(time.time() - t0))

    def reboot(self, block=True):
        ''' Reboot the device.

        :param block: if this evaluates to True, block until the device is ready to accept commands
        :return:
        '''
        self.logger.info('rebooting')
        sp.run([self.settings.binary_path, 'reboot'], check=True, timeout=2)
        self.wait()

    def wait(self, timeout=30):
        ''' Block until the device is ready to accept commands

        :return: None
        '''
        sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=timeout)
        self.logger.debug('device is ready')


class IPerfClient(IPerf):
    ''' This class is deprected. Use IPerf instead
    '''
    
    def __imports__ (self, *args, **kws):
        self.logger.warning('this class is deprecated! use {} instead'\
                            .format(repr(IPerf)))
        super(IPerfClient, self).__imports__(*args, **kws)


class IPerfBoundPair(lb.Device):
    ''' Run an iperf client and a server on the host computer at the same time. They are
        bound to opposite interfaces to ensure data is routed between them, and not through
        localhost or any other interface.
    '''
    
    # Copy the IPerf settings. Most of these are simply passed through 
    class settings(IPerf.settings):
        resource = lb.Unicode(help='ignored - use sender and receiver instead')
        bind = None # blanked out - determined for the client and server based on sender and receiver addresses
        sender = lb.Unicode(help='the ip address to use for the iperf client, which must match a network interface on the host')
        receiver = lb.Unicode(help='the ip address to use for the iperf server, which must match a network interface on the host')
        port_max = lb.Int(6000, min=1, read_only=True,
                          help='highest port number to use when cycling through ports')

    class state(lb.Device.state):
        pass

    def __init__ (self, *args, **kws):
        super().__init__(*args, **kws)
        self.port_start = self.settings.port

    def connect(self):
        settings = dict([(k,getattr(self.settings, k)) for k,v in self.settings.traits().items() if not v.read_only])
        
        for k in 'resource', 'sender', 'receiver', 'bind':
            if k in settings:
                del settings[k]

        client = IPerf(resource=self.settings.sender,
                       bind=self.settings.receiver,
                       **settings)
        server = IPerf(bind=self.settings.sender, **settings)
        
        server.connect()
        client.connect()
        
        self.backend = {'iperf_client': client, 'iperf_server': server}
        
    def disconnect(self):
        try:
            self.kill()
        except TypeError as e:
            if 'NoneType' not in str(e):
                raise

    def kill(self):
        backend = self.backend
        try:
            backend['iperf_server'].kill()
        finally:
            backend['iperf_client'].kill()

    def running(self):
        return self.backend['iperf_client'].running()\
               and self.backend['iperf_server'].running()

    def fetch(self):
        client = self.backend['iperf_client'].fetch()
        server = self.backend['iperf_server'].fetch()
        
        return {'iperf_client': client,
                'iperf_server': server}

    def start(self):
        # Increment the port, because binding seems to cause blockin in win32
        self.settings.port = self.settings.port + 1
        if self.settings.port > self.settings.port_max:
            self.settings.port = self.port_start
        
        self.backend['iperf_client'].settings.port = self.settings.port
        self.backend['iperf_server'].settings.port = self.settings.port
        
        self.backend['iperf_server'].start()
        self.backend['iperf_client'].start()
        
    def acquire(self, duration):
        ''' Acquire iperf output for the specified duration and return.
            Raises a lb.DeviceConnectionLost if iperf stops before the
            duration has finished.
            
            Call run before 
        '''
        if self.running():
            # Blank any buffered output
            self.fetch()
        else:
            # Otherwise, start
            self.start()
        
        # Wait for the duration, checking regularly to ensure the client is running
        t0 = time.time()
        while time.time()-t0 < duration:
            time.sleep(min(0.5,duration-(time.time()-t0)))
            if not self.running():
                raise lb.DeviceConnectionLost('iperf stopped unexpectedly')

        ret = self.fetch()
        lb.logger.debug('  iperf_client and server returned {} and {} rows'\
                       .format(len(ret['iperf_client']),len(ret['iperf_server'])))
        
        self.kill()
        return ret


m1  = 0x5555555555555555
m2  = 0x3333333333333333
m4  = 0x0f0f0f0f0f0f0f0f
m8  = 0x00ff00ff00ff00ff
m16 = 0x0000ffff0000ffff
m32 = 0x00000000ffffffff
h01 = 0x0101010101010101

def bit_errors(x):
    ''' See: https://en.wikipedia.org/wiki/Hamming_weight
    '''
    if x is None:
        return None
#    a1 = np.frombuffer(buf1,dtype='uint64')
    x = np.frombuffer(x[:(len(x)//8)*8],dtype='uint64').copy()
    x -= (x >> 1) & m1;
    x = (x & m2) + ((x >> 2) & m2);
    x = (x + (x >> 4)) & m4;
    return ((x * h01) >> 56).sum()

from contextlib import suppress, AbstractContextManager

def get_ipv4_address(iface):
    ''' Try to look up the IP address corresponding to the network interface
        referred to by the OS with the name `iface`.
        
        If the interface does not exist, the medium is disconnected, or there
        is no IP address associated with the interface, raise `ConnectionError`.
    '''
    addrs = psutil.net_if_addrs()
    
    # Check whether the interface exists
    if iface not in addrs:
        available = ', '.join(addrs.keys())
        msg = f'specified receiver interface {iface} but only ({available}) are available'
        raise ConnectionError(msg)            
    
    # Check whether it's up
    if not psutil.net_if_stats()[iface].isup:
        raise ConnectionError(f'the {iface} network interface is disabled or disconnected')
        
    # Lookup and return the address
    for addr_struct in addrs[iface]:
        if 'AF_INET' in str(addr_struct.family):
            return addr_struct.address
    else:
        raise ConnectionError(f'no ipv4 address associated with interface "{iface}"')

class ClosedLoopBenchmark(lb.Device):
    ''' Profile closed-loop traffic between two network interfaces
        on this computer. Takes advantage of the system clock as a common
        basis for traffic delay measurement, with uncertainty approximately
        equal to the system time resolution.
    '''

    class settings(lb.Device.settings):
        server = lb.Unicode(help='the name of the network interface that will send data')
        client = lb.Unicode(help='the name of the network interface that will receive data')
        receiver = lb.Unicode(help='the name of the network interface that will send data')
        port = lb.Int(0,
                      min=0,
                      help='TCP or UDP port for networking, or 0 to let the operating system choose')
        resource = lb.Unicode(help='skipd - use sender and receiver instead')        
        timeout = lb.Float(2,
                           min=1e-3,
                           help='timeout before aborting the test')
        bytes = lb.Int(4096,
                       min=0,
                       help='TCP or UDP data buffer size')
        skip = lb.Int(2, min=0,
                      help='extra buffers to send and not log before acquisition')
        tcp_nodelay = lb.Bool(True,
                              help='if True, disable Nagle\'s algorithm')
        sync_each = lb.Bool(False,
                              help='synchronize the start times of the send and receive threads for each buffer at the cost of throughput')

    def __repr__(self):
        return "{name}(server='{server}',client='{client}')"\
               .format(name=self.__class__.__name__,
                       server=self.settings.server,
                       client=self.settings.client)

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
    
    def _close_sockets(self, *sockets, bytes_=None):
        if bytes_ is None:
            bytes_ = self.settings.bytes
            
        for sock in sockets:
            sock.settimeout(0.1)
            
            with suppress_matching_arg0(OSError, arg0=10057):
                sock.send(b'')

            with suppress(OSError):
                t0 = perf_counter()
                while perf_counter()-t0 < 5:
                    try:
                        buf = sock.recv(bytes_)
                    except socket.timeout:
                        break
                    if len(buf) == 0:
                        break
                else:
                    self.logger.warning('failed to flush socket before closing')
            
            with suppress_matching_arg0(OSError, arg0=10057),\
                 suppress_matching_arg0(OSError, arg0='timed out'):
                sock.shutdown(socket.SHUT_RDWR)
            
            with suppress_matching_arg0(OSError, arg0=10057):
                sock.close()

    def _open_sockets(self):
        ''' Connect the supplied client socket to the server.
        '''
        if self.settings.tcp_nodelay and self.settings.bytes < self.mss():
            raise ValueError(f'with tcp_nodelay enabled, set bytes at least as large as the MSS ({self.mss()})')

        if self.settings.receiver not in (self.settings.server, self.settings.client):
            raise ValueError(f'the receiver setting must match the client or server interface name')
        
        global _tcp_port_offset
        
        server_ip = get_ipv4_address(self.settings.server)
        client_ip = get_ipv4_address(self.settings.client)        
        listen_sock = None
        
        timeout = self.settings.timeout
        bytes_ = self.settings.bytes
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
                sock.bind((client_ip, port))

                # Do the connect                
                sock.connect((server_ip, port))
            
            # This exception needs to come first, because it is a subclass
            # of OSError (at least on windows)
            except socket.timeout:
                if sock is not None:
                    self._close_sockets(sock, bytes_=bytes_)
                msg = f'client socket timed out in connection attempt to the server at {server_ip}:{port}'
                raise ConnectionRefusedError(msg)                
                
            # Certain "port busy" errors are raised as OSError. Check whether
            # they match a whitelist of known port errors to map into port busy
            except OSError as e:
                # Windows-specific errors
                if hasattr(e, 'winerror') and e.winerror in self.port_winerrs:
                    self.logger.debug(f'port {port} is inaccessible')
                    raise PortBusyError
                else:
                    raise

            # For everything else, we still need to clean up
            except BaseException:
                if sock is not None:
                    self._close_sockets(sock, bytes_=bytes_)
                raise

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
                while perf_counter()-t0 < timeout:
                    try:
                        listen_sock.settimeout(0.01+timeout-(perf_counter()-t0))
                        conn, (other_ip, _) = listen_sock.accept()
                    except socket.timeout:
                        continue
#                    except OSError as e:
#                        # Windows-specific errors
#                        if hasattr(e, 'winerror') and e.winerror in self.port_winerrs:
#                            self.logger.debug(f'port {port} is inaccessible')
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
                        self.logger.warning(f'connection attempt from unexpected ip {other_ip} instead of {client_ip}')
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
                    self.logger.debug(f'server connection exception: {repr(ex)} (suppressed by client exception)')                
                    ex = None
                if conn is not None:
                    self._close_sockets(conn, bytes_=bytes_)                
                    
            server_done.set()

            if ex is not None:
                raise ex

            return conn

        def connect():
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
                self._close_sockets(listen_sock)
                raise
            finally:
                if self.settings.port != 0:
                    _tcp_port_offset = (_tcp_port_offset+1)%5000

            ret['listener'] = listen_sock
            return ret

        try:
            t0 = perf_counter()
            
            if self.settings.port == 0:
                ret = connect()
            else:
                # Allow chances to try other ports
                ret = lb.retry(PortBusyError, 100)(connect)()
            p = ret['client'].getsockname()[1]
            self.logger.debug(f'server {server_ip}:{p} connected to client {client_ip}:{p} in {perf_counter()-t0:02f}s')
        except PortBusyError:
            raise ConnectionError(r'failed to connect on {retries} ports')

        return ret['server'], ret['client'], ret['listener']

    def _run(self, send_sock, recv_sock, count):
        # Pull some parameters and thread sync objects into the namespace
        timeout = self.settings.timeout
        bytes_ = self.settings.bytes
        skip = self.settings.skip
        sync = self.settings.sync_each
        rx_ready = Event()
        tx_ready = Event()
        except_event = Event()

        def check_status():
            lb.sleep(0)
    
            # Bail if the sender hit an exception
            if except_event.is_set():
                raise lb.ThreadEndedByMaster()

        def receiver():
            buf = bytearray(bytes_)
            starts = []
            finishes = []

            def do_sync():
                if sync:
                    rx_ready.set()
                    while not tx_ready.is_set():
                        pass
                    tx_ready.clear()

            def single():
                i = 0
                remaining = int(bytes_)
                t0 = perf_counter()
                while remaining > 0:
                    i += 1
                    t1 = perf_counter()
                    if t1-t0 > timeout:
                        msg = f'timeout while waiting to receive {remaining} of {bytes_} bytes'
                        raise TimeoutError(msg)
                    try:
                        remaining -= recv_sock.recv_into(buf[-remaining:], remaining)
                    except socket.timeout as e:
                        raise TimeoutError(' '.join(e.args))
#                if i>1:
#                    self.logger.warning(f'buffer read required {i} attempts')
                return t1, t0

            try:
                do_sync()
                
                # A few throwaway buffers to get things started
                for i in range(skip):
                    check_status()
                    single()
        
                # Receive the test data
                for i in range(count):
                    check_status()
                    do_sync()        
                    t1, t0 = single()        
                    starts.append(t0)
                    finishes.append(t1)

                
                self.logger.debug(f'tested {count} x {bytes_} byte buffers')
            except lb.ThreadEndedByMaster:
                self.logger.debug(f'{self.__class__.__name__}() ended by master thread')
                except_event.set()                
            except BaseException:
                except_event.set()
                raise

            return {'t_rx_start': starts,
                    't_rx_end': finishes}

        def sender():
            ''' This runs in the receive thread, with the socket connected.
            '''
            start_timestamps = []
            finish_timestamps = []
            start = None
            
            def do_sync():
                check_status()
                if sync:
                    while not rx_ready.is_set():
                        pass        
                    rx_ready.clear()
                    tx_ready.set()
    
            try:
                do_sync()
                
                # No point in more interesting data unless the point is to debug TCP
                data = b'\x00'*bytes_
        
                # Run through number of "throwaway" bytes
                for i in range(skip):
                    data = np.random.bytes(bytes_)
                    check_status()
                    send_sock.sendall(data)
        
                for i in range(count):
                    data = np.random.bytes(bytes_)
        
                    check_status()
        
                    # (Approximately) synchronize the transmit and receive timing
                    if sync:
                        do_sync()
                    if i == 0:
                        start = datetime.datetime.now()

                    t0 = perf_counter()

                    # Time sending the data
                    try:                    
                        send_sock.sendall(data)
                    except socket.timeout:
                        ex = IOError('timed out attempting to send data')
                    else:
                        ex = None
                    t1 = perf_counter()
                    if ex is not None:
                        raise ex
                    
                    start_timestamps.append(t0)
                    finish_timestamps.append(t1)

            except lb.ThreadEndedByMaster:
                self.logger.debug(f'{self.__class__.__name__}() ended by master thread')
                except_event.set()
            except BaseException as e:
                self.logger.debug(f'suppressed exception in sender: {e}')
                except_event.set()

            return {'start': start,
                    't_tx_start': start_timestamps,
                    't_tx_end': finish_timestamps}

        return lb.concurrently(sender, receiver, traceback_delay=True)
            
    def acquire(self, count):
        t0 = perf_counter()
        
        # Connect all the sockets   
        server_sock, client_sock, listener = self._open_sockets()

        try:
            # Run the test
            if self.settings.server == self.settings.receiver:
                ret = self._run(send_sock=client_sock,
                                recv_sock=server_sock,
                                count=count+2)
            else:
                ret = self._run(send_sock=server_sock,
                                recv_sock=client_sock,
                                count=count+2)
        finally:
            self._close_sockets(client_sock, server_sock, listener)

        self.logger.debug(f'benchmark test finished in {perf_counter()-t0:02f}s')

        start = ret.pop('start', None)
        if start is None:
            print(start)
            raise IOError('the run did not return data')

        # Compute elapsed timings, shift timestamps, etc.
        ret = pd.DataFrame(ret)
        timestamp = pd.TimedeltaIndex(ret.t_tx_start, unit='s')+start

        duration = ret.t_rx_end.iloc[1:-1]-ret.t_rx_start.iloc[1:-1]
        ret = pd.DataFrame({'bits_per_second': 8*self.settings.bytes/duration,
                            'duration': duration,
                            'start_offset': ret.t_rx_start.iloc[1:-1]-ret.t_tx_start.iloc[1:-1],
                            'timestamp': timestamp[1:-1]})

        return ret.set_index('timestamp')
    
    def mss(self):
        return self.mtu()-40
    
    def mtu(self):
        return psutil.net_if_stats()[self.settings.receiver].mtu

    def wait_for_interfaces(self, timeout):
        errors = (TimeoutError,ConnectionRefusedError)
        
        t0 = time.perf_counter()
        socks = lb.until_timeout(errors, timeout)(self._open_sockets)()
        self._close_sockets(*socks)
        elapsed = perf_counter()-t0
        self.logger.debug(f'interfaces ready after {elapsed:0.2f}s')
        return elapsed

#class ReceiveUDPWorker(ReceiveWorker):   
#    def open(self):
#        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#        sock.settimeout(self.timeout)
#        conn = None
#
#        try:
#            # Avoid some already in use errors if we try to reuse the socket
#            # soon after closing it
#            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#            
#            # The receive buffer for this socket (under the hood in the OS)
#            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.bytes)
#            bufsize = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
#            if bufsize < self.bytes:
#                msg = f'recv buffer size is {bufsize}, but need at least {self.bytes}'
#                raise OSError(msg)
#
#            sock.bind((self.receiver, self.port))
#
#            return sock
#        except:
#            try:
#                if conn is not None:
#                    conn.close()
#            except:
#                sock.close()
#            raise
#        
#    def run(self, count):
#        self.bad_data = []
#        starts = [None]*count
#        finishes = [None]*count
#        received = [None]*count            
#        
#        with self.open() as self.sock:
#            self.logger.info('connected')
#            # Receive the data
#            for self.i in range(self.skip+count):
#                # Bail if the sender hit an exception
#                if self.except_event.is_set():
#                    raise lb.ThreadEndedByMaster()
#
#                if self.sync:
#                    self.trigger.wait()
#    
#                started = perf_counter()
#    
#                # UDP datagrams seem to come atomically. One simple recv.
#                data, addr = self.sock.recvfrom(self.bytes)
#                finished = perf_counter()
#    
#                if self.sender != addr[0]:
#                    raise Exception(f"udp sender is {addr[0]}, but expected {self.sender}")
#    
#                try:
#                    i_sent = self.sender_obj.sent.pop(data)
#                except KeyError:
#                    self.bad_data.append(data)
#
#                if self.i>=self.skip:
#                    starts[i_sent-self.skip] = started
#                    finishes[i_sent-self.skip] = finished
#                    received[i_sent-self.skip] = data
#
#            self.logger.info('done')
#                    
#        error_count = [bit_errors(data) for data in received]
#
#        return {'t_rx_start': starts,
#                't_rx_end': finishes,
#                'bit_error_count':  error_count}
#
#
#class SendUDPWorker(SocketWorker):    
#    def open(self):
#        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#        sock.settimeout(self.timeout)
#        
#        try:
#            # The OS-level transmit buffer size for this socket.
#            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,
#                            self.bytes)
#            bytes_actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
#            if bytes_actual != self.bytes:
#                msg = f'send buffer size is {bytes_actual}, but requested {self.bytes}'
#                raise OSError(msg)
#
#            sock.bind((self.sender, 0))
#
#            return sock
#        except:
#            sock.close()
#            raise
#
#    def run(self, count):
#        timestamps = []
#        start = None
#
#        with self.open() as self.sock:             
#            for self.i in range(self.skip+count):
#                # Generate the next data to send
#                data = np.random.bytes(self.bytes) # b'\x00'*size
#                self.sent[data] = self.i
#                
#                # Leave now if the server bailed
#                if self.except_event.is_set():
#                    raise lb.ThreadEndedByMaster()                
#    
#                # Throw any initial samples as configured
#                if self.i>=self.skip:
#                    if self.i==self.skip:
#                        start = datetime.datetime.now()
#                    timestamps.append(perf_counter())
#    
#                if self.sync:
#                    self.trigger.wait()
#                self.sock.sendto(data, (self.receiver, self.port))
#                    
#                lb.sleep(0.)
#
#        return {'start': start,
#                't_tx_start': timestamps,
#                'bytes': self.bytes}
#
#
#class ClosedLoopUDPBenchmark(ClosedLoopBenchmark):
#    ''' Profile closed-loop UDP or TCP traffic between two network interfaces
#        on the computer. Takes advantage of the shared clock to provide
#        one-way traffic delay with uncertainty on the order of the system time
#        resolution.
#        
#        WARNING: This does not work right yet.
#    '''
#
##    @lb.retry((ConnectionError,TimeoutError), 2)
#    def acquire(self, count, mss=1500-40):
#        self.sent = {}
#        
##        if self.settings.sync:
##            trigger = 
##        else:
##            trigger = None
#
#        # Parameters for the client and server
#        events = {'except_event': Event(),
#                  'rx_ready': Event(),
#                  'tx_ready': Event(),
#                  'sync': self.settings.sync_each}
#
#        receiver = ReceiveTCPWorker(self, suppress=True, **events)
#        sender = SendTCPWorker(self, **events)
#
#        ret = lb.concurrently(lb.Call(sender, count),
#                              lb.Call(receiver, count, sender),
#                              traceback_delay=True)
#
#        start = ret.pop('start', None)
#
#        if start is None:
#            raise ConnectionError('send failed')
#
#        ret = pd.DataFrame(ret)
#        dt = pd.TimedeltaIndex(ret.t_tx_start, unit='s')
#
#
#        ret = pd.DataFrame({'bytes_sent': ret.bytes,
#                            'duration': ret.t_rx_end - ret.t_rx_start,
##                            'send_duration': send_duration,
##                            'receive_duration': receive_duration,
##                            'delay': delay,
#                            'start_offset': ret.t_rx_start-ret.t_tx_start,
##                            'finish_delay': ret.t_rx_end-ret.t_tx_end,
#                            'timestamp': dt+start})
#
#        return ret.set_index('timestamp')

# Examples
# ClosedLoopNetworkingTest example
if __name__ == '__main__':
    lb.show_messages('debug')

    net = ClosedLoopTCPBenchmark(server='WLAN_AP_DUT',
                                 client='WLAN_Client_DUT',
                                 receiver='WLAN_Client_DUT',
                                 port=0,
                                 bytes=4096*4,#1460*10,
                                 tcp_nodelay=True)

    mss_mults = []
    binary_mults = []
    with net:        
        for j in range(100):
            lb.logger.info(f'test {j}')
            net.settings.bytes = 1460*10
            mss_mults.append(net.acquire(1000))
            net.settings.bytes = 4096*4
            binary_mults.append(net.acquire(1000))

#            traffic = net.acquire(50)
##            pylab.figure()
##            traffic.hist(bins=51)            
#    #        traffic[['duration','delay']].plot(marker='.', lw=0)
#            traffic['rate'] = net.settings.bytes/traffic.duration*8/1e6
#            print(f'{traffic.rate.median()} +/- {2*traffic.rate.std()} Mbps')
##            print('medians\n',traffic.median(axis=0))

#if __name__ == '__main__':
#    lb.show_messages('debug')
#    ips = IPerf(interval=0.5, udp=True)
#
#    ipc = IPerf('127.0.0.1',interval=1, time=10000, udp=True, bit_rate='1M')
##    ipc.iperf_path = r'..\lib\iperf.exe'
#
#    with ipc,ips:
#        for i in range(1):
#            ips.start()
#            lb.sleep(1)
#            ipc.start()
#            lb.sleep(20)
#            ipc.kill()
#            ips.kill()
#            ips_result = ips.read_stdout()
#            ipc_result = ipc.read_stdout()
