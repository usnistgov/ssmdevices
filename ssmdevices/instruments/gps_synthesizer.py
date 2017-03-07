# -*- coding: utf-8 -*-

""" GPS simulator control classes

:author: Duncan McGillivray <duncan.mcgillivray@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
"""

import time,re
import labbench as lb

import logging
logger = logging.getLogger('labbench')

class SpirentGSS8000(lb.SerialDevice):   
    ''' Control a Spirent GPS GSS8000 simulator over a serial connection.
    
        Responses from the Spirent seem to be incompatible with
        pyvisa, so this driver uses plain serial.
    '''

    class state(lb.SerialDevice.state):
        current_scenario = lb.Bytes(read_only=True)
        running          = lb.Bool(read_only=True)
        utc_time         = lb.Bytes(read_only=True)
        
        @current_scenario.getter
        def __get_current_scenario (self, device):
            ret = int(device.write('SC_NAME,includepath\n'))
            return ret[1::2][2][8:-9]
        
        @utc_time.getter
        def __get_utc_time(self, device):
            ''' Get the UTC time of the current running scenario.
            
                :param timeformat: 'UTC' for UTC timestamp, or 'TOW' for Time of week in seconds
            '''
            timeformat = 'utc'
            
            device.inst.read(self.inst.inWaiting())
            resp=[]
            if timeformat=='TOW':
                timecmd='ZCNT_TOW'
            else:
                timecmd='UTC_TIME'
            device.link.write('-,%s\n'%(timecmd))
    
            for m in range(0,4):
                resp+=[m,device.inst.readline()]
                
            utc_unformatted=resp[1::2][2][8:-9]
            
            try:
                utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S.%f')
            except:
                utc_struct = time.strptime(utc_unformatted, '%d-%b-%Y %H:%M:%S')
            return time.strftime('%Y-%m-%d %H:%M:%S', utc_struct)
        
        @running.getter
        def __get_running(self, device):
            ''' Check whether a scenario is running.
            
                :return: True if a scenario is running, otherwise False
            '''
            return device.get_status() == 'running'
        
        
    resource='COM17'
    'serial port resource name (COMnn in windows or /dev/xxxx in unix/Linux)'
    
    connection_settings = lb.SerialDevice.update(baudrate=9600)

    status_messages=['no scenario',
                     'loading',
                     'ready',
                     'arming',
                     'armed',
                     'running',
                     'paused',
                     'ended']    
    'Status messages that may be received from the instrument'

    def load_scenario(self,path):
        ''' Load a GPS scenario from a file stored on the instrument.
        
            :param path: Full path to scenario file on the instrument.
            
        '''
        #write scenario path as 'c:\folder\folder\name.scn'
        loadpath = self.fix_path_name(path)
        self.inst.read(self.inst.inWaiting())
        self.link.write('SC,%s\n'%(loadpath))
        self.state.current_scenario

    def save_scenario(self, folderpath):
        ''' Save the current GPS scenario to a file stored on the instrument.
        
            :param path: Full path to scenario file on the instrument.
            
        '''
        
        # write folderpath as 'c:\folder\folder'
        writepath=self.fix_path_name(folderpath)

        self.inst.read(self.inst.inWaiting())
        self.link.write('SAVE_SCENARIO,with_changes,as_simgen,%s/\n'%(writepath))
        self.state.current_scenario
        
    @staticmethod
    def fix_path_name (path):
        return path.replace('\\','/')

    def write (self, command):
        ''' Send a message to the spirent, and check the status message
            returned by the spirent.
            
            :return: returned status code (possible codes listed in `self.status_messages`)
        '''
        self.inst.read(self.inst.inWaiting())        
        logger.debug('\nGPS SIMULATOR SEND\n{}'.format(repr(command)))        
        self.link.write('{}\n'.format(command))
        
        response = ''
        while '</msg>' not in response.lower():
            response += self.inst.readline()
        logger.debug('\nGPS SIMULATOR RECEIVE\n{}'.format(repr(response)))

        status_code = int(re.match('.*<status>[\W*]*(\d+)[\W*]</status>.*',response,flags=re.S).group(1))
        returncheck = re.match('.*<data>[\W*]*(.*)[\W*]</data>.*',response,flags=re.S)
        if returncheck is not None:
            raise Exception(returncheck.group(1))
        self.inst.read(self.inst.inWaiting())
        return self.status_messages[status_code]
    
    def run(self):
        ''' Start running the current scenario. Requires that there is time left in
            the scenario, otherwise run `rewind()` first.
        '''
        return self.write('RU')

    def end(self):
        ''' Stop running the current scenario. If a scenario is not
            running, an exception is raised.
        '''
        return self.write('-,EN')

    def rewind(self):
        ''' Rewind the current scenario to the beginning.
        '''
        return self.write('RW')
        
    def abort(self):
        ''' Force stop the current scenario.
        '''        
        return self.write('-,EN,1,0')

    def get_status(self):
        ''' Get current instrument status.
        '''
        return self.write('NULL')
            
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
    spirent = SpirentGSS8000()
    spirent.connect()

#    try:
#        spirent.rewind()
#        spirent.run()
#        spirent.utc_time
#
#    finally:
#        spirent.close()
#    time.sleep(0.1)
    #    spirent.run()
    
    #    starttime=datetime.timedelta(hours=1,minutes=40,seconds=1)
    #    endtime=datetime.timedelta(seconds=65)+starttime
    #    print endtime    
    #    spirent.TimedEnd(str(endtime))
    #    [bb,cc]=spirent.poll_time('UTC')
    #    time.sleep(1)
#        spirent.run()
#        utc_time = spirent.utc_time
#        print utc_time
#    finally:
##        spirent.close()
#        pass