# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""

from remotelets import *
import pandas as pd

__all__ = ['KeysightU2040XSeries']

class KeysightU2040XSeries(VISAInstrument):
    ''' This is my cool driver for Keysight U2040 X-Series power sensors
    '''
    connection_settings     = {'read_termination':  '\n',
                               'write_termination': '\n'}

    initiate_continuous     = SCPI(Bool(),                                         'INIT:CONT')    
    output_trigger          = SCPI(Bool(),                                         'OUTP:TRIG')
    trigger_source          = SCPI(EnumBytes(['IMM','INT','EXT','BUS','INT1']),    'TRIG:SOUR')
    trigger_count           = SCPI(Int(min=1,max=200,step=1,help="help me"),       'TRIG:COUN')
    measurement_rate        = SCPI(EnumBytes(['NORM','DOUB','FAST']),              'SENS:MRAT')
    sweep_aperture          = SCPI(Float(min=20e-6, max=200e-3,label='s'),         'SWE:APER')
    frequency               = SCPI(Float(min=10e6, max=18e9,step=1e-3,label='Hz'), 'SENS:FREQ')
    
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