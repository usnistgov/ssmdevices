# -*- coding: utf-8 -*-
"""
@author: Dan Kuester <daniel.kuester@nist.gov>, Michael Voecks <michael.voecks@nist.gov>
"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()

from builtins import super
from builtins import str
__all__ = ['IPerfClient','IPerf','IPerfOnAndroid', 'IPerfBoundPair']

import pandas as pd
import labbench as lb
import os,ssmdevices.lib,time
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

if __name__ == '__main__':
    lb.show_messages('debug')
    ips = IPerf(interval=0.5, udp=True)

    ipc = IPerf('127.0.0.1',interval=1, time=10000, udp=True, bit_rate='1M')
#    ipc.iperf_path = r'..\lib\iperf.exe'

    with ipc,ips:
        for i in range(1):
            ips.start()
            lb.sleep(1)
            ipc.start()
            lb.sleep(20)
            ipc.kill()
            ips.kill()
            ips_result = ips.read_stdout()
            ipc_result = ipc.read_stdout()
