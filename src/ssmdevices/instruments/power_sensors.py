# -*- coding: utf-8 -*-

__all__ = [
    'KeysightU2000XSeries',
    'KeysightU2044XA',
    'RohdeSchwarzNRP8s',
    'RohdeSchwarzNRP18s',
    'PowerTrace_RohdeSchwarzNRP',
]

import labbench as lb
from labbench import paramattr as attr
import typing
import typing_extensions
import warnings
import contextlib
import time
import pyvisa

if typing.TYPE_CHECKING:
    import pandas as pd
    import numpy as np
else:
    # delayed import for speed
    pd = lb.util.lazy_import('pandas')
    np = lb.util.lazy_import('numpy')

DataFrameType: typing_extensions.TypeAlias = 'pd.DataFrame'
SeriesType: typing_extensions.TypeAlias = 'pd.Series'

class KeysightU2000XSeries(lb.VISADevice):
    """Coaxial power sensors connected by USB"""

    # used for automatic connection
    make = attr.value.str('Keysight Technologies', inherit=True)

    def open(self):
        if type(self) is KeysightU2000XSeries:
            warnings.warn(
                'the generic base class KeysightU2000XSeries will be removed from the '
                'ssmdevices.instruments namespace in a future release. instead, use '
                'a specific model, such as KeysightU2044XA',
                DeprecationWarning,
            )

        self._clear()
        self._event_status_enable()

    initiate_continuous = attr.property.bool(
        key='INIT:CONT', help='whether to enable triggering to acquire power samples'
    )
    output_trigger = attr.property.bool(
        key='OUTP:TRIG', help='whether to enable the trigger output signal'
    )
    trigger_source = attr.property.str(
        key='TRIG:SOUR',
        case=False,
        only=('IMM', 'INT', 'EXT', 'BUS', 'INT1'),
        help='input source for the acquisitiont trigger',
    )
    trigger_count = attr.property.int(
        key='TRIG:COUN',
        min=1,
        max=200,
        help='the number of contiguous power samples to acquire per trigger',
    )
    measurement_rate = attr.property.str(
        key='SENS:MRAT',
        only=('NORM', 'DOUB', 'FAST'),
        case=False,
        help='measurement speed',
    )
    sweep_aperture = attr.property.float(
        key='SWE:APER',
        min=20e-6,
        max=200e-3,
        help='duration of the acquisition window of each power sample',
        label='s',
    )
    frequency = attr.property.float(
        key='SENS:FREQ',
        min=10e6,
        max=18e9,
        step=1e-3,
        label='Hz',
        help='input signal center frequency',
    )
    auto_calibration = attr.property.bool(
        key='CAL:ZERO:AUTO', help='whether to enable auto-calibration'
    )
    options = attr.property.str(
        key='*OPT',
        sets=False,
        cache=True,
        help='a comma-separated list of installed license options',
    )

    def preset(self, wait=True) -> None:
        """restore the instrument to its default state"""
        self.write('SYST:PRES')
        if wait:
            self.wait()
        self._clear()
        self._event_status_enable()

    def fetch(self, precheck=True) -> typing.Union[float, SeriesType]:
        """return power readings from the instrument.

        Returns:
            a single number if trigger_count == 1, otherwise or pandas.Series"""
        
        if precheck:
            self._check_errors()

        series = self.query_ascii_values('FETC?', container=pd.Series)
        if len(series) == 1:
            return series.iloc[0]
        else:
            ii = np.arange(len(series))
            series.index = pd.Index(self.sweep_aperture * ii, name='Time elapsed (s)')
            series.name = 'Power (dBm)'
            return series

    def zero(self):
        with self.overlap_and_block(30):
            self.write('CAL:ZERO:AUTO ONCE')

    def calibrate(self):
        with self.overlap_and_block(10):
            self.write('CAL:AUTO ONCE')

    @contextlib.contextmanager
    def overlap_and_block(self, timeout=None, quiet=False):
        """context manager that sends '*OPC' on entry, and performs
        a blocking '*OPC?' query on exit.

        These SCPI commands instruct the sensor to execute the commands
        concurrently. On exit out of the python context block, execution
        blocks until all of the commands have completed.

        Example::

            with inst.overlap_and_block():
                inst.write('long running command 1')
                inst.write('long running command 2')

        Arguments:
            timeout: maximum time to wait for '*OPC?' reply, or None to use `self.backend.timeout`
            quiet: Suppress timeout exceptions if this evaluates as True

        Raises:
            TimeoutError: on '*OPC?' query timeout
        """

        self._opc = True
        yield
        self._opc = False

        self._await_completion()
        
    def _await_completion(self, timeout: float=None):
        if timeout is None:
            timeout = self.timeout

        # monitoring *ESR? is recommended by the programming manual
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout:
            try:
                register = int(self.backend.query('*ESR?'))
                time.sleep(0.1)
            except pyvisa.errors.VisaIOError as ex:
                raise ex
            else:
                if register & 1:
                    # first bit == operation complete
                    break
        else:
            raise TimeoutError('command failed')

    def _clear(self):
        self.write('*CLS')

    def _event_status_enable(self):
        self.write('*ESE 1')

    def _check_errors(self):
        code, text = self.query('SYST:ERR?').split(',', 1)
        code = int(code)

        if code == 0:
            return
        else:
            raise IOError(code, text[1:-1])


class KeysightU2044XA(KeysightU2000XSeries):
    model = attr.value.str('U2044XA', inherit=True)


class RohdeSchwarzNRPSeries(lb.VISADevice):
    """Coaxial power sensors connected by USB.

    These require the installation of proprietary drivers from the vendor website.
    Resource strings for connections take the form 'RSNRP::0x00e2::103892::INSTR'.
    """

    _FUNCTIONS = ('POW:AVG', 'POW:BURS:AVG', 'POW:TSL:AVG', 'XTIM:POW', 'XTIM:POWer')
    _TRIGGER_SOURCES = ('HOLD', 'IMM', 'INT', 'EXT', 'EXT1', 'EXT2', 'BUS', 'INT1')

    # Instrument state traits (pass command arguments and/or implement setter/getter)
    frequency = attr.property.float(
        key='SENS:FREQ', min=10e6, step=1e-3, label='Hz', help='calibration frequency'
    )
    initiate_continuous = attr.property.bool(
        key='INIT:CONT',
        help='whether to enable triggering, enabling measurement acquisition',
    )
    options = attr.property.str(
        key='*OPT', sets=False, cache=True, help='installed license options'
    )

    function = attr.property.str(key='SENS:FUNC', case=False, only=_FUNCTIONS)

    @function.setter
    def _(self, value):
        # special case SCPI format: requires quotes around the argument
        self.write(f'SENSe:FUNCtion "{value}"')

    @attr.property.str(key='TRIG:SOUR', case=False, only=_TRIGGER_SOURCES)
    def trigger_source(self):
        """'HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm"""

        # special case - the instrument returns '2' instead of 'EXT2'
        remap = {'2': 'EXT2'}
        source = self.query('TRIG:SOUR?')
        return remap.get(source, default=source)

    trigger_delay = attr.property.float(key='TRIG:DELAY', min=-5, max=10, label='s')
    trigger_count = attr.property.int(key='TRIG:COUN', min=1, max=8192)
    trigger_holdoff = attr.property.float(
        key='TRIG:HOLD',
        min=0,
        max=10,
        label='s',
        help='wait time after trigger before acquisition',
    )
    trigger_level = attr.property.float(
        key='TRIG:LEV',
        min=1e-7,
        max=200e-3,
        label='dBm?',
        help='threshold for power triggering',
    )

    trace_points = attr.property.int(
        key='SENSe:TRACe:POINTs',
        min=1,
        max=8192,
        gets=False,
        help='number of contiguous power samples to acquire per trigger',
    )
    trace_realtime = attr.property.bool(key='TRAC:REAL')
    trace_time = attr.property.float(key='TRAC:TIME', min=10e-6, max=3, label='s')
    trace_offset_time = attr.property.float(
        key='TRAC:OFFS:TIME', min=-0.5, max=100, label='s'
    )
    trace_average_count = attr.property.int(
        key='TRAC:AVER:COUN', min=1, max=65536, label='samples'
    )
    trace_average_mode = attr.property.str(
        key='TRAC:AVER:TCON', only=('MOV', 'REP'), case=False
    )
    trace_average_enable = attr.property.bool(key='TRAC:AVER')

    average_count = attr.property.int(key='AVER:COUN', min=1, max=65536)
    average_auto = attr.property.bool(key='AVER:COUN:AUTO')
    average_enable = attr.property.bool(key='AVER')
    smoothing_enable = attr.property.bool(key='SMO:STAT', gets=False)

    # Local settings traits (leave command unset, and do not implement setter/getter)
    read_termination: str = attr.value.str('\n', inherit=True)

    def preset(self):
        self.write('*PRE')

    def trigger_single(self):
        self.write('INIT')

    def reset(self):
        self.write('*RST')

    def fetch(self) -> typing.Union[SeriesType, float]:
        """Return a single number or pandas Series containing the power readings"""
        series = self.query_ascii_values('FETC?', container=pd.Series)
        if len(series) == 1:
            return float(series.iloc[0])
        series.index = np.arange(len(series)) * (
            self.trace_time / float(self.trace_points)
        )
        series.name = 'Power (dBm)'
        return series

    def fetch_buffer(self):
        """Return a single number or pandas Series containing the power readings"""
        response = self.query('FETC:ARR?').split(',')
        if len(response) == 1:
            return float(response[0])
        else:
            index = None  # np.arange(len(response))*(self.trace_time/float(self.trace_points))
            return pd.to_numeric(pd.Series(response, index=index))

    def setup_trace(
        self,
        frequency: float,
        trace_points: int,
        sample_period: float,
        trigger_level: float,
        trigger_delay: float,
        trigger_source: str,
    ) -> None:
        """establish trace operation.

        Arguments:
            frequency: in Hz
            trace_points: number of points in the trace (perhaps as high as 5000)
            sample_period: in s
            trigger_level: in dBm
            trigger_delay: in s
            trigger_source: 'HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm'
        """

        warnings.warn(
            'setup_trace is deprecated; use RohdeSchwarzNRPTrace instead',
            DeprecationWarning,
        )

        self.reset()
        self.frequency = frequency
        self.function = 'XTIM:POW'
        self.trace_points = trace_points
        self.trace_time = trace_points * sample_period
        self.trigger_level = 10 ** (trigger_level / 10.0)
        self.trigger_delay = trigger_delay  # self.Ts / 2
        self.trace_realtime = True
        self.trigger_source = trigger_source  # 'EXT2'  # Signal analyzer trigger output (10kOhm impedance)
        self.initiate_continuous = False
        self.wait()


class RohdeSchwarzNRP8s(RohdeSchwarzNRPSeries):
    frequency = attr.property.float(inherit=True, max=8e9)


class RohdeSchwarzNRP18s(RohdeSchwarzNRPSeries):
    frequency = attr.property.float(inherit=True, max=18e9)


class PowerTrace_RohdeSchwarzNRP(lb.Rack):
    sensor: RohdeSchwarzNRPSeries

    def setup_trace(
        self,
        frequency: float,
        trace_points: int,
        sample_period: float,
        trigger_level: float,
        trigger_delay: float,
        trigger_source: str,
    ) -> None:
        """establish trace operation.

        Arguments:
            frequency: in Hz
            trace_points: number of points in the trace (perhaps as high as 5000)
            sample_period: in s
            trigger_level: in dBm
            trigger_delay: in s
            trigger_source: 'HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm'
        """

        self.sensor.reset()
        self.sensor.frequency = frequency
        self.sensor.function = 'XTIM:POW'
        self.sensor.trace_points = trace_points
        self.sensor.trace_time = trace_points * sample_period
        self.sensor.trigger_level = 10 ** (trigger_level / 10.0)
        self.sensor.trigger_delay = trigger_delay
        self.sensor.trace_realtime = True
        self.sensor.trigger_source = trigger_source  # 'EXT2'  # Signal analyzer trigger output (10kOhm impedance)
        self.sensor.initiate_continuous = False
        self.sensor.wait()


if __name__ == '__main__':
    from matplotlib import pyplot as plt
    import seaborn as sns

    sns.set(style='ticks')

    # Enable labbench debug messages
    lb.show_messages('info')

    with KeysightU2000XSeries() as sensor:
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

    power.hist(figsize=(6, 2))
    plt.xlabel('Power level')
    plt.ylabel('Count')
    plt.title('Histogram of power sensor readings')
