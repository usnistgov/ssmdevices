# -*- coding: utf-8 -*-
__all__ = ['IPerfClient']

import subprocess as sp
import pandas as pd
import labbench as lb
import traitlets as tl
import os
import ssmdevices.lib 

class IPerfClient(lb.Device):
    ''' Run an IPerfClient. Set the resource to the location of iperf.
        The default value is the path that installs with 64-bit cygwin.
    '''
    resource = os.path.join(ssmdevices.lib.__path__[0], 'iperf.exe')
    
    class state(lb.Device.state):
        interval = tl.CFloat(1,min=.5)
        duration = tl.CFloat(1,min=.5)
    
    def connect (self):
        if not os.path.exists(self.resource):
            raise OSError('iperf does not exist at supplied resource (path {})'\
                          .format(self.resource))
            
        # Quick dummy run to sanity check connectivity
        self.acquire(.5,.5)
        
    def disconnect (self):
        pass

    def acquire (self, server, interval=None, duration=None):
        if interval is None:
            interval = self.state.interval
        if duration is None:
            duration = self.state.duration
            
        cmd = self.resource,'-i',str(interval),\
              '-t',str(duration),'-y','C',\
              '-c', str(server)
        
        si = sp.STARTUPINFO()
        si.dwFlags |= sp.STARTF_USESHOWWINDOW
        try:
            proc = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, startupinfo=si)
        except Exception,e:
            raise e
        
        err = proc.stderr.read()
        if len(err)>0:
            if 'unknown host' in err.lower():
                unknown_host = True
            elif 'warning' in err.lower():
                print err
            else:
                raise Exception('iperf error: {}'.format(err))
        else:
            unknown_host = False

        columns = 'timestamp','source_address',\
                  'source_port','destination_address','destination_port',\
                  'interval','transferred_bytes','bits_per_second'
        
        columns = ['iperf_'+c for c in columns]
        data = pd.read_csv(proc.stdout, header=None,index_col=False,
                           names=columns)
        
        if len(data.index)>1:
            data.drop(data.index[-1],inplace=True)
        elif len(data)==0:
            data = data.append([None])
        data.drop(['iperf_timestamp','iperf_interval','iperf_transferred_bytes'],inplace=True,axis=1)

        data['iperf_unknown_host'] = unknown_host
        return data
    
if __name__ == '__main__':
    with IPerfClient() as iperf:
        iperf.state.duration=.5
        iperf.state.interval=.5
        data = iperf.acquire('672dk1')
        print data