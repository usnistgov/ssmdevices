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
    resource = os.path.join(ssmdevices.lib.__path__[0], 'iperf.exe')
    
    class state(lb.CommandLineWrapper.state):
        interval = tl.CFloat(1,min=.5)
#        duration = tl.CFloat(0,min=0)

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

#        data['iperf_unknown_host'] = unknown_host
        data.index = range(len(data))
        return data
    
    def execute (self, server):
        # Call the iperf binary
        cmd = self.resource,'-i',str(self.state.interval),\
              '-t','0','-y','C',\
              '-c', str(server)
              
        self.state.timeout = self.state.interval*2
              
        super(IPerfClient,self).execute(cmd)

if __name__ == '__main__':
    import time
    
    ipc = IPerfClient()
    ipc.execute('127.0.0.1')
    time.sleep(5)
    ipc.stop()
    print ipc.fetch()