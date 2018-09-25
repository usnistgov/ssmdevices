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
__all__ = ['IPerfClient','IPerf','IPerfOnAndroid']

import pandas as pd
import labbench as lb
import os,ssmdevices.lib,time
from io import StringIO

class IPerf(lb.CommandLineWrapper):
    ''' Run an instance of iperf, collecting output data in a background thread.
        When running as an iperf client (server=False), 
        The default value is the path that installs with 64-bit cygwin.
    '''
    resource = None

    class settings(lb.CommandLineWrapper.settings):
        binary_path   = lb.Unicode(ssmdevices.lib.path('iperf.exe'))
        timeout       = lb.Float(6, min=0, help='wait time for traffic results before throwing a timeout exception (s)')
        port          = lb.Int(5001, command='-p', min=1, help='connection port')
        bind          = lb.Unicode(None, command='-B', allow_none=True, help='bind connection to specified IP')
        tcp_window_size = lb.Int(8192, command='-w', min=1, help='(bytes)')
        buffer_size   = lb.Int(8192, command='-l', min=1, help='Size of data buffer that generates traffic (bytes)')
        interval      = lb.Float(0.25, command='-i', min=0.01, help='Interval between throughput reports (s)')
        bidirectional = lb.Bool(False, command='-d', help='Send and receive simultaneously')
        udp           = lb.Bool(False, command='-u', help='UDP instead of TCP networking')
        bit_rate      = lb.Unicode(None, allow_none=True, command='-b', help='Maximum bit rate (append unit for size, e.g. 10K)')
        time          = lb.Int(10, min=0, max=16535, command='-t', help='time in seconds to transmit before quitting (default 10s)')
        arguments     = lb.List(['-n','-1','-y','C'])

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
        open(r'C:\python code\junk.csv','wb').write(StringIO(result).read().encode())
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

        with self.respawn, self.exception_on_stderr:
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

    def setup (self):
        with self.no_state_arguments:
#            self.logger.warning('TODO: need to fix setup for android iperf, but ok for now')
#            devices = self.foreground('devices').strip().rstrip().splitlines()[1:]
#            if len(devices) == 0:
#                raise Exception('adb lists no devices. is the UE connected?')
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True,
                   timeout=30)

            time.sleep(.1)
            sp.run([self.settings.binary_path, "push", ssmdevices.lib.path('android','iperf'),
                   self.settings.remote_binary_path], check=True, timeout=2)
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=2)
            sp.run([self.settings.binary_path, "shell", 'chmod', '777',
                    self.settings.remote_binary_path], timeout=2)
            sp.run([self.settings.binary_path, 'wait-for-device'], check=True, timeout=2)
    
#            # Check that it's executable
            cp = sp.run([self.settings.binary_path, 'shell',
                         self.settings.remote_binary_path, '--help'],
                         timeout=2, stdout=sp.PIPE)
            if cp.stdout.startswith(b'/system/bin/sh'):
                raise Exception('could not execute!!! ', cp.stdout)

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
            time.sleep(.1)
            # Wait for any iperf zombie processes to die
            t0 = time.time()
            while time.time()-t0 < wait_time and wait_time != 0:
                out = self.foreground('shell', 'ps').lower()
                if b'iperf' not in out:
                    break
                time.sleep(.25)
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
            raise TimeoutError('timeout waiting for cellular data')
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
    
    def __init__ (self, *args, **kws):
        self.logger.warning('this class is deprecated! use {} instead'\
                            .format(repr(IPerf)))
        super(IPerfClient, self).__init__(*args, **kws)


if __name__ == '__main__':   
    lb.show_messages('debug')
    ips = IPerf(interval=0.5, udp=True)

    ipc = IPerfOnAndroid('10.133.0.201',interval=1, time=10000,
                         udp=True, bit_rate='1M')
#    ipc.iperf_path = r'..\lib\iperf.exe'
    
    with ipc,ips:
        for i in range(1):
            ips.start()
            time.sleep(1)
            ipc.start()
            time.sleep(20)
            ipc.kill()
            ips.kill()
            ips_result = ips.read_stdout()
            ipc_result = ipc.read_stdout()
