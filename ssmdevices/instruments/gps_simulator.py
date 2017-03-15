# -*- coding: utf-8 -*-

""" GPS simulator control classes

:author: Duncan McGillivray <duncan.mcgillivray@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
"""

import time,re
import labbench as lb
import traitlets as tl

import logging
logger = logging.getLogger('labbench')

class AutoMessage(object):
    def __new__ (cls, trait_type, command=None):
        return trait_type.tag(command=command)

class SpirentGSS8000(lb.SerialDevice):   
    ''' Control a Spirent GPS GSS8000 simulator over a serial connection.
    
        Responses from the Spirent seem to be incompatible with
        pyvisa, so this driver uses plain serial.
    '''

    class state(lb.SerialDevice.state):
        status           = tl.Bytes()
        current_scenario = AutoMessage(lb.Bytes(read_only=True), 'SC_NAME,includepath')
        gps_week         = AutoMessage(lb.Int(read_only=True), '-,ZCNT_TOW')
        running          = lb.Bool(read_only=True)
        utc_time         = lb.Bytes(read_only=True)
        
#        @current_scenario.getter
#        def __get_current_scenario (self, device):
#            return device.query('SC_NAME,includepath')
        
        @utc_time.getter
        def __get_utc_time(self, device):
            ''' Get the UTC time of the current running scenario.
            
                :param timeformat: 'UTC' for UTC timestamp, or 'TOW' for Time of week in seconds
            '''
            timeformat = 'utc'
            
            utc_unformatted = device.query('-,UTC_TIME')
            try:
                utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S.%f')
                frac = utc_unformatted.split('.')[-1]
            except:
                utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S')
                frac = '000'
                
            return time.strftime('%Y-%m-%d %H:%M:%S', utc_struct)+'.'+frac
        
        @running.getter
        def __get_running(self, device):
            ''' Check whether a scenario is running.
            
                :return: True if a scenario is running, otherwise False
            '''
            return device.get_status() == 'running'
        
        
    resource='COM17'
    'serial port resource name (COMnn in windows or /dev/xxxx in unix/Linux)'
    
#    connection_settings = dict(baud_rate=9600)
#
    status_messages=['no scenario',
                     'loading',
                     'ready',
                     'arming',
                     'armed',
                     'running',
                     'paused',
                     'ended']
                     
    def state_get (self, attr):        
        # Alternatively, check to see if there is an command
        command = self.state.trait_metadata(attr, 'command')
        if command is not None:
            return self.query(command)
            
    'Status messages that may be received from the instrument'

    def load_scenario(self,path):
        ''' Load a GPS scenario from a file stored on the instrument.
        
            :param path: Full path to scenario file on the instrument.
            
        '''
        #write scenario path as 'c:\folder\folder\name.scn'
        loadpath = self.fix_path_name(path)
        self.link.read(self.link.inWaiting())
        self.link.write('SC,%s\n'%(loadpath))
        self.state.current_scenario

    def save_scenario(self, folderpath):
        ''' Save the current GPS scenario to a file stored on the instrument.
        
            :param path: Full path to scenario file on the instrument.
            
        '''
        
        # write folderpath as 'c:\folder\folder'
        writepath=self.fix_path_name(folderpath)

        self.link.read(self.link.inWaiting())
        self.link.write('SAVE_SCENARIO,with_changes,as_simgen,%s/\n'%(writepath))
        self.state.current_scenario
        
    @staticmethod
    def fix_path_name (path):
        return path.replace('\\','/')

    def write (self, command, returns=False):
        ''' Send a message to the spirent, and check the status message
            returned by the spirent.
            
            :return: returned status code (possible codes listed in `self.status_messages`)
        '''
        self.link.read(self.link.inWaiting())        
        logger.debug('\nGPS SIMULATOR SEND\n{}'.format(repr(command)))        
        self.link.write('{}\n'.format(command))
        
        response = ''
        while '</msg>' not in response.lower():
            response += self.link.readline()
        logger.debug('\nGPS SIMULATOR RECEIVE\n{}'.format(repr(response)))

        status_code = int(re.match('.*<status>[\W*]*(\d+)[\W*]</status>.*',response,flags=re.S).group(1))
        self.state.status = self.status_messages[status_code]
        
        returncheck = re.match('.*<data>[\W*]*(.*)[\W*]</data>.*',response,flags=re.S)
        self.link.read(self.link.inWaiting())
        if not returns:
            if returncheck is not None:
                raise Exception(returncheck.group(1))
        else:
            return returncheck.group(1)

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

    def get_status(self):
        ''' Get current instrument status.
        '''
        print self.write('NULL')
        return self.state.status
            
    def reset(self):
        ''' End any currently running scenario, then rewind
        '''
        try:
            if self.get_status() != 'ended':
                self.end()
        except:
            pass
        self.rewind()
        
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