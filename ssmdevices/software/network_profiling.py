# -*- coding: utf-8 -*-
"""
@author: Dan Kuester <daniel.kuester@nist.gov>,
         Michael Voecks <michael.voecks@nist.gov>
"""
from future import standard_library
standard_library.install_aliases()

from builtins import super
from builtins import str

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

class SocketWorker:
    def __init__ (self, receive_ip, send_ip, logger, settings, events, suppress=False):
        self.receiver = receive_ip
        self.sender = send_ip

        self.bytes = settings.bytes
        self.skip = settings.skip
        self.port = settings.port
        self.timeout = settings.timeout
        self.tcp_nodelay = settings.tcp_nodelay
        self.sync = settings.sync_each
        
        self.logger = logger
       
        self.rx_ready = events['rx_ready']
        self.tx_ready = events['tx_ready']
        self.except_event = events['except_event']

        self.suppress = suppress
        
        self.i = 0
        self.sock = None
        self.conn = None
        self.sent = {}
        self.bad_data = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.except_event.set()
        self.do_sync()
        self.teardown()

    def teardown(self):
        pass

    def run(self, count):        
        try:
            ret = {}

            self.open()            
            ret = self(count)
        except lb.ThreadEndedByMaster:
            self.logger.debug(f'{self.__class__.__name__}() ended by master thread')
            self.except_event.set()
        except BaseException as e:
            if self.suppress:
                self.logger.debug(f'suppressed exception {e}')
            else:
                raise
        finally:
            self.teardown()

        return ret

    def _check_thread(self):
        ''' End this thread if another thread requests it
        '''
        lb.sleep(0)

        # Bail if the sender hit an exception
        if self.except_event.is_set():
            raise lb.ThreadEndedByMaster()
            
    def open(self):
        raise NotImplementedError
        
    def __call__(self):
        raise NotImplementedError

    def connection_check(self):
        try:
            self.open()            
        except lb.ThreadEndedByMaster:
            self.logger.debug(f'{self.__class__.__name__}() ended by master thread')
            self.except_event.set()
        except BaseException as e:
            if self.suppress:
                self.logger.debug(f'suppressed exception {e}')
            else:
                raise
        finally:
            self.teardown()

class ReceiveWorker(SocketWorker):
    def do_sync(self):
        if self.sync:
            self.rx_ready.set()
            while not self.tx_ready.is_set():
                pass
            self.tx_ready.clear()

#    def run (self, count, sender_obj):
#        self.sender_obj = sender_obj
#        return super().run(count)


class SendWorker(SocketWorker):
    def do_sync(self):
        self._check_thread()
        if self.sync:
            while not self.rx_ready.is_set():
                pass        
            self.rx_ready.clear()
            self.tx_ready.set()

from contextlib import suppress, AbstractContextManager

class suppress_matching_arg0(AbstractContextManager):
    """Context manager to suppress specified exceptions

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
    
def shutdown(sock):   
    with suppress_matching_arg0(OSError, arg0=10057):
        sock.send(b'')
    
    with suppress_matching_arg0(OSError, arg0=10057):
        sock.recv(0)

    with suppress_matching_arg0(OSError, arg0=10057),\
         suppress_matching_arg0(OSError, arg0='timed out'):
        sock.shutdown(socket.SHUT_RDWR)

    with suppress_matching_arg0(OSError, arg0=10057):
        sock.close()

class ReceiveTCPWorker(ReceiveWorker):
    def open(self):        

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(self.timeout)

        # Set the size of the buffer for this socket
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.bytes)
        bufsize = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        if bufsize < self.bytes:
            msg = f'recv buffer size is {bufsize}, but need at least {self.bytes}'
            raise OSError(msg)                

        self.sock.bind((self.receiver, self.port))
        self.logger.debug(f'server/receive socket bound to {self.receiver}:{self.port}')

        # start listening
        self.sock.listen(5)

        self.wait_for_connection()

    def teardown(self):
#        if hasattr(self.sock, 'close'):
#            shutdown(self.sock)
        self.do_sync()
        self.do_sync()
        if hasattr(self.conn, 'close'):
            shutdown(self.conn)
#            self.sock.close()
        self.logger.debug(f'server/receive sockets closed')

#    @lb.retry(ConnectionError, 3)
    def wait_for_connection(self):        
        # Notify the sender that we're ready
        self.do_sync()

        while True:
            # Try to get a connection
            try:
                ex = None
                self.conn, (other_addr, _) = self.sock.accept()
                self.conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.conn.settimeout(self.timeout)
            except socket.timeout:
                msg = f'server/receive timeout waiting for a connection from the sender'
                ex = ConnectionRefusedError(msg)
            except OSError as e:
                if e.args[0] == 10048:
                    msg = f'server/receive timeout waiting for a connection from the sender'
                    ex = ConnectionRefusedError(msg)                    
                else:
                    raise
            if ex is not None:
                if self.conn is not None:
                    shutdown(self.conn)
                raise ex

            # Validate it is from the expected sender
            if other_addr == self.sender:
                msg = f'accepted TCP connection from sender ({self.sender})'
                self.logger.debug(msg)
                break
            else:
                shutdown(self.conn)
                msg = f'ignored connection attempt from unexpected ip {other_addr[0]} instead of {self.sender}'
                self.logger.warning(msg)

    def __call__(self, count):
        self.logger.debug('receive thread start')
#        self.wait_for_connection()
        
        buf = bytearray(self.bytes)
        starts = []
        finishes = []

        def receive():
            remaining = int(self.bytes)
            t0 = perf_counter()
            while remaining > 0:
                t1 = perf_counter()
                if t1-t0 > self.timeout:
                    msg = f'timeout while waiting to receive {remaining} of {self.bytes} bytes on {self.receiver}'
                    raise TimeoutError(msg)
                
                try:
                    remaining -= self.conn.recv_into(buf[-remaining:], remaining)
                except socket.timeout as e:
                    raise TimeoutError(' '.join(e.args))
            return t1, t0

        # A few throwaway buffers to get things started
        for i in range(self.skip):
            self._check_thread()

            # Go!
            receive()

        # Receive the test data
        for self.i in range(count):
            self._check_thread()

            # (Approximately) synchronize the transmit and receive timing
            # to compute latency from the end time
            if self.sync:
                self.do_sync()

            t1, t0 = receive()

            starts.append(t0)
            finishes.append(t1)

        self.logger.debug(f'received {count} buffers of {self.bytes} TCP data')

        return {'t_rx_start': starts,
                't_rx_end': finishes}

class SendTCPWorker(SendWorker):
    def open(self):
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.bytes)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Verify the send buffer size
        bytes_actual = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        if bytes_actual != self.bytes:
            msg = f'send buffer size is {bytes_actual}, but requested {self.bytes}'
            raise OSError(msg)

        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, self.tcp_nodelay)        
        self.sock.bind((self.sender, self.port))
        self.logger.debug(f'client/sender bound to {self.sender}:{self.port}')        
        
        self.connect()
        
    def teardown(self):
        self.do_sync() 
        if hasattr(self.sock, 'close'):
            shutdown(self.sock)
        self.logger.debug(f'client/send sockets closed')
        self.do_sync()

#    @lb.retry(ConnectionError, 3)
    def connect(self):
        # Wait for the receive socket to be ready
        self.do_sync()
        
        self.logger.debug(f'send socket attempting to connect to receiver at {self.receiver}:{self.port}')
        try:
            ex = None
            self.sock.connect((self.receiver, self.port))
        except socket.timeout:
            msg = f'send socket timed out in connection attempt to the receiver at {self.receiver}:{self.port}'
            ex = ConnectionRefusedError(msg)
        except BaseException as e:
            self.except_event.set()
            self.logger.warning(f'unhandled receive exception {str(e)}')
            raise
        else:
            msg = f'send socket ({self.sender}:{self.port}) connected to receive socket ({self.receiver})'
            self.logger.debug(msg)
        
        if ex is not None:
            raise ex

    def __call__(self, count):
        ''' This runs in the receive thread, with the socket connected.
        '''
#        self.connect()

        start_timestamps = []
        finish_timestamps = []
        start = None

        # No point in more interesting data unless the point is to debug TCP
        data = b'\x00'*self.bytes

        # Run through number of "throwaway" bytes
        for self.i in range(self.skip):
            data = np.random.bytes(self.bytes)
            self._check_thread()
            self.sock.sendall(data)

        for self.i in range(count):
            data = np.random.bytes(self.bytes)

            self._check_thread()

            # (Approximately) synchronize the transmit and receive timing
            if self.sync:
                self.do_sync()
            if self.i == 0:
                start = datetime.datetime.now()                   

            t0 = perf_counter()

            # Time sending the data
            try:                    
                self.sock.sendall(data)
            except socket.timeout:
                ex = IOError('timed out attempting to send data')
            else:
                ex = None
            t1 = perf_counter()
            if ex is not None:
                raise ex

            start_timestamps.append(t0)
            finish_timestamps.append(t1)
            
        self.logger.debug(f'sent {count} buffers of {self.bytes} TCP data')

        return {'start': start,
                't_tx_start': start_timestamps,
                't_tx_end': finish_timestamps,
                'bytes': self.bytes}

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
        raise ConnectionError(f'network interface {iface} is down')
        
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
        sender = lb.Unicode(help='the name of the network interface that will send data')
        receiver = lb.Unicode(help='the name of the network interface that will receive data')
        port = lb.Int(5555,
                      min=1,
                      help='TCP or UDP port')
        resource = lb.Unicode(help='skipd - use sender and receiver instead')        
        timeout = lb.Float(1,
                           min=1e-3,
                           help='timeout before aborting the test')
        bytes = lb.Int(4096,
                       min=0,
                       help='TCP or UDP transmit data size')
        skip = lb.Int(0, min=0,
                      help='extra buffers to send and not log before acquisition')
        tcp_nodelay = lb.Bool(True,
                              help='if True, disable Nagle\'s algorithm')
        sync_each = lb.Bool(False,
                              help='synchronize the start times of the send and receive threads for each buffer at the cost of throughput')

    def __repr__(self):
        return "{name}(sender='{sender}',receiver='{receiver}')"\
               .format(name=self.__class__.__name__,
                       sender=self.settings.sender,
                       receiver=self.settings.receiver)
               
    def connect(self):
        self.events = {'except_event': Event(),
                       'rx_ready': Event(),
                       'tx_ready': Event()}

class ClosedLoopTCPBenchmark(ClosedLoopBenchmark):
    _port_increment = 0
    
#    @lb.retry((ConnectionError,TimeoutError), 5)
    def acquire(self, count, mss=1500-40):
        if self.settings.tcp_nodelay and self.settings.bytes < mss:
            raise ValueError(f'with tcp_nodelay enabled, set bytes at least as large as the MSS ({mss})')

        try:
            receive_ip = get_ipv4_address(self.settings.receiver)
            send_ip = get_ipv4_address(self.settings.sender)
    
            # Parameters for the client and server
            params = dict(events=self.events,
                          receive_ip=receive_ip,
                          send_ip=send_ip,
                          logger=self.logger,
                          settings=self.settings)        
    
            receiver = ReceiveTCPWorker(**params)
            sender = SendTCPWorker(**params, suppress=True)
    
            receiver.port += self.__class__._port_increment
            sender.port += self.__class__._port_increment
            
            ret = lb.concurrently(lb.Call(sender.run, count+1),
                                  lb.Call(receiver.run, count+1),
                                  traceback_delay=True)
            
            self.logger.debug('done, cleaning up')
            
            start = ret.pop('start', None)
            if start is None:
                print(start)
                raise IOError('the run did not return data')
    
            ret = pd.DataFrame(ret)
            timestamp = pd.TimedeltaIndex(ret.t_tx_start, unit='s')+start
    
            duration = ret.t_rx_end.iloc[:-1]-ret.t_rx_start.iloc[:-1]
            ret = pd.DataFrame({'bits_per_second': 8*ret.bytes.iloc[0]/duration,
                                'duration': duration,
                                'start_offset': ret.t_rx_start.iloc[:-1]-ret.t_tx_start.iloc[:-1],
                                'timestamp': timestamp[:-1]})
        finally:
            self.__class__._port_increment += 1
        
        return ret.set_index('timestamp')
    
    def wait(self, timeout):
        receive_ip = get_ipv4_address(self.settings.receiver)
        send_ip = get_ipv4_address(self.settings.sender)

        # Parameters for the client and server
        params = dict(events=self.events,
                      receive_ip=receive_ip,
                      send_ip=send_ip,
                      logger=self.logger,
                      settings=self.settings)        
        
        t0 = time.perf_counter()
        while time.perf_counter()-t0 <= timeout:
            try:
                receiver = ReceiveTCPWorker(**params)
                sender = SendTCPWorker(**params, suppress=True)

                receiver.port += self.__class__._port_increment
                sender.port += self.__class__._port_increment
                self.__class__._port_increment += 1
                
                lb.concurrently(sender.connection_check,
                                receiver.connection_check,
                                traceback_delay=True)
            except (TimeoutError, ConnectionError):
                continue
            else:
                break               

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

    net = ClosedLoopTCPBenchmark(sender='WLAN_AP_DUT',
                                  receiver='WLAN_Client_DUT',
                                  port=5568,
                                  bytes=1460*10,
                                  tcp_nodelay=True,
                                  sync_each=False)
    with net:
        for j in range(3):
            traffic = net.acquire(50)
#            pylab.figure()
#            traffic.hist(bins=51)            
    #        traffic[['duration','delay']].plot(marker='.', lw=0)
            traffic['rate'] = net.settings.bytes/traffic.duration*8/1e6
            print(f'{traffic.rate.median()} +/- {2*traffic.rate.std()} Mbps')
#            print('medians\n',traffic.median(axis=0))

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
