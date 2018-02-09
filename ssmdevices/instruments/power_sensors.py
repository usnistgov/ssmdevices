# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from builtins import str
from future import standard_library
standard_library.install_aliases()
__all__ = ['KeysightU2000XSeries','RohdeSchwarzNRP8s','RohdeSchwarzNRP18s','RohdeSchwarzNRPSeries']

import labbench as lb
from labbench.visa import VISADevice
import pandas as pd

class KeysightU2000XSeries(VISADevice):
    ''' This is my cool driver for Keysight U2040 X-Series power sensors
    '''

    class state (VISADevice.state):
        initiate_continuous = lb.Bool      (command='INIT:CONT')
        output_trigger      = lb.Bool      (command='OUTP:TRIG')
        trigger_source      = lb.CaselessStrEnum (command='TRIG:SOUR', values=['IMM','INT','EXT','BUS','INT1'])
        trigger_count       = lb.Int       (command='TRIG:COUN', min=1,max=200,step=1)
        measurement_rate    = lb.CaselessStrEnum (command='SENS:MRAT', values=['NORM','DOUB','FAST'])
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


class RohdeSchwarzNRPSeries(VISADevice):
    ''' Requires drivers from the R&S website; resource strings for connections take the form
        'RSNRP::0x00e2::103892::INSTR'.
    '''

    class state(VISADevice.state):
        # output_trigger = lb.Bool(command='OUTP:TRIG')
        #
        # measurement_rate = lb.CaselessStrEnum(command='SENS:MRAT', values=['NORM', 'DOUB', 'FAST'])
        # sweep_aperture = lb.Float(command='SWE:APER', min=20e-6, max=200e-3, label='s')

        frequency = lb.Float(command='SENS:FREQ', min=10e6, step=1e-3, label='Hz')
        initiate_continuous = lb.Bool(command='INIT:CONT', trues=['ON'], falses=['OFF'])
        function = lb.CaselessStrEnum(command='SENS:FUNC',\
                                      values=['POW:AVG', 'POW:BURS:AVG', 'POW:TSL:AVG',
                                              'XTIM:POW', "XTIM:POWer"])

        trigger_source = lb.CaselessStrEnum(command='TRIG:SOUR', \
                                      values=['HOLD', 'IMM', 'INT', 'EXT', 'EXT1', 'EXT2', 'BUS', 'INT1'],
                                      help='HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm')
        trigger_delay = lb.Float(command='TRIG:DELAY', min=-5, max=10)
        trigger_count = lb.Int(command='TRIG:COUN', min=1, max=8192, step=1, help="help me")
        trigger_holdoff = lb.Float(command='TRIG:HOLD', min=0, max=10)
        trigger_level = lb.Float(command='TRIG:LEV', min=1e-7, max=200e-3)

        trace_points = lb.Int(command='SENSe:TRACe:POINTs', min=1, max=8192, write_only=True)
        trace_realtime = lb.Bool(command='TRAC:REAL', trues=['ON'], falses=['OFF'])
        trace_time = lb.Float(command='TRAC:TIME', min=10e-6, max=3)
        trace_offset_time = lb.Float(command='TRAC:OFFS:TIME', min=-0.5, max=100)
        trace_average_count = lb.Int(command='TRAC:AVER:COUN', min=1, max=65536)
        trace_average_mode = lb.CaselessStrEnum(command='TRAC:AVER:TCON', values=['MOV','REP'])
        trace_average_enable = lb.Bool(command='TRAC:AVER', trues=['ON'], falses=['OFF'])

        average_count = lb.Int(command='AVER:COUN', min=1, max=65536)
        average_auto = lb.Bool(command='AVER:COUN:AUTO', trues=['ON'], falses=['OFF'])
        average_enable = lb.Bool(command='AVER', trues=['ON'], falses=['OFF'])
        smoothing_enable = lb.Bool(command='SMO:STAT', trues=['ON'], falses=['OFF'], write_only=True)
        options = lb.LocalDict({}, read_only=True)

        read_termination = lb.LocalUnicode('', read_only='connected')

        # unit = lb.CaselessStrEnum(command='UNIT:POW', values=['DBM','W','DBUV']) # seems to fail
        # format = lb.CaselessStrEnum(command='FORMat:DATA', values=['REAL', 'ASCII']) # Seems to fail

    @state.function.setter
    def __ (self, value):
        self.write('SENSe:FUNCtion "{}"'.format(value))

    @state.trigger_source.getter
    def __ (self):
        remap = {'2': 'EXT2'}
        source = self.query('TRIG:SOUR?')
        return remap.get(source, default=source)

    def preset(self):
        self.write('*PRE')

    def trigger_single (self):
        self.write('INIT')

    def fetch(self):
        ''' Return a single number or pandas Series containing the power readings
        '''
        response = self.query('FETC?').split(',')
        if len(response) == 1:
            return float(response[0])
        else:
            index = np.arange(len(response))*(self.state.trace_time/float(self.state.trace_points))
            return pd.to_numeric(pd.Series(response,index=index))

    def fetch_buffer(self):
        ''' Return a single number or pandas Series containing the power readings
        '''
        response = self.query('FETC:ARR?').split(',')
        if len(response) == 1:
            return float(response[0])
        else:
            index = None#np.arange(len(response))*(self.state.trace_time/float(self.state.trace_points))
            return pd.to_numeric(pd.Series(response,index=index))

    def setup_trace(self, frequency, trace_points, sample_period, trigger_level,
                    trigger_delay, trigger_source):
        '''

        :param frequency: in Hz
        :param trace_points: number of points in the trace (perhaps as high as 5000)
        :param sample_period: in s
        :param trigger_level: in dBm
        :param trigger_delay: in s
        :param trigger_source: 'HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm'
        :return: None
        '''
        self.write('*RST')
        self.state.frequency = frequency
        self.state.function = 'XTIM:POW'
        self.state.trace_points = trace_points
        self.state.trace_time = trace_points * sample_period
        self.state.trigger_level = 10**(trigger_level / 10.)
        self.state.trigger_delay = trigger_delay#self.Ts / 2
        self.state.trace_realtime = True
        self.state.trigger_source = trigger_source#'EXT2'  # Signal analyzer trigger output (10kOhm impedance)
        self.state.initiate_continuous = False
        self.wait()


class RohdeSchwarzNRP8s(RohdeSchwarzNRPSeries):
    class state(RohdeSchwarzNRPSeries):
        frequency = lb.Float(command='SENS:FREQ', min=10e6, max=8e9, step=1e-3, label='Hz')


class RohdeSchwarzNRP18s(RohdeSchwarzNRPSeries):
    class state(RohdeSchwarzNRPSeries):
        frequency = lb.Float(command='SENS:FREQ', min=10e6, max=18e9, step=1e-3, label='Hz')


if __name__ == '__main__':
    from pylab import *
    import seaborn as sns

    sns.set(style='ticks')

    # Enable labbench debug messages
    # log_to_screen()

    with KeysightU2040XSeries('USB0::0x2A8D::0x1E01::SG56360004::INSTR') as sensor:
        print('Connected to ', sensor.state.identity)

        # Configure
        sensor.preset()
        sensor.state.frequency = 1e9
        sensor.state.measurement_rate = 'FAST'
        sensor.state.trigger_count = 200
        sensor.state.sweep_aperture = 20e-6
        sensor.state.trigger_source = 'IMM'
        sensor.state.initiate_continuous = True

        power = sensor.fetch()

    power.hist(figsize=(6, 2));
    xlabel('Power level');
    ylabel('Count');
    title('Histogram of power sensor readings')
