import labbench as lb

__all__ = ['RohdeSchwarzZMBSeries']

class RohdeSchwarzZMBSeries(lb.VISADevice):
    ''' A network analyzer.
    
        Author: Audrey Puls
    '''
    class state(lb.VISADevice.state):
        initiate_continuous = lb.Bool(command='INITiate1:CONTinuous:ALL',
                                      remap={True: 'ON', False: 'OFF'},
                                      help='')
        
    def clear(self):
        self.write('*CLS')
        
    def save_trace_to_csv(self, path, trace=1):
        ''' Save the specified trace to a csv file on the instrument.
            Block until the operation is finished.
        '''
        # This with block causes the function not to return until
        # the instrument is done saving data
        with self.overlap_and_block(timeout=3):
            self.write(f"MMEM:STOR:TRAC:CHAN {trace}, '{path}'")

    def trigger(self):
        ''' Initiate a software trigger. To use this, consider setting
            `state.initiate_continuous = False` so that the instrument waits
            for this trigger before starting a sweep.
        '''
        self.write(':INITiate:IMMediate')

if __name__ == '__main__':
    from ssmdevices.instruments import MiniCircuitsRCDAT
    import time
    import numpy as np
    
    # Example: Calibration sweep of an attenuator
    #############################SETUP CONNECTIONS#####################
    atten=MiniCircuitsRCDAT('11604210008') # Set the attenuator serial number here
    na=RohdeSchwarzZMBSeries('TCPIP0::132.163.202.153::inst0::INSTR')
    
    lb.show_messages('debug')
    
    with na, atten:
        na.clear()
        na.state.initiate_continuous = False
        
        ####################SWEEP THROUGH ATTENUATION AND COLLECT DATA#################
        # Since we want to collect cal data on (uncalibrated) attenuator settings,
        # we work with atten.state.attenuation_setting instead of
        # atten.state.attenuation (which tries to apply calibration data)
        for atten.state.attenuation_setting in np.linspace(0,110,num=441):       
            # The name of the run, based on the attenuation setting
            name=str(atten.state.attenuation_setting).replace('.','pt') 
    
            na.trigger()
            time.sleep(20) # Pauses python to let the VNA finish a full sweep
            na.save_trace_to_csv(f'VA_{atten.settings.resource}_{name}.csv')
            
        # All done!
        print(r'''ATTENTION USER: This program has completed. Your data is stored
                  on the VNA under: C:\Users\Public\Documents\Rhode-Schwarz\VNA
                  This data can be transfered to another computer via USB.
               ''')