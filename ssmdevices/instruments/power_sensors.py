# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""
from __future__ import print_function

__all__ = ['KeysightU2040XSeries']

import labbench as lb
from labbench.visa import VISADevice
import pandas as pd


class KeysightU2040XSeries(VISADevice):
    ''' This is my cool driver for Keysight U2040 X-Series power sensors
    '''

    class state (VISADevice.state):
        initiate_continuous = lb.Bool      (command='INIT:CONT')
        output_trigger      = lb.Bool      (command='OUTP:TRIG')
        trigger_source      = lb.EnumBytes (command='TRIG:SOUR', values=[b'IMM',b'INT',b'EXT',b'BUS',b'INT1'])
        trigger_count       = lb.Int       (command='TRIG:COUN', min=1,max=200,step=1)
        measurement_rate    = lb.EnumBytes (command='SENS:MRAT', values=[b'NORM',b'DOUB',b'FAST'])
        sweep_aperture      = lb.Float     (command='SWE:APER',  min=20e-6, max=200e-3,help='time (in s)')
        frequency           = lb.Float     (command='SENS:FREQ', min=10e6, max=18e9,step=1e-3,help='input signal center frequency (in Hz)')

    def preset (self):
        self.write('SYST:PRES')

    def fetch (self):
        ''' Return a single number or pandas Series containing the power readings
        '''
        response = self.query('FETC?').split(',')
        if len(response)==1:
            return float(response[0])
        else:
            return pd.to_numeric(pd.Series(response))

if __name__ == '__main__':
    from pylab import *
    import seaborn as sns
    sns.set(style='ticks')

    # Enable labbench debug messages
    #log_to_screen()

    with KeysightU2040XSeries('USB0::0x2A8D::0x1E01::SG56360004::INSTR') as sensor:
        print('Connected to ', sensor.state.identity)

        # Configure
        sensor.preset()
        sensor.state.frequency           = 1e9
        sensor.state.measurement_rate    = 'FAST'
        sensor.state.trigger_count       = 200
        sensor.state.sweep_aperture      = 20e-6
        sensor.state.trigger_source      = 'IMM'
        sensor.state.initiate_continuous = True

        power = sensor.fetch()

    power.hist(figsize=(6,2)); xlabel('Power level'); ylabel('Count'); title('Histogram of power sensor readings')