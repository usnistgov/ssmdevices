# -*- coding: utf-8 -*-
"""
@author: Dan Kuester <daniel.kuester@nist.gov>,
         Michael Voecks <michael.voecks@nist.gov>
"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()

from builtins import super
from builtins import str

__all__ = ['IPerfClient','IPerf','IPerfOnAndroid', 'IPerfBoundPair',
           'ClosedLoopNetworkingTest']

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
    def __init__ (self, profiler, tx_exception, tx_ready, rx_ready):
        self.bytes = profiler.settings.bytes
        self.skip = profiler.settings.skip
        self.receiver = profiler.settings.receiver
        self.sender = profiler.settings.sender
        self.udp = profiler.settings.udp
        self.port = profiler.settings.port
        self.timeout = profiler.settings.timeout
        self.tcp_nodelay = profiler.settings.tcp_nodelay
        self.logger = profiler.logger
        
        self.i = 0
        self.sock = None
        self.tx_exception = tx_exception
        self.tx_ready = tx_ready
        self.rx_ready = rx_ready
        self.sent = {}
        self.bad_data = []        
        
    def __call__ (self, count):
        ret = {}
        try:
            if self.udp:
                ret = self._udp(count)
            else:
                ret = self._tcp(count)
        except lb.ThreadEndedByMaster:
            self.logger.warning(f'{self.__class__.__name__}() ended by master thread')
            self.tx_exception.set()
        except socket.timeout as e:
            self.logger.warning(f'{self.__class__.__name__} socket timeout on {self.i+1}/{count}')
            self.tx_exception.set()
            if self.udp:
                print(e)
            else:
                raise
        except:
            self.tx_exception.set()
            raise        
        finally:
            self.logger.debug('traffic stopped')
            self.sock.close()
            if self.udp and len(self.sent):
                self.logger.warning(f'missed {count-self.i}/{count} datagrams')     
            if self.udp and len(self.bad_data):
                self.logger.warning(f'failed to recognize {len(self.bad_data)} datagrams')            

        return ret

class ReceiveWorker(SocketWorker):
    def _open(self):
        socket_type = socket.SOCK_DGRAM if self.udp else socket.SOCK_STREAM        
        sock = socket.socket(socket.AF_INET, socket_type)
        
        # The receive buffer for this socket (under the hood in the OS)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.bytes)        
        bufsize = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        if bufsize < self.bytes:
            msg = f'recv buffer size is {bufsize}, but need at least {self.bytes}'
            raise OSError(msg)

        sock.settimeout(self.timeout)
        sock.bind((self.receiver, self.port))

        if self.udp:
            return sock
        else:
            # Make friends with the sender            
            sock.listen(1)
            conn, other_addr = sock.accept()
            if other_addr[0] != self.sender:
                raise ValueError(f'connection request from incorrect ip {other_addr[0]}')                    
            return conn

    def __call__ (self, count, sender_obj):
        self.sender_obj = sender_obj
        return super().__call__(count)        
        
    def _udp(self, count):       
        self.bad_data = []
        starts = [None]*count
        finishes = [None]*count
        received = [None]*count            
        
        with self._open() as self.sock:
            self.logger.info('connected')
            # Receive the data
            for self.i in range(self.skip+count):
                # Bail if the sender hit an exception
                if self.tx_exception.is_set():
                    raise lb.ThreadEndedByMaster()
    
                self.tx_ready.wait(timeout=self.timeout)
                self.rx_ready.set()
    
                started = perf_counter()
    
                # UDP datagrams seem to come atomically. One simple recv.
                data, addr = self.sock.recvfrom(self.bytes)
                finished = perf_counter()
    
                if self.sender != addr[0]:
                    raise Exception(f"udp sender is {addr[0]}, but expected {self.sender}")
    
                try:
                    i_sent = self.sender_obj.sent.pop(data)
#                    if i_sent != self.i:
#                        print('index mismatch: ', self.i, i_sent)
                except KeyError:
                    self.bad_data.append(data)
                    
                if self.i>=self.skip:
                    starts[i_sent-self.skip] = started
                    finishes[i_sent-self.skip] = finished
                    received[i_sent-self.skip] = data
                    
            self.logger.info('done')
                    
        error_count = [bit_errors(data) for data in received]
        
        return {'receive_start_timestamp': starts,
                'receive_finish_timestamp': finishes,
                'bit_error_count':  error_count}

    def _tcp(self, count):        
        buf = bytearray(self.bytes)            
        starts = []
        finishes = []
        received = []
        
        with self._open() as self.sock:
            # Receive the data
            for self.i in range(self.skip+count):
                lb.sleep(0)
#                print('rx ', i)
                # Bail if the sender hit an exception
                if self.tx_exception.is_set():
                    raise lb.ThreadEndedByMaster()

                started = perf_counter()

                rx_count = 0
                while rx_count < self.bytes:
                    rx_count += self.sock.recv_into(buf[rx_count:],
                                               self.bytes-rx_count)
                    if perf_counter()-started > self.timeout:
                        raise socket.timeout

                finished = perf_counter()
                data = bytes(buf.copy())

                # Throw away the first sample
                if self.i>=self.skip:
                    starts.append(started)
                    finishes.append(finished)
                    received.append(data)
                
        error_count = [bit_errors(data) for data in received]
                    
        return {'receive_start_timestamp': starts,
                'receive_finish_timestamp': finishes,
                'bit_error_count':  error_count}
        
class SendWorker(SocketWorker):
    def _open(self):
        socket_type = socket.SOCK_DGRAM if self.udp else socket.SOCK_STREAM        
        sock = socket.socket(socket.AF_INET, socket_type)
        
        # The OS-level TCP transmit buffer size for this socket.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,
                        self.bytes)
        bytes_actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        if bytes_actual != self.bytes:
            msg = f'send buffer size is {bytes_actual}, but requested {self.bytes}'
            raise OSError(msg)

        if not self.udp:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, self.tcp_nodelay)            
        sock.bind((self.sender, 0))        
        if not self.udp:
            sock.connect((self.receiver, self.port))            

        return sock
        
    def _tcp(self, count):
        # TODO: configure the type of data sent?
        timestamps = []
        start = None

        with self._open() as self.sock:
            for self.i in range(self.skip+count):
                data = np.random.bytes(self.bytes) # b'\x00'*size
                
    #                self.logger.info(f'tx {i}')
                # Leave now if the server bailed
                if self.tx_exception.is_set():
                    raise lb.ThreadEndedByMaster()                
    
                # Throw any initial samples as configured
                if self.i>=self.skip:
                    if self.i==self.skip:
                        start = datetime.datetime.now()
                    timestamps.append(perf_counter())
    
                self.sock.sendall(data)
    
                lb.sleep(0.)        

        return {'start': start,
                'send_timestamp': timestamps,
                'bytes': self.bytes}
            
    def _udp(self, count):
        timestamps = []
        start = None
        
        with self._open() as self.sock:                   
            for self.i in range(self.skip+count):
                # Generate the next data to send
                data = np.random.bytes(self.bytes) # b'\x00'*size
                self.sent[data] = self.i
                
                # Leave now if the server bailed
                if self.tx_exception.is_set():
                    raise lb.ThreadEndedByMaster()                
    
                # Throw any initial samples as configured
                if self.i>=self.skip:
                    if self.i==self.skip:
                        start = datetime.datetime.now()
                    timestamps.append(perf_counter())
    
                self.tx_ready.set()
                self.sock.sendto(data, (self.receiver, self.port))
                self.rx_ready.wait(timeout=self.timeout)
                    
                lb.sleep(0.)

        return {'start': start,
                'send_timestamp': timestamps,
                'bytes': self.bytes}


class ClosedLoopNetworkingTest(lb.Device):
    ''' Profile closed-loop UDP or TCP traffic between two network interfaces
        on the computer. Takes advantage of the shared clock to provide
        one-way traffic delay with uncertainty on the order of the system time
        resolution.
        
        WARNING: UDP does not work right yet.
    '''
    
    class settings(lb.Device.settings):
        sender = lb.Unicode(help='the ip address of the network interface to use to send data')
        receiver = lb.Unicode(help='the ip address of the network interface to use to receive data')
        port = lb.Int(5555, min=1, help='TCP or UDP port')
        resource = lb.Unicode(help='skipd - use sender and receiver instead')        
        timeout = lb.Float(1, min=1e-3, help='timeout before aborting the test')
        bytes = lb.Int(4096, min=0, help='TCP or UDP transmit data size')
        udp = lb.Bool(False, help='use UDP (True) or TCP (False)')
        skip = lb.Int(1, min=0, help='extra buffers to send and not log before acquisition')
        tcp_nodelay = lb.Bool(True, help='if True, disable Nagle\'s algorithm')
        
    def __repr__(self):
        return "{name}(sender='{sender}',receiver='{receiver}')"\
               .format(name=self.__class__.__name__,
                       sender=self.settings.sender,
                       receiver=self.settings.receiver)

   
#    @lb.retry(socket.timeout, 5)
    def acquire(self, count):
        if not self.settings.udp and self.settings.tcp_nodelay\
           and self.settings.bytes < 1500:
            raise ValueError('with tcp_nodelay enabled, set bytes larger than the MTU (1500)')

        self.sent = {}
        
        # Parameters for the client and server
        events = {'tx_exception': Event(),
                  'rx_ready': Event(),
                  'tx_ready': Event()}

        receiver = ReceiveWorker(self, **events)
        sender = SendWorker(self, **events)

        ret = lb.concurrently(lb.Call(receiver.__call__, count, sender),
                              lb.Call(sender.__call__, count))

        start = ret.pop('start')
        ret = pd.DataFrame(ret)
        dt = pd.TimedeltaIndex(ret.send_timestamp, unit='s')
        ret = pd.DataFrame({'bit_error_count': ret.bit_error_count,
                            'bytes_sent': ret.bytes,
                            'duration': ret.receive_finish_timestamp - ret.receive_start_timestamp,
                            'delay': ret.receive_start_timestamp-ret.send_timestamp,
                            'timestamp': dt+start})
        
        return ret.set_index('timestamp')

# Examples
# ClosedLoopNetworkingTest example
if __name__ == '__main__':
    import pylab
    
    with ClosedLoopNetworkingTest(sender='10.0.0.2', receiver='10.0.0.3',
                                  bytes=2*1024) as net:    
        for j in range(1):
            traffic = net.acquire(500)
            pylab.figure()
            traffic.hist(bins=51)            
    #        traffic[['duration','delay']].plot(marker='.', lw=0)
            traffic['rate'] = net.settings.bytes/traffic.duration
            print('medians\n',traffic.median(axis=0))

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
