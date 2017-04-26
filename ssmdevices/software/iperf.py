# -*- coding: utf-8 -*-
__all__ = ['IPerfClient']

import subprocess as sp
import pandas as pd
import labbench as lb
import traitlets as tl
import os
import ssmdevices.lib 
import threading,datetime

class IPerfClient(lb.Device):
    ''' Run an IPerfClient. Set the resource to the location of iperf.
        The default value is the path that installs with 64-bit cygwin.
    '''
    resource = os.path.join(ssmdevices.lib.__path__[0], 'iperf.exe')
    _stop_event = None
    
    class state(lb.Device.state):
        interval = tl.CFloat(1,min=.5)
        duration = tl.CFloat(1,min=.5)
    
    def connect (self):
        if not os.path.exists(self.resource):
            raise OSError('iperf does not exist at supplied resource (path {})'\
                          .format(self.resource))
        # Quick dummy run to sanity check connectivity
#        self.acquire(.5,.5)
        
    def disconnect (self):
        if self.running():
            self.stop()
            
    def running (self):
        return self._stop_event is not None

    def acquire (self, server, interval=None, duration=None):
        if interval is None:
            interval = self.state.interval
        if duration is None:
            duration = self.state.duration
        if self._stop_event is not None:
            assert isinstance(self._stop_event, threading._Event)

        # Call the iperf binary
        cmd = self.resource,'-i',str(interval),\
              '-t',str(duration),'-y','C',\
              '-c', str(server)
            
        si = sp.STARTUPINFO()
        si.dwFlags |= sp.STARTF_USESHOWWINDOW
        
        self._data_start = datetime.datetime.now()
        
        try:
            proc = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, startupinfo=si,
                            creationflags=sp.CREATE_NEW_PROCESS_GROUP)
            self.proc = proc
        except Exception,e:
            raise e

        if self._stop_event is not None:
            self._stop_event.wait()
            terminated = proc.poll() is None
            if terminated:
                proc.terminate()
                proc.wait()
            proc.stdout.flush()
            proc.stderr.flush()
        else:
            terminated = False

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
                  'test_id','interval','transferred_bytes','bits_per_second'

        columns = ['iperf_'+c for c in columns]
        data = pd.read_csv(proc.stdout, header=None,index_col=False,
                           names=columns)
        
        # if there is more than one data point, and execution ended 
        # naturally, then throw out the last row (a summary of the previous rows)
        if len(data.index)>1 and not terminated:
            data.drop(data.index[-1],inplace=True)
        elif len(data)==0:
            data = data.append([None])
#        print data
        data.drop(['iperf_interval','iperf_transferred_bytes','iperf_test_id'],inplace=True,axis=1)
        data['iperf_timestamp'] = pd.to_datetime(data['iperf_timestamp'], format='%Y%m%d%H%M%S')

        data['iperf_unknown_host'] = unknown_host
        data = data[data['iperf_timestamp']>self._data_start]
        data.index = range(len(data))
        return data
    
    def start (self, server, stop_event=threading.Event()):
        ''' Start an acquisition in the background.
        '''
        def run ():
            self._stop_event = stop_event
            self._result = self.acquire(server, duration=0)
            self._stop_event = None
        thread = threading.Thread(target=run)
        thread.start()
        
    def clear (self):
        if not self.running():
            raise threading.ThreadError('cannot clear buffered results - not running')
        self._data_start = datetime.datetime.now()
        
    def stop (self):
        ''' End a background run that started with a call to start(), and return
            a pandas DataFrame containing the acquisition results
        '''
        if not self.running():
            raise threading.ThreadError('cannot stop background iperf - not running')
        self._stop_event.set()
        while not hasattr(self, '_result'):
            time.sleep(.01)
        data = self._result
        del self._result
        return data

if __name__ == '__main__':
    import time
    with IPerfClient() as iperf:
        iperf.state.duration=2
        iperf.state.interval=.5
        iperf.start('672dk1')
        time.sleep(2.5)
        iperf.clear()
        time.sleep(2.5)
        data = iperf.stop()
        print data