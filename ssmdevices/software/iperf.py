# -*- coding: utf-8 -*-
"""
Created on Thu May 11 09:39:43 2017

@author: dkuester
"""

__all__ = ['IPerfClient']

import pandas as pd
import labbench as lb
import traitlets as tl
import os
import ssmdevices.lib 
from StringIO import StringIO

class IPerfClient(lb.CommandLineWrapper):
    ''' Run an IPerfClient. Set the resource to the location of iperf.
        The default value is the path that installs with 64-bit cygwin.
    '''
    resource = '127.0.0.1'
    port = None
    bind = None
    tcp_window_size = None
    buffer_size = 1024
    interval = 0.5
    
    binary_path = os.path.join(ssmdevices.lib.__path__[0], 'iperf.exe')
    
    class state(lb.CommandLineWrapper.state):
        timeout         = tl.CFloat(6,     min=0)

    def fetch (self):
        result = super(IPerfClient,self).fetch()

        columns = 'timestamp','source_address',\
                  'source_port','destination_address','destination_port',\
                  'test_id','interval','transferred_bytes','bits_per_second'

        columns = ['iperf_'+c for c in columns]
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
                                  pd.TimedeltaIndex((data.index*self.interval)%1,'s')
        
        return data

    def connect (self):
        loop_path = os.path.join(os.path.dirname(self.binary_path),
                                 'loop.bat')
        
        # Call the iperf binary
        cmd = loop_path,self.binary_path,\
              '-n','-1','-y','C',\
              '-c', str(self.resource)
              
        if self.port is not None:
            cmd = cmd + ('-p',str(self.port))
        if self.bind is not None:
            cmd = cmd + ('-B',str(self.bind))
        if self.tcp_window_size is not None:
            cmd = cmd + ('-w',str(self.tcp_window_size))
        if self.buffer_size is not None:
            cmd = cmd + ('-l',str(self.buffer_size))
        if self.interval is not None:
            cmd = cmd + ('-i',str(self.interval))            

#        self.state.timeout = self.state.interval*2
        
        super(IPerfClient,self).connect()
        super(IPerfClient,self).execute(cmd)

if __name__ == '__main__':
    import time
    
    ipc = IPerfClient('10.0.0.3',interval=0.25)
    ipc.binary_path = r'..\lib\iperf.exe'
    
    with ipc:
        ipc.clear()
        while True:
            print ipc.fetch()
            time.sleep(3)