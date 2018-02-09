# -*- coding: utf-8 -*-

""" GPS simulator control classes

:author: Duncan McGillivray <duncan.mcgillivray@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from builtins import int
from future import standard_library
standard_library.install_aliases()
__all__ = ['SpirentGSS8000']

import time,re
import labbench as lb
import traitlets as tl

status_messages=[b'no scenario',
                 b'loading',
                 b'ready',
                 b'arming',
                 b'armed',
                 b'running',
                 b'paused',
                 b'ended']

class SpirentGSS8000(lb.SerialDevice):   
    ''' Control a Spirent GPS GSS8000 simulator over a serial connection.
    
        Responses from the Spirent seem to be incompatible with
        pyvisa, so this driver uses plain serial.
    '''

    class state(lb.SerialDevice.state):
        status           = lb.CaselessBytesEnum(read_only=True, values=status_messages)
        'UTC time of the current running scenario.'

        current_scenario = lb.Bytes    (command=b'SC_NAME,includepath', read_only=True, is_metadata=True)
        gps_week         = lb.Int      (command='-,ZCNT_TOW', read_only=True)
        running          = lb.Bool     (read_only=True)
        utc_time         = lb.Bytes    (read_only=True)        
        
    resource='COM17'
    'serial port resource name (COMnn in windows or /dev/xxxx in unix/Linux)'
    
#    connection_settings = dict(baud_rate=9600)
#
                     
    def command_get (self, command, trait):        
        return self.query(command)
            
    'Status messages that may be received from the instrument'

    def load_scenario(self,path):
        ''' Load a GPS scenario from a file stored on the instrument.
        
            :param path: Full path to scenario file on the instrument.
            
        '''
        #write scenario path as 'c:\folder\folder\name.scn'
        loadpath = self.fix_path_name(path)
        self.backend.read(self.backend.inWaiting())
        self.backend.write('SC,%s\n'%(loadpath))
        self.state.current_scenario

    def save_scenario(self, folderpath):
        ''' Save the current GPS scenario to a file stored on the instrument.
        
            :param path: Full path to scenario file on the instrument.
            
        '''
        
        # write folderpath as 'c:\folder\folder'
        writepath=self.fix_path_name(folderpath)

        self.backend.read(self.backend.inWaiting())
        self.backend.write(b'SAVE_SCENARIO,with_changes,as_simgen,%s/\n'%(writepath))
        self.state.current_scenario

    @staticmethod
    def fix_path_name (path):
        return path.replace('\\','/')

    def write (self, command, returns=None):
        ''' Send a message to the spirent, and check the status message
            returned by the spirent.
            
            :return: Either 'value' (return the data response), 'status'
                     (return the instrument status), or None (raise an
                     exception if a data value is returned)
        '''
        self.backend.read(self.backend.inWaiting())        
        self.logger.debug('write {}'.format(repr(command)))
        self.backend.write('{}\n'.format(command))
        
        # Get the response
        response = b''
        while b'</msg>' not in response.lower():
            response += self.backend.readline()
        self.logger.debug(b'  <- {}'.format(repr(response)))
        self.backend.read(self.backend.inWaiting()) # Clear out any remaining data
        
        # Pull the data/error message payload
        data = re.match(b'.*<data>[\W*]*(.*)[\W*]</data>.*',response,flags=re.S)
        
        
        if returns is None:
            if data is not None:
                raise Exception(data.group(1))
            return
        elif returns.lower() == b'value':
            return data.group(1)        
        if returns.lower() == b'status':
            status = int(re.match(b'.*<status>[\W*]*(\d+)[\W*]</status>.*',response,flags=re.S).group(1))
            return status_messages[status]
        else:
            raise Exception("Expected return type in ['value', 'status', None], but got {}".format(repr(returns)))

    def query (self, command):
        return self.write(command+'\n', returns='value')
    
    def run(self):
        ''' Start running the current scenario. Requires that there is time left in
            the scenario, otherwise run `rewind()` first.
        '''
        self.write(b'RU')

    def end(self):
        ''' Stop running the current scenario. If a scenario is not
            running, an exception is raised.
        '''
        self.write(b'-,EN')

    def rewind(self):
        ''' Rewind the current scenario to the beginning.
        '''
        self.write(b'RW')
           
    def abort(self):
        ''' Force stop the current scenario.
        '''        
        self.write(b'-,EN,1,0')
            
    def reset(self):
        ''' End any currently running scenario, then rewind
        '''
        if self.state.status != b'ended':
            try:            
                self.end()
            except:
                pass

        self.rewind()

    @state.utc_time.getter
    def _ (self):
        utc_unformatted = self.query(b'-,UTC_TIME')
        try:
            utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S.%f')
            frac = utc_unformatted.split('.')[-1]
        except:
            utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S')
            frac = b'000'
            
        return time.strftime('%Y-%m-%d %H:%M:%S', utc_struct)+'.'+frac
    
    @state.running.getter
    def _ (self):
        ''' Check whether a scenario is running.
        
            :return: True if a scenario is running, otherwise False
        '''
        return self.state.status == b'running'
        
    @state.status.getter
    def _ (self):
        ''' Get current instrument status.
        '''
        return self.write(b'NULL', returns=b'status')
        
#%%
if __name__ == '__main__':
    lb.debug_to_screen('DEBUG')
    with SpirentGSS8000('COM17') as spirent:
        print(spirent.state.status)
        spirent.reset()
        spirent.run()
        scn = spirent.state.current_scenario
        utc = spirent.state.utc_time

    print(scn)
    print(utc)