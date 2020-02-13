# -*- coding: utf-8 -*-

__all__ = ['KeysightU2000XSeries', 'RohdeSchwarzNRP8s', 'RohdeSchwarzNRP18s', 'RohdeSchwarzNRPSeries']

import labbench as lb


class KeysightU2000XSeries(lb.VISADevice):
    ''' This is my cool driver for Keysight U2040 X-Series power sensors
    '''

    initiate_continuous = lb.Bool(key='INIT:CONT')
    output_trigger = lb.Bool(key='OUTP:TRIG')
    trigger_source = lb.Unicode(key='TRIG:SOUR', case=False, only=('IMM', 'INT', 'EXT', 'BUS', 'INT1'))
    trigger_count = lb.Int(key='TRIG:COUN', min=1, max=200)
    measurement_rate = lb.Unicode(key='SENS:MRAT', only=('NORM', 'DOUB', 'FAST'), case=False)
    sweep_aperture = lb.Float(key='SWE:APER', min=20e-6, max=200e-3, help='time (in s)')
    frequency = lb.Float(key='SENS:FREQ', min=10e6, max=18e9, step=1e-3,
                         help='input signal center frequency (in Hz)')

    def preset(self):
        self.write('SYST:PRES')

    def fetch(self):
        ''' Return a single number or pandas Series containing the power readings
        '''
        response = self.query('FETC?').split(',')
        if len(response) == 1:
            return float(response[0])
        else:
            return pd.to_numeric(pd.Series(response))

    @classmethod
    def __imports__(cls):
        global pd
        import pandas as pd
        super().__imports__()


class RohdeSchwarzNRPSeries(lb.VISADevice):
    ''' Requires drivers from the R&S website; resource strings for connections take the form
        'RSNRP::0x00e2::103892::INSTR'.
    '''

    # Instrument state traits (pass command arguments and/or implement setter/getter)
    frequency = lb.Float(key='SENS:FREQ', min=10e6, step=1e-3, label='Hz')
    initiate_continuous = lb.Bool(key='INIT:CONT', remap={False: 'OFF', True: 'ON'})

    @lb.Unicode(key='SENS:FUNC', case=False,
                only=('POW:AVG', 'POW:BURS:AVG', 'POW:TSL:AVG', 'XTIM:POW', "XTIM:POWer"))
    def function(self, value):
        # Special case - this message requires quotes around the argument
        self.write('SENSe:FUNCtion "{}"'.format(value))

    @lb.Unicode(
        key='TRIG:SOUR', case=False, only=('HOLD', 'IMM', 'INT', 'EXT', 'EXT1', 'EXT2', 'BUS', 'INT1'))
    def trigger_source(self):
        ''''HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm'''
        # special case - the instrument returns '2' instead of 'EXT2'
        remap = {'2': 'EXT2'}
        source = self.query('TRIG:SOUR?')
        return remap.get(source, default=source)

    trigger_delay = lb.Float(key='TRIG:DELAY', min=-5, max=10)
    trigger_count = lb.Int(key='TRIG:COUN', min=1, max=8192, help="help me")
    trigger_holdoff = lb.Float(key='TRIG:HOLD', min=0, max=10)
    trigger_level = lb.Float(key='TRIG:LEV', min=1e-7, max=200e-3)

    trace_points = lb.Int(key='SENSe:TRACe:POINTs', min=1, max=8192, gettable=False)
    trace_realtime = lb.Bool(key='TRAC:REAL', remap={False: 'OFF', True: 'ON'})
    trace_time = lb.Float(key='TRAC:TIME', min=10e-6, max=3)
    trace_offset_time = lb.Float(key='TRAC:OFFS:TIME', min=-0.5, max=100)
    trace_average_count = lb.Int(key='TRAC:AVER:COUN', min=1, max=65536)
    trace_average_mode = lb.Unicode(key='TRAC:AVER:TCON', only=('MOV', 'REP'), case=False)
    trace_average_enable = lb.Bool(key='TRAC:AVER', remap={False: 'OFF', True: 'ON'})

    average_count = lb.Int(key='AVER:COUN', min=1, max=65536)
    average_auto = lb.Bool(key='AVER:COUN:AUTO', remap={False: 'OFF', True: 'ON'})
    average_enable = lb.Bool(key='AVER', remap={False: 'OFF', True: 'ON'})
    smoothing_enable = lb.Bool(key='SMO:STAT', remap={False: 'OFF', True: 'ON'}, gettable=False)

    # Local settings traits (leave command unset, and do not implement setter/getter)
    read_termination = lb.Unicode()

    def preset(self):
        self.write('*PRE')

    def trigger_single(self):
        self.write('INIT')

    def fetch(self):
        ''' Return a single number or pandas Series containing the power readings
        '''
        response = self.query('FETC?').split(',')
        if len(response) == 1:
            return float(response[0])
        else:
            index = np.arange(len(response)) * (self.trace_time / float(self.trace_points))
            return pd.to_numeric(pd.Series(response, index=index))

    def fetch_buffer(self):
        ''' Return a single number or pandas Series containing the power readings
        '''
        response = self.query('FETC:ARR?').split(',')
        if len(response) == 1:
            return float(response[0])
        else:
            index = None  # np.arange(len(response))*(self.trace_time/float(self.trace_points))
            return pd.to_numeric(pd.Series(response, index=index))

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
        self.frequency = frequency
        self.function = 'XTIM:POW'
        self.trace_points = trace_points
        self.trace_time = trace_points * sample_period
        self.trigger_level = 10 ** (trigger_level / 10.)
        self.trigger_delay = trigger_delay  # self.Ts / 2
        self.trace_realtime = True
        self.trigger_source = trigger_source  # 'EXT2'  # Signal analyzer trigger output (10kOhm impedance)
        self.initiate_continuous = False
        self.wait()

    @classmethod
    def __imports__(cls):
        global pd
        import pandas as pd
        super().__imports__()


class RohdeSchwarzNRP8s(RohdeSchwarzNRPSeries):
    frequency = lb.Float(key='SENS:FREQ', min=10e6, max=8e9, step=1e-3, label='Hz')


class RohdeSchwarzNRP18s(RohdeSchwarzNRPSeries):
    frequency = lb.Float(key='SENS:FREQ', min=10e6, max=18e9, step=1e-3, label='Hz')


if __name__ == '__main__':
    from pylab import *
    import seaborn as sns

    sns.set(style='ticks')

    # Enable labbench debug messages
    # log_to_screen()

    with KeysightU2040XSeries('USB0::0x2A8D::0x1E01::SG56360004::INSTR') as sensor:
        print('Connected to ', sensor.identity)

        # Configure
        sensor.preset()
        sensor.frequency = 1e9
        sensor.measurement_rate = 'FAST'
        sensor.trigger_count = 200
        sensor.sweep_aperture = 20e-6
        sensor.trigger_source = 'IMM'
        sensor.initiate_continuous = True

        power = sensor.fetch()

    power.hist(figsize=(6, 2));
    xlabel('Power level');
    ylabel('Count');
    title('Histogram of power sensor readings')
