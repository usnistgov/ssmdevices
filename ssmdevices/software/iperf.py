# -*- coding: utf-8 -*-
"""
@author: Dan Kuester <daniel.kuester@nist.gov>
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

    class state(lb.CommandLineWrapper.state):
#        client        = lb.LocalUnicode(False, help='True to run as server; False to run as client. If True, resource is ignored.')
        timeout       = lb.LocalFloat(6, min=0, help='wait time for traffic results before throwing a timeout exception (s)')
        port          = lb.LocalInt(command='-p', min=1, help='connection port')
        bind          = lb.LocalUnicode(command='-B', help='bind connection to specified IP')
        tcp_window_size = lb.LocalInt(command='-w', min=1, help='(bytes)')
        buffer_size   = lb.LocalInt(command='-l', min=1, help='Size of data buffer that generates traffic (bytes)')
        interval      = lb.LocalFloat(0.25, command='-i', min=0.01, help='Interval between throughput reports (s)')
        bidirectional = lb.LocalBool(command='-d', help='Send and receive simultaneously')
        udp           = lb.LocalBool(False, command='-u', help='UDP instead of TCP networking')
        bit_rate      = lb.LocalUnicode(command='-b', help='Maximum bit rate (append unit for size, e.g. 10K)')
        time          = lb.LocalInt(min=0, max=16535, command='-t', help='time in seconds to transmit before quitting (default 10s)')
        arguments     = lb.LocalList([os.path.join(ssmdevices.lib.__path__[0], 'iperf.exe'),
                                      '-n','-1','-y','C'])
        binary_path   = lb.LocalUnicode(os.path.join(ssmdevices.lib.__path__[0], 'loop.bat'))

        restart_on_state_change\
                      = lb.LocalBool(True, is_metadata=True, read_only='connected',
                                    help='Whether to terminate restart the command line executable if a state changes while running')


    def fetch (self):
        ''' Retreive csv-formatted text from standard output and parse into
            a pandas DataFrame.
        '''
        result = self.read_stdout()

        columns = 'timestamp','source_address',\
                  'source_port','destination_address','destination_port',\
                  'test_id','interval','transferred_bytes','bits_per_second'

        if self.state.udp:
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
#        if len(data.index)>1:
#            data.drop(data.index[-1],inplace=True)
        if len(data)==0:
            data = data.append([None])
#        print data
        data.drop(['iperf_interval','iperf_transferred_bytes','iperf_test_id'],inplace=True,axis=1)
        data['iperf_timestamp'] = pd.to_datetime(data['iperf_timestamp'], format='%Y%m%d%H%M%S')
        data['iperf_timestamp'] = data['iperf_timestamp']+\
                                  pd.TimedeltaIndex((data.index*self.state.interval)%1,'s')

        return data
    

    def execute (self, *extra_args, **flags):
        if self.state.udp and self.state.buffer_size is not None:
            self.logger.warning('iperf might not behave nicely setting udp=True and setting buffer_size')#              

        if self.resource:
            self.logger.info('client start')
            super(IPerf, self).execute('-c', str(self.resource), *extra_args, **flags)
        else:
            self.logger.info('server start')
            super(IPerf, self).execute('-s', *extra_args, **flags)

    def start(self):
        self.execute()


class IPerfOnAndroid(IPerf):
    class state(IPerf.state):
        binary_path   = lb.LocalUnicode(os.path.join(ssmdevices.lib.__path__[0], 'adb.exe'))
        remote_binary_path = lb.LocalUnicode('/data/local/tmp/iperf', is_metadata=True)
        arguments     = lb.LocalList([])

    def execute (self, *extra, **flags):
        if self.resource:
            super(IPerf, self).execute('shell', self.state.remote_binary_path,
                                       '-c', str(self.resource),
                                       '-y','C', *extra, **flags)
        else:
            super(IPerf, self).execute('shell', self.state.remote_binary_path,
                                       *extra, **flags)

    def setup (self):
        devices = self.block_single('devices').strip().rstrip().splitlines()[1:]
        if len(devices) == 0:
            raise Exception('adb lists no devices. is the UE connected?')
        self.block_single("push",
                    os.path.join(ssmdevices.lib.__path__[0], 'android', 'iperf'),
                    self.state.remote_binary_path)
        self.block_single("shell", 'chmod', '777', self.state.remote_binary_path)
        
        # Check that it's executable
        got = self.block_single('shell', self.state.remote_binary_path, '--help')
        if got.startswith(b'/system/bin/sh'):
            raise Exception(got)

    def start (self):
        super(IPerfOnAndroid,self).start()
        test = self.read_stdout(1)        
        if 'network' in test:
            self.logger.warning('no network connectivity in UE')

    def kill (self, wait_time=3):
        # Kill the local adb process as normal
        super(IPerfOnAndroid,self).kill()
        
        # Now find and kill processes on the UE
        out = self.block_single('shell', 'ps')
        for line in out.splitlines():
            if self.state.remote_binary_path.encode() in line.lower():
                pid = line.split()[1]
                self.logger.debug('killing zombie iperf. stdout: {}'\
                                  .format(self.block_single('shell', 'kill', '-9', pid)))
        
        # Wait for any iperf zombie processes to die
        t0 = time.time()
        while time.time()-t0 < wait_time and wait_time != 0:
            out = self.block_single('shell', 'ps').lower()
            if b'iperf' not in out:
                break
            time.sleep(.25)
        else:
            raise TimeoutError('timeout waiting for iperf process termination on UE')
            
    def read_stdout(self, n=0):
        ''' adb seems to forward stderr as stdout. Filter out some resulting
            undesired status messages.
        '''
        txt = super(IPerfOnAndroid, self).read_stdout(n)
        lines = txt.splitlines()
        out = []
        for l in lines:
            if ':' not in l:
                out.append(l)
            else:
                self.logger.warning('iperf message: {}'.format(repr(l)))
        return '\n'.join(out)
    
    def fetch(self):
        return self.read_stdout()


class IPerfClient(IPerf):
    ''' This class is deprected. Use IPerf instead
    '''
    
    def __init__ (self, *args, **kws):
        self.logger.warning('this class is deprecated! use {} instead'\
                            .format(repr(IPerf)))
        super(IPerfClient, self).__init__(*args, **kws)


if __name__ == '__main__':
    import time
    
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
            ips_result = ips.fetch()
            ipc_result = ipc.read_stdout()
