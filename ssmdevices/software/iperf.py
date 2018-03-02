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
__all__ = ['IPerfClient','IPerf']

import pandas as pd
import labbench as lb
import os,ssmdevices.lib
from io import StringIO

class IPerf(lb.CommandLineWrapper):
    ''' Run an instance of iperf, collecting output data in a background thread.
        When running as an iperf client (server=False), 
        The default value is the path that installs with 64-bit cygwin.
    '''
    resource = '127.0.0.1'

    binary_path = os.path.join(ssmdevices.lib.__path__[0], 'loop.bat')
    iperf_path = os.path.join(ssmdevices.lib.__path__[0], 'iperf.exe')

    class state(lb.CommandLineWrapper.state):
        server        = lb.LocalBool(False, help='True to run as server; False to run as client. If True, resource is ignored.')
        timeout       = lb.LocalFloat(6, min=0, help='wait time for traffic results before throwing a timeout exception (s)')
        port          = lb.LocalInt(5001, help='connection port')
        bind          = lb.LocalUnicode(help='bind connection to specified IP')
        tcp_window_size = lb.LocalInt(8192, min=1, help='(bytes)')
        buffer_size   = lb.LocalInt(1024, min=1, help='Size of data buffer that generates traffic (bytes)')
        interval      = lb.LocalFloat(0.5, min=0.01, help='Interval between throughput reports (s)')
        bidirectional = lb.LocalBool(False, help='Send and receive simultaneously')
        udp           = lb.LocalBool(False, help='UDP instead of TCP networking')
        bit_rate      = lb.LocalInt(0, min=0, help='Maximum bit rate (bps)')
        restart_on_state_change\
                      = lb.LocalBool(True, is_metadata=True, read_only='connected',
                                    help='Whether to terminate restart the command line executable if a state changes while running')


    def fetch (self):
        result = super(IPerf,self).fetch()

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

    def setup (self):
        # Call the iperf binary
        cmd = self.iperf_path,'-n','-1','-y','C'
              
        if self.state.server:
            cmd = cmd + ('-s',)
        else:
            cmd = cmd + ('-c', str(self.resource))

        cmd = cmd + ('-p',str(self.state.port))
        if self.state.bind:
            cmd = cmd + ('-B',str(self.state.bind))
        if self.state.bidirectional:
            cmd = cmd + ('-d',)
        if self.state.udp:
            cmd = cmd + ('-u',)
        else:
            # TCP-only options?
            cmd = cmd + ('-l',str(self.state.buffer_size))
        if self.state.bit_rate > 0:
            cmd = cmd + ('-b', '{}k'.format(self.state.bit_rate//1024))

        cmd = cmd + ('-w',str(self.state.tcp_window_size))
        cmd = cmd + ('-i',str(self.state.interval))
        
        self.cmd = cmd

    def start(self):
        self.execute(self.cmd)


class IPerfClient(IPerf):
    ''' This class is deprected. Use IPerf instead
    '''
    
    def __init__ (self, *args, **kws):
        self.logger.warning('this class is deprecated; use IPerf instead')
        super(IPerfClient, self).__init__(*args, **kws)

if __name__ == '__main__':
    import time
    
    ipc = IPerf('10.0.0.3',interval=0.25)
    ipc.iperf_path = r'..\lib\iperf.exe'
    
    with ipc:
        ipc.clear()
        while True:
            print(ipc.fetch())
            time.sleep(3)