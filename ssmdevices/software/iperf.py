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
import os,ssmdevices.lib
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
        bidirectional = lb.LocalBool(False, command='-d', help='Send and receive simultaneously')
        udp           = lb.LocalBool(False, command='-u', help='UDP instead of TCP networking')
        bit_rate      = lb.LocalInt(min=0, command='-b', help='Maximum bit rate (bps)')
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
    
    def single (self, *args, **flags):
        ''' Blocking execution.
        '''
        import subprocess
        flagtup = tuple()
        for k,v in flags:
            if not isinstance(k,str):
                raise ValueError('flag keys must be str')
            if not isinstance(v,str):
                raise ValueError('flag values must be str')
            flagtup = flagtup + (k,v)
        self.logger.debug('single call to {}'\
                          .format(repr(' '.join((self.state.binary_path,) + args + flagtup))))
        return subprocess.check_output((self.state.binary_path,) + args + flagtup)

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
                                       '-y','C', *extra, **flags)

    def setup (self):
        self.single("push",
                    os.path.join(ssmdevices.lib.__path__[0], 'android', 'iperf'),
                    self.state.remote_binary_path)
        self.single("shell", 'chmod', '777', self.state.remote_binary_path)
        
        # Check that it's executable
        got = self.single('shell', self.state.remote_binary_path, '--help')
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
        out = self.single('shell', 'ps')
        for line in out.splitlines():
            if self.state.remote_binary_path.encode() in line.lower():
                pid = line.split()[1]
                self.logger.debug('killing zombie iperf. stdout: {}'\
                                  .format(self.single('shell', 'kill', '-9', pid)))
        
        # Wait for any iperf zombie processes to die
        t0 = time.time()
        while time.time()-t0 < wait_time and wait_time != 0:
            out = self.single('shell', 'ps').lower()
            if b'iperf' not in out:
                break
            time.sleep(.25)
        else:
            raise TimeoutError('timeout waiting for iperf process termination on UE')

class IPerfClient(IPerf):
    ''' This class is deprected. Use IPerf instead
    '''
    
    def __init__ (self, *args, **kws):
        self.logger.warning('this class is deprecated; use IPerf instead')
        super(IPerfClient, self).__init__(*args, **kws)

if __name__ == '__main__':
    import time
    
    lb.show_messages('debug')
    ipc = IPerfOnAndroid('10.133.0.201',interval=0.5, time=10000,
                         udp=True)
#    ipc.iperf_path = r'..\lib\iperf.exe'
    
    with ipc:
        for i in range(10):
            ipc.start()
            time.sleep(3)
            print(ipc.read_stdout())
            ipc.kill()
        
