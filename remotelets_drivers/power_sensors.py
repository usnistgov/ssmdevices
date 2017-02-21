# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""

import remotelets as rlts
from remotelets import *
import pandas as pd
import pyvisa

__all__ = ['KeysightU2040XSeries']

class KeysightU2040XSeries(rlts.VISAInstrument):
    ''' This is my cool driver for Keysight U2040 X-Series power sensors
    
        We have calibration data here:
            
            \\jake\bla\ajlsdjfalsdjf\Calibrations\cooldata.dat
    '''
    initiate_continuous     = rlts.SCPI(rlts.Bool(),                               'INIT:CONT')    
    output_trigger          = rlts.SCPI(rlts.Bool(),                                         'OUTP:TRIG')
    trigger_source          = rlts.SCPI(rlts.EnumBytes(['IMM','INT','EXT','BUS','INT1']),   'TRIG:SOUR')
    trigger_count           = rlts.SCPI(rlts.Int(min=1,max=200,step=1,help="help me"),      'TRIG:COUN')
    measurement_rate        = rlts.SCPI(rlts.EnumBytes(['NORM','DOUB','FAST']),             'SENS:MRAT')
    sweep_aperture          = rlts.SCPI(rlts.Float(min=20e-6, max=200e-3,label='s'),        'SWE:APER')
    frequency               = rlts.SCPI(rlts.Float(min=10e6, max=18e9,step=1e-3,label='Hz'),'SENS:FREQ')

    def preset (self, block=True):
        if block:
            self.link.write('SYST:PRES;*OPC')
            self.link.query('*OPC?')
        else:
            self.link.write('SYST:PRES')

    def fetch (self):
        ''' Return a single number or pandas Series containing the power readings
        '''
        response = self.link.query('FETC?')
        return pd.Series([float(s) for s in response.split(',')])

if __name__ == '__main__':
    from pylab import *
    import seaborn as sns
    sns.set(style='ticks')

    # Enable pyvisa debug messages
    # pyvisa.log_to_screen()

    with KeysightU2040XSeries('USB0::0x2A8D::0x1E01::SG56360004::INSTR') as sensor:
        print 'Connected to ', sensor.identity

        # Configure
        sensor.preset()
        sensor.frequency           = 1e9
        sensor.measurement_rate    = 'FAST'
        sensor.trigger_count       = 200
        sensor.sweep_aperture      = 20e-6
        sensor.trigger_source      = 'IMM'
        sensor.initiate_continuous = True

        power = sensor.fetch()

    power.hist(figsize=(6,2)); xlabel('Power level'); ylabel('Count'); title('Histogram of power sensor readings')