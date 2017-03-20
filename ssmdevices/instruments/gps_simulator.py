# -*- coding: utf-8 -*-

""" GPS simulator control classes

:author: Duncan McGillivray <duncan.mcgillivray@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
"""

__all__ = ['SpirentGSS8000']

import time,re
import labbench as lb
import traitlets as tl

import logging
logger = logging.getLogger('labbench')

status_messages=['no scenario',
                 'loading',
                 'ready',
                 'arming',
                 'armed',
                 'running',
                 'paused',
                 'ended']

class SpirentGSS8000(lb.SerialDevice):   
    ''' Control a Spirent GPS GSS8000 simulator over a serial connection.
    
        Responses from the Spirent seem to be incompatible with
        pyvisa, so this driver uses plain serial.
    '''

    class state(lb.SerialDevice.state):
        status           = lb.EnumBytes(read_only=True, values=status_messages)
        'UTC time of the current running scenario.'

        current_scenario = lb.Bytes    (command='SC_NAME,includepath', read_only=True)
        gps_week         = lb.Int      (command='-,ZCNT_TOW', read_only=True)
        running          = lb.Bool     (read_only=True)
        utc_time         = lb.Bytes    (read_only=True)        
        
    resource='COM17'
    'serial port resource name (COMnn in windows or /dev/xxxx in unix/Linux)'
    
#    connection_settings = dict(baud_rate=9600)
#
                     
    def command_get (self, attr):        
        # Alternatively, check to see if there is an command
        command = self.state.trait_metadata(attr, 'command')
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
        self.backend.write('SAVE_SCENARIO,with_changes,as_simgen,%s/\n'%(writepath))
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
        logger.debug('\nGPS SIMULATOR SEND\n{}'.format(repr(command)))        
        self.backend.write('{}\n'.format(command))
        
        # Get the response
        response = ''
        while '</msg>' not in response.lower():
            response += self.backend.readline()
        logger.debug('\nGPS SIMULATOR RECEIVE\n{}'.format(repr(response)))
        self.backend.read(self.backend.inWaiting()) # Clear out any remaining data
        
        # Pull the data/error message payload
        data = re.match('.*<data>[\W*]*(.*)[\W*]</data>.*',response,flags=re.S)
        if returns.lower() == 'value' or returns == None:
            raise Exception(data.group(1))

        if returns.lower() == 'status':            
            status = int(re.match('.*<status>[\W*]*(\d+)[\W*]</status>.*',response,flags=re.S).group(1))
            return status_messages[status]
        elif returns.lower() == 'value':
            return data.group(1)
        elif returns == None:
            return
        else:
            raise Exception("Expected return type in ['value', 'status', None], but got {}".format(repr(returns)))

    def query (self, command):
        return self.write(command+'\n', returns=True)
    
    def run(self):
        ''' Start running the current scenario. Requires that there is time left in
            the scenario, otherwise run `rewind()` first.
        '''
        self.write('RU')

    def end(self):
        ''' Stop running the current scenario. If a scenario is not
            running, an exception is raised.
        '''
        self.write('-,EN')

    def rewind(self):
        ''' Rewind the current scenario to the beginning.
        '''
        self.write('RW')
           
    def abort(self):
        ''' Force stop the current scenario.
        '''        
        self.write('-,EN,1,0')
            
    def reset(self):
        ''' End any currently running scenario, then rewind
        '''
        try:
            if self.get_status() != 'ended':
                self.end()
        except:
            pass
        self.rewind()

    @state.utc_time.getter
    def _ (self):
        utc_unformatted = self.query('-,UTC_TIME')
        try:
            utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S.%f')
            frac = utc_unformatted.split('.')[-1]
        except:
            utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S')
            frac = '000'
            
        return time.strftime('%Y-%m-%d %H:%M:%S', utc_struct)+'.'+frac
    
    @state.running.getter
    def _ (self):
        ''' Check whether a scenario is running.
        
            :return: True if a scenario is running, otherwise False
        '''
        return self.get_status() == 'running'
        
    @state.status.getter
    def _ (self):
        ''' Get current instrument status.
        '''
        return self.write('NULL', return_status=True)
        
#%%
if __name__ == '__main__':
    lb.debug_to_screen('DEBUG')
    with SpirentGSS8000('COM14') as spirent:
        spirent.reset()
        spirent.run()
        scn = spirent.state.current_scenario
        utc = spirent.state.utc_time

    print scn
    print utc