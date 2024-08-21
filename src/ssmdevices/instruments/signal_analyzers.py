# Authors:
#   Keith Forsyth and Dan Kuester

import os
import time
import labbench as lb
from labbench import paramattr as attr
import typing
import typing_extensions
from typing import Union, Literal

if typing.TYPE_CHECKING:
    import pandas as pd
    import numpy as np
else:
    # delayed import for speed
    pd = lb.util.lazy_import('pandas')
    np = lb.util.lazy_import('numpy')

DataFrameType: typing_extensions.TypeAlias = 'pd.DataFrame'
SeriesType: typing_extensions.TypeAlias = 'pd.Series'
NumpyArrayType: typing_extensions.TypeAlias = 'np.ndarray'

__all__ = [
    'KeysightN9951B',
    'RohdeSchwarzFSW26SpectrumAnalyzer',
    'RohdeSchwarzFSW26IQAnalyzer',
    'RohdeSchwarzFSW26LTEAnalyzer',
    'RohdeSchwarzFSW26RealTime',
    'RohdeSchwarzFSW43Base',
    'RohdeSchwarzFSW43SpectrumAnalyzer',
    'RohdeSchwarzFSW43IQAnalyzer',
    'RohdeSchwarzFSW43LTEAnalyzer',
    'RohdeSchwarzFSW43RealTime',
]

DEFAULT_CHANNEL_NAME = 'remote'


@attr.visa_keying(remap={False: '0', True: '1'})
class KeysightN9951B(lb.VISADevice):
    """A Keysight N9951B "Field Fox".

    Attributes:
        frequency_start (int): the sweep start
    """

    frequency_start = attr.property.float(
        key='FREQ:START', min=1e6, max=43.99e9, label='Hz'
    )
    frequency_stop = attr.property.float(
        key='FREQ:STOP', min=10e6, max=44e9, label='Hz'
    )

    # the bounds on these two vary dynamically with the value of the other.
    # sets=False here to avoid accidents - use frequency_start and frequency_stop
    frequency_span = attr.property.float(key='FREQ:SPAN', sets=False, min=2, max=44e9, label='Hz')
    frequency_center = attr.property.float(
        key='FREQ:CENT', sets=False, min=2, max=26.5e9, step=1e-9, label='Hz'
    )

    initiate_continuous = attr.property.bool(key='INIT:CONT')
    reference_level = attr.property.float(
        key='DISP:WIND:TRAC1:Y:RLEV', step=1e-3, label='dB'
    )

    resolution_bandwidth = attr.property.float(
        key='BAND', min=1e3, max=5.76e6, label='Hz'
    )

    def fetch_trace(self, trace: int = 1) -> DataFrameType:
        """Get trace x values and y values using XVAL? and DATA?

        Arguments:
            trace: which trace to pull from the fieldfox
        """

        x_data = self.query(f'TRAC{trace}:XVAL?').split(',')
        y_data = self.query(f'TRAC{trace}:DATA?').split(',')
        return pd.DataFrame({'Frequency': x_data, 'Power': y_data})

    def get_marker_power(self, marker: int) -> float:
        """Get marker measurement value (on vertical axis)

        Arguments:
            marker: number on instrument display
        Returns:
            position of the marker, in units of the horizontal axis
        """
        return float(self.query(f'CALC:MARK{marker}:Y?'))

    def get_marker_position(self, marker: int) -> float:
        """Get marker position (on horizontal axis)
        Arguments:
            marker: marker number on instrument display

        Returns:
            position of the marker, in units of the horizontal axis
        """
        return float(self.query(f'CALC:MARK{marker}:X?'))

    def set_marker_position(self, marker: int, position: float):
        """Get marker position (on horizontal axis)

        Arguments:
            marker: marker number on instrument display
            position: position of the marker, in units of the horizontal axis
        """
        return self.write(f'CALC:MARK{marker}:X {position}')


@attr.method_kwarg.int('trace', min=1, max=6, help='trace index for analysis')
@attr.method_kwarg.int(
    'output_trigger_index', min=1, max=3, help='output trigger port index'
)
class RohdeSchwarzFSWBase(lb.VISADevice):
    _DATA_FORMATS = 'ASC,0', 'REAL,32', 'REAL,64', 'REAL,16'
    _CHANNEL_TYPES = 'SAN', 'IQ', 'RTIM', DEFAULT_CHANNEL_NAME
    _TRIGGER_OUT_TYPES = 'DEV', 'TARM', 'UDEF'
    _TRIGGER_DIRECTIONS = 'INP', 'OUTP'
    _CHANNEL_TYPES = None, 'SAN', 'IQ', 'RTIM'
    _CACHE_DIR = r'c:\temp\remote-cache'

    expected_channel_type: str = attr.value.str(
        None,
        allow_none=True,
        only=_CHANNEL_TYPES,
        sets=False,
        cache=True,
        help='which channel type to use',
    )
    default_window: str = attr.value.str(
        '', cache=True, help='data window number to use if unspecified'
    )
    default_trace: str = attr.value.str(
        '', cache=True, help='data trace number to use if unspecified'
    )

    # Set these in subclasses for specific FSW instruments
    frequency_center = attr.property.float(
        key='FREQ:CENT', min=0, step=1e-9, label='Hz'
    )
    frequency_span = attr.property.float(key='FREQ:SPAN', min=0, step=1e-9, label='Hz')
    frequency_start = attr.property.float(
        key='FREQ:START', min=0, step=1e-9, label='Hz'
    )
    frequency_stop = attr.property.float(key='FREQ:STOP', min=0, step=1e-9, label='Hz')
    resolution_bandwidth = attr.property.float(key='BAND', min=0, label='Hz')

    sweep_time = attr.property.float(key='SWE:TIME', label='Hz')
    sweep_time_window2 = attr.property.float(key='SENS2:SWE:TIME', label='Hz')

    initiate_continuous = attr.property.bool(key='INIT:CONT')

    reference_level = attr.method.float(
        key='DISP:TRAC{trace}:Y:RLEV', step=1e-3, label='dB'
    )

    amplitude_offset = attr.method.float(
        key='DISP:TRAC{trace}:Y:RLEV:OFFS', step=1e-3, label='dB'
    )

    output_trigger_direction = attr.method.str(
        key='OUTP:TRIG{output_trigger_index}:DIR', only=_TRIGGER_DIRECTIONS, case=False
    )
    output_trigger_type = attr.method.str(
        key='OUTP:TRIG{output_trigger_index}:OTYP', only=_TRIGGER_OUT_TYPES, case=False
    )

    input_preamplifier_enabled = attr.property.bool(key='INP:GAIN:STATE')
    input_attenuation_auto = attr.property.bool(key='INP:ATT:AUTO')
    input_attenuation = attr.property.float(key='INP:ATT', step=1, min=0, max=79)

    channel_type = attr.property.str(key='INST', only=_CHANNEL_TYPES, case=False)
    format = attr.property.str(key='FORM', only=_DATA_FORMATS, case=False)
    sweep_points = attr.property.int(key='SWE:POIN', min=1, max=100001)

    display_update = attr.property.bool(key='SYST:DISP:UPD')
    options = attr.property.str(
        key='*OPT', sets=False, cache=True, help='installed license options'
    )

    def verify_channel_type(self):
        valid = self.expected_channel_type, DEFAULT_CHANNEL_NAME
        if self.expected_channel_type is not None and self.channel_type not in valid:
            self._logger.warning(
                f'expected {self.expected_channel_type} mode, but got {self.channel_type}'
            )

    def open(self):
        self.format = 'REAL,32'

    def acquire_spectrogram(self, acquisition_time_sec):
        t0 = time.time()

        specs = []

        time_remaining = acquisition_time_sec
        active_time = 0

        while active_time == 0:
            # Setup
            self.clear_spectrogram()
            self.wait()
            # Give the power sensor time to arm
            lb.sleep(0.1)

            t0_active = time.time()

            # Try to trigger; block until timeout.
            with self.overlap_and_block(timeout=int(1e3 * time_remaining)):
                self.trigger_single(wait=False)
            active_time += time.time() - t0_active

            self.backend.timeout = 50000
            single = self.fetch_spectrogram(timeout=50000, timestamps='fast')
            self.backend.timeout = 1000

            if single is not None:
                specs.append(single)

            time_remaining = acquisition_time_sec - (time.time() - t0)

        specs = pd.concat(specs, axis=0) if specs else pd.DataFrame()
        return {
            'sa_spectrogram': specs,
            'sa_spectrogram_acquisition_time': time.time() - t0,
            'sa_spectrogram_active_time': active_time,
        }

    def close(self):
        try:
            self.abort()
        except BaseException:
            pass
        try:
            self.clear_status()
        except BaseException:
            pass

    def clear_status(self):
        self.write('*CLS')

    def status_preset(self):
        self.write('STAT:PRES')

    def save_state(self, name: str, basedir: Union[str, None] = None):
        """Save current state of the device to the default directory in the instrument.

        Arguments:
            path: state file location on the instrument
        """
        if basedir is None:
            path = name
        else:
            self.mkdir(basedir)
            path = basedir + '\\' + name

        self.write(f"MMEMory:STORe:STATe 1,'{path}'")
        self.wait()

    def load_state(self, name: str, basedir: Union[str, None] = None):
        """Loads a previously saved state file in the instrument

        Arguments:
            path: state file location on the instrument
        """
        if basedir is not None:
            path = basedir + '\\' + name
        if not path.endswith('.dfl'):
            path = path + '.dfl'

        if self.file_info(path) is None:
            raise FileNotFoundError(
                f'there is no file to load on the instrument at path "{path}"'
            )

        self.write(f"MMEM:LOAD:STAT 1,'{path}'")
        self.wait()

    def load_cache(self):
        cache_name = lb.util.hash_caller(2)

        try:
            self.load_state(cache_name, self._CACHE_DIR)
        except FileNotFoundError:
            return False
        else:
            self._logger.debug('Successfully loaded cached save file')
            return True

    def save_cache(self):
        cache_name = lb.util.hash_caller(2)
        self.save_state(cache_name, self._CACHE_DIR)

    def mkdir(self, path, recursive=True):
        """Make a new directory (optionally recursively) on the instrument
        if we haven't tried to make it already.
        """
        try:
            if path in self.__prev_dirs:
                return
        except AttributeError:
            self.__prev_dirs = set()

        if recursive:
            subs = path.replace('/', '\\').split('\\')
            for i in range(1, len(subs) + 1):
                self.mkdir('\\'.join(subs[:i]), recursive=False)
        else:
            with self.overlap_and_block():
                self.write(f"MMEM:MDIR '{path}'")
            self.__prev_dirs.add(path)
        return path

    def file_info(self, path):
        with self.suppress_timeout(), self.overlap_and_block(timeout=0.1):
            ret = None
            ret = self.query(f"MMEM:CAT? '{path}'")
        return ret

    def remove_window(self, name):
        self.write(f"LAY:REM '{name}'")

    def trigger_single(self, wait=True, disable_continuous=True):
        """Trigger once."""
        if disable_continuous:
            self.initiate_continuous = False
        self.write('INIT')
        if wait:
            self.wait()

    def autolevel(self):
        """Try to automatically set the reference level on the instrument, which sets the
        internal attenuation and preamplifier enable settings.
        """
        self.write('ADJ:LEV')

    def abort(self):
        self.write('ABORT')

    def apply_channel_type(self, type_=None):
        """setup a channel with name DEFAULT_CHANNEL_NAME, that has measurement type self.channel_type"""
        channel_list = self.query('INST:LIST?').replace("'", '').split(',')[1::2]
        if DEFAULT_CHANNEL_NAME in channel_list:
            self.write(
                f"INST:CRE:REPL '{DEFAULT_CHANNEL_NAME}',"
                f"{self.channel_type},'{DEFAULT_CHANNEL_NAME}'"
            )
        else:
            self.write(f"INST:CRE {self.channel_type},'{DEFAULT_CHANNEL_NAME}'")

    def channel_preset(self):
        self.write('SYST:PRES:CHAN')

    def query_ieee_array(self, msg: str) -> NumpyArrayType:
        """An alternative to self.backend.query_binary_values for fetching block data. This
        implementation works around slowness between pyvisa and the instrument that seems to
        result from transferring in chunks of size self.backend.chunk_size as implemented
        in pyvisa.

        The performance of a transfer of a spectrogram with 100,000 time samples is impacted as follows:

        # The pyvisa implementation
        >>>  %timeit -n 1 -r 1 sa.backend.query_binary_values('TRAC2:DATA? SPEC', container=np.array)
        (takes at least 10 minutes)

        # This implementation
        >>> %timeit -n 1 -r 1 sa.query_ieee_array('TRAC2:DATA? SPEC')
        (~23 sec)

        Arguments:
            msg: The SCPI command to send
        :return: a numpy array containing the response.
        """

        from pyvisa.constants import VI_SUCCESS_DEV_NPRESENT, VI_SUCCESS_MAX_CNT

        self._logger.debug(f'query {msg}')

        # The read_termination seems to cause unwanted behavior in self.backend.visalib.read
        self.backend.read_termination, old_read_term = (
            None,
            self.backend.read_termination,
        )
        self.backend.write(msg)

        try:
            with self.backend.ignore_warning(
                VI_SUCCESS_DEV_NPRESENT, VI_SUCCESS_MAX_CNT
            ):
                # Reproduce the behavior of pyvisa.util.from_ieee_block without
                # a priori access to the entire buffer.
                raw, _ = self.backend.visalib.read(self.backend.session, 2)
                digits = int(raw.decode('ascii')[1])
                raw, _ = self.backend.visalib.read(self.backend.session, digits)
                data_size = int(raw.decode('ascii'))

                # Read the actual data
                raw, _ = self.backend.visalib.read(self.backend.session, data_size)

                # Read termination characters so that the instrument doesn't show
                # a "QUERY INTERRUPTED" error when there is unread buffer
                self.backend.visalib.read(self.backend.session, len(old_read_term))
        finally:
            self.backend.read_termination = old_read_term

        data = np.frombuffer(raw, np.float32)
        self._logger.debug('      -> {} bytes ({} values)'.format(data_size, data.size))
        return data

    def fetch_horizontal(self, window=None, trace: int = None):
        if window is None:
            window = self.default_window
        if trace is None:
            trace = self.default_trace

        return self.query_ieee_array(f'TRAC{window}:DATA:X? TRACE{trace}')

    def fetch_trace(self, trace=None, horizontal=False, window=None) -> DataFrameType:
        """Fetch trace data with 'TRAC:DATA TRACE?' and return the result in
        a pandas series.fetch and return the current trace data. This does not
        initiate a trigger; this must be done separately if desired.
        (see :method:`trigger_single`). This method is meant to be used
        in all signal analyzer modes (spectrum analyzer, IQ analyzer, LTE analyzer,
        etc.), because variants of TRAC:DATA TRACE? are implemented for each.

        The `trace` and `window` parameters have different meaning in different
        modes. Specify `window` only in signal analyzer modes that support it,
        which include LTE.  When `window` is not supported, specifying it (any
        value besides `None`) will cause a timeout.

        Trace data is returned in single-precision (32-bit) binary blocks.

        If necessary, we can read the count, set count to 1, read, adjust level
        then set the count back, and read again like this:

        ::
            count = inst.query('SENSE:SWEEP:COUNT?')
            self.write('SENSE:SWEEP:COUNT 1')

        Arguments:
            trace: The trace number to query (or None, the default, to use self.default_trace)
            horizontal: Set the index of the returned Series by a call to :method:`fetch_horizontal`
            window: The window number to query (or None, the default, to use self.default_window)
        """
        if trace is None:
            trace = self.default_trace
        if window is None:
            window = self.default_window
        if hasattr(trace, '__iter__'):
            return pd.concat(
                [self.fetch_trace(t, horizontal=horizontal) for t in trace]
            )

        if horizontal:
            index = self.fetch_horizontal(trace)
            values = self.query_ieee_array(f'TRAC{window}:DATA? TRACE{trace}')
            return pd.DataFrame(values, columns=['Trace ' + trace], index=index)
        else:
            values = self.query_ieee_array(f'TRAC{window}:DATA? TRACE{trace}')
            return pd.DataFrame(values)

    def fetch_timestamps(self, window=None, all=True, timeout=50000) -> NumpyArrayType:
        """Fetch data timestamps associated with acquired data. Not all types of acquired data support timestamping,
        and not all modes support the trace argument. A choice that is incompatible with the current state
        of the signal analyzer should lead to a TimeoutError.

        Arguments:
            all: If True, acquire and return all available timestamps; if False, only the most current timestamp.
            window: The window number corresponding to the desired timestamp data (or self.default_window when window=None)
        """

        if window is None:
            window = self.default_window

        if all:
            _to, self.backend.timeout = self.backend.timeout, timeout

        try:
            scope = 'ALL' if all else 'CURR'
            timestamps = self.backend.query_ascii_values(
                f'CALC{window}:SGR:TST:DATA? {scope}', container=np.array
            )
            timestamps = timestamps.reshape((timestamps.shape[0] // 4, 4))[:, :2]
            ret = timestamps[:, 0] + 1e-9 * timestamps[:, 1]
        finally:
            if all:
                self.backend.timeout = _to

        if not all:
            return ret[0]
        else:
            return ret

    def fetch_spectrogram(
        self,
        window: Union[int, None] = None,
        freqs: str = 'exact',
        timestamps: str = 'exact',
        timeout=None,
    ):
        """
        Fetch a spectrogram without initiating a new trigger. This has been tested in IQ Analyzer and real time
        spectrum analyzer modes. Not all instrument operating modes support trace selection; a choice that is
        incompatible with the current state of the signal analyzer should lead to a TimeoutError.

        Arguments:
            freqs: 'exact' (to fetch the frequency axis), 'fast' (to guess at index values based on FFT parameters), or None (leaving the integer indices)
            timestamps: 'exact' (to fetch the frequency axis), 'fast' (to guess at index values based on sweep time), or None (leaving the integer indices)
            window: The window number corresponding to the desired timestamp data (or self.default_window when window=None)
        :return: a pandas DataFrame containing the acquired data
        """
        if timeout is None:
            if self.trigger_source.lower() == 'mask':
                max_trigger_time = self.trigger_post_time
            else:
                max_trigger_time = self.sweep_dwell_time

            old_timeout, self.backend.timeout = (
                self.backend.timeout,
                6 * 1e3 * max_trigger_time,
            )
        else:
            old_timeout = timeout

        with self.suppress_timeout():
            if window is None:
                window = self.default_window

            data = self.query_ieee_array(f'TRAC{window}:DATA? SPEC')

            # Fetch time axis
            if timestamps not in ('fast', 'exact', None):
                raise ValueError("timestamps argument must be 'fast', 'exact', or None")
            elif timestamps == 'exact':
                t = self.fetch_timestamps(all=True, window=window, timeout=timeout)
            elif timestamps is None:
                t = None

            # Fetch frequency axis
            if freqs == 'fast':
                fc = self.frequency_center
                fsamp = self.iq_sample_rate
                Nfreqs = self.sweep_points
                f_ = fc + np.linspace(
                    -fsamp * (1.0 - 1.0 / Nfreqs) / 2,
                    +fsamp * (1.0 - 1.0 / Nfreqs) / 2,
                    Nfreqs,
                )
            if freqs == 'exact':
                f_ = self.fetch_horizontal(window)
                Nfreqs = len(f_)
            elif freqs is None:
                f_ = None
                Nfreqs = self.sweep_points

            # Reshape data according to frequency axis, since we'll be most certain
            # to know that dimension
            if data.size > 1:
                data = data.reshape((data.size // Nfreqs, Nfreqs))

            # Generate timestamps if we're going to guesstimate
            if timestamps == 'fast':
                if window == 1:
                    sweep_time = self.sweep_time
                else:
                    sweep_time = getattr(self, 'sweep_time_window' + window)
                ts0 = self.fetch_timestamps(all=False, window=window)
                t = (ts0 - sweep_time * data.shape[0]) + sweep_time * np.arange(
                    data.shape[0]
                )[::-1]

            self.backend.timeout = old_timeout

            if data.size > 1:
                return pd.DataFrame(
                    data[::-1], columns=f_, index=None if t is None else t[::-1]
                )
            else:
                return pd.DataFrame([], columns=f_)

        self.backend.timeout = old_timeout

    def fetch_marker(
        self, marker: int, axis: Union[Literal['X'], Literal['Y']]
    ) -> float:
        """Get marker value

        Arguments:
            marker: marker number on instrument display
            axis: 'X' for x axis or 'Y' for y axis
        """
        return float(self.query(f'CALC:MARK{marker}:{axis}?'))

    def get_marker_enables(self) -> DataFrameType:
        markers = list(range(1, 17))
        states = [
            [
                self.query(f'CALC:MARK{m}:STATE?'),
                self.query(f'CALC:MARK{m}:FUNC:BPOW:STATE?'),
            ]
            for m in markers
        ]

        df = pd.DataFrame(states, columns=['Marker', 'Band'], index=markers)

        df.index.name = 'Marker'

        return df.astype(int).astype(bool)

    def get_marker_power(self, marker: int) -> float:
        """Get marker value (on vertical axis)

        Arguments:
            marker: marker number on instrument display
        """
        return float(self.query(f'CALC:MARK{marker}:Y?'))

    def get_marker_position(self, marker: int) -> float:
        """Get marker position (on horizontal axis)

        Arguments:
            marker: marker number on instrument display

        Returns:
            position of the marker, in units of the horizontal axis
        """
        return float(self.query(f'CALC:MARK{marker}:X?'))

    def set_marker_position(self, marker: int, position: float):
        """get marker position (on horizontal axis)

        Arguments:
            marker: marker number on instrument display
            position: position of the marker, in units of the horizontal axis
        """
        return self.write(f'CALC:MARK{marker}:X {position}')

    def trigger_output_pulse(self, port: int):
        """trigger a pulse on a trigger output

        Arguments:
            port: Trigger port number

        :return: None
        """
        self.write(f'OUTPUT:TRIGGER{port}:PULS:IMM')


class _RSSpectrumAnalyzerMixIn(RohdeSchwarzFSWBase):
    expected_channel_type = attr.value.str('SAN', inherit=True)

    def get_marker_band_power(self, marker: int) -> float:
        """Get marker band power measurement

        Arguments:
            marker: marker number on instrument display

        Returns:
            power in dBm
        """

        return float(self.query(f'CALC:MARK{marker}:FUNC:BPOW:RES?'))

    def get_marker_band_span(self, marker: int) -> float:
        """Get span of marker band power measurement

        Arguments:
            marker: marker number on instrument display

        Returns:
            bandwidth in Hz
        """
        return float(self.query(f'CALC:MARK{marker}:FUNC:BPOW:SPAN?'))

    def get_marker_power_table(self):
        """Get the values of all markers."""
        enables = self.get_marker_enables()

        values = pd.DataFrame(
            columns=['Frequency'] + enables.columns.values.tolist(),
            index=enables.index,
            dtype=float,
            copy=True,
        )

        for m in enables.index:
            if enables.loc[m, 'Marker']:
                values.loc[m, 'Marker'] = self.get_marker_power(m)
                values.loc[m, 'Frequency'] = self.get_marker_position(m)

                if enables.loc[m, 'Band']:
                    values.loc[m, 'Band'] = self.get_marker_band_power(m)

        values.dropna(how='all', inplace=True)
        return values

    def fetch_marker_bpow(self, marker: int) -> float:
        """Get marker band power measurement

        Arguments:
            marker: marker number on instrument display

        """

        mark_cmd = 'CALC:MARK' + str(marker) + ':FUNC:BPOW:RES?'
        marker_val = float(self.query(mark_cmd))
        return marker_val

    def fetch_marker_bpow_span(self, marker: int) -> float:
        """Get marker band power measurement

        Arguments:
            marker: marker number on instrument display
        """

        return float(self.query(f'CALC:MARK{marker}:FUNC:BPOW:SPAN?'))


class _RSLTEAnalyzerMixIn(RohdeSchwarzFSWBase):
    format = attr.property.str(key='FORM', only=('REAL', 'ASCII'), case=False)

    @attr.property.float(min=0)
    def uplink_sample_rate(self):
        response = self.query('CONF:LTE:UL:BW?')
        return float(response[2:].replace('_', '.')) * 1e6

    @attr.property.float(min=0)
    def downlink_sample_rate(self):
        response = self.query('CONF:LTE:DL:BW?')
        return float(response[2:].replace('_', '.')) * 1e6

    def open(self):
        lb.VISADevice.open(self)
        # self.verify_channel_type()
        self.format = 'REAL'

    def fetch_power_vs_symbol_x_carrier(self, window, trace):
        data = self.fetch_trace(window=window, trace=trace)

        # Dimensioning is based on LTE standard definitions
        # of the resource block
        Ncarrier = int(50 * self.uplink_sample_rate / 10e6)
        Nsubcarrier = 12 * Ncarrier
        Nsymbol = data.size // Nsubcarrier

        data[data > 1e30] = np.nan

        data = data.values.reshape((Nsymbol, Nsubcarrier))
        data = pd.DataFrame(data)
        data.index.name = 'Symbol'
        data.columns.name = 'Subcarrier'
        return data

    # The methods should be deprecatable now, since the base fetch_trace() should work fine now that format is set
    # in the connect() method and the window parameter is supported by fetch_trace()
    def get_ascii_window_trace(self, window, trace):
        self.write('FORM ASCII')
        data = self.backend.query_ascii_values(
            f'TRAC{window}:DATA? TRACE{trace}', container=pd.Series
        )
        return data

    def get_binary_window_trace(self, window, trace):
        self.write('FORM REAL')
        data = self.backend.query_binary_values(
            f'TRAC{window}:DATA? TRACE{trace}',
            datatype='f',
            is_big_endian=False,
            container=pd.Series,
        )
        return data

    def get_allocation_summary(self, window):
        self.write('FORM ASCII')
        data = self.query(f'TRAC{window}:DATA? TRACE1').split(',')
        return data


class _RSIQAnalyzerMixIn(RohdeSchwarzFSWBase):
    _IQ_FORMATS = ('FREQ', 'MAGN', 'MTAB', 'PEAK', 'RIM', 'VECT')
    _IQ_MODES = ('TDOMain', 'FDOMain', 'IQ')

    expected_channel_type = attr.value.str('RTIM', inherit=True)

    iq_simple_enabled = attr.property.bool(key='CALC:IQ')
    iq_evaluation_enabled = attr.property.bool(key='CALC:IQ:EVAL')
    iq_mode = attr.property.str(key='CALC:IQ:MODE', only=_IQ_MODES, case=False)
    iq_record_length = attr.property.int(key='TRAC:IQ:RLEN', min=1, max=461373440)
    iq_sample_rate = attr.property.float(key='TRAC:IQ:SRAT', min=1e-9, max=160e6)
    iq_format = attr.property.str(key='CALC:FORM', only=_IQ_FORMATS, case=False)
    iq_format_window2 = attr.property.str(
        key='CALC2:FORM', case=False, only=_IQ_FORMATS
    )

    def fetch_trace(self, horizontal=False, trace=None):
        fmt = self.iq_format
        if fmt == 'VECT':
            df = RohdeSchwarzFSWBase.fetch_trace(self, horizontal=False, trace=trace)
        else:
            df = RohdeSchwarzFSWBase.fetch_trace(
                self, horizontal=horizontal, trace=trace
            )

        if fmt == 'RIM':
            if hasattr(df, 'columns'):
                df = pd.DataFrame(
                    df.iloc[: len(df) // 2].values
                    + 1j * df.iloc[len(df) // 2 :].values,
                    index=df.index[: len(df) // 2],
                    columns=df.columns,
                )
            else:
                df = pd.Series(
                    df.iloc[: len(df) // 2].values
                    + 1j * df.iloc[len(df) // 2 :].values,
                    index=df.index[: len(df) // 2],
                )
        if fmt == 'VECT':
            df = pd.DataFrame(df.iloc[1::2].values, index=df.iloc[::2].values)

        return df

    def store_trace(self, path):
        self.write(f"MMEM:STOR:IQ:STAT 1, '{path}'")


class _RSRealTimeMixIn(RohdeSchwarzFSWBase):
    TRIGGER_SOURCES = 'IMM', 'EXT', 'EXT2', 'EXT3', 'MASK', 'TDTR'
    WINDOW_FUNCTIONS = 'BLAC', 'FLAT', 'GAUS', 'HAMM', 'HANN', 'KAIS', 'RECT'
    _BOOL_LABELS = {False: '0', True: '1'}
    expected_channel_type = attr.value.str('RTIM', inherit=True)

    trigger_source = attr.property.str(
        key='TRIG:SOUR', only=TRIGGER_SOURCES, case=False
    )
    trigger_post_time = attr.property.float(key='TRIG:POST', min=0)
    trigger_pre_time = attr.property.float(key='TRIG:PRET', min=0)

    iq_fft_length = attr.property.int(key='IQ:FFT:LENG', sets=False)
    iq_bandwidth = attr.property.float(key='TRAC:IQ:BWID', sets=False)
    iq_sample_rate = attr.property.float(key='TRACe:IQ:SRAT', sets=False)
    iq_trigger_position = attr.property.float(key='TRAC:IQ:TPIS', sets=False)

    sweep_dwell_auto = attr.property.bool(key='SWE:DTIM:AUTO')
    sweep_dwell_time = attr.property.float(key='SWE:DTIM', min=30e-3)
    sweep_window_type = attr.property.str(
        key='SWE:FFT:WIND:TYP', case=False, only=WINDOW_FUNCTIONS
    )

    def store_spectrogram(self, path, window=2):
        self.mkdir(os.path.split(path)[0])
        self.write(f"MMEM:STOR{window}:SGR '{path}'")

    def clear_spectrogram(self, window=2):
        self.write(f'CALC{window}:SGR:CLE')

    def fetch_horizontal(self, window=2, trace=1):
        return self.backend.query_binary_values(
            f'TRAC{window}:X? TRACE{trace}', datatype='f', container=np.array
        )

    def set_detector_type(self, type_, window=None, trace=None):
        if window is None:
            window = self.default_window
        if trace is None:
            trace = self.default_trace
        self.write(f'WIND{window}:DET{trace} {type_}')

    def get_detector_type(self, window=None, trace=None):
        if window is None:
            window = self.default_window
        if trace is None:
            trace = self.default_trace
        return self.query('WIND{window}:DET{trace}?')

    def set_spectrogram_depth(self, depth, window=None):
        if window is None:
            window = self.default_window

        self.write(f'CALC{window}:SPEC:HDEP {depth}')

    def get_spectrogram_depth(self, window=None):
        if window is None:
            window = self.default_window

        return self.query(f'CALC{window}:SPEC:HDEP?')

    @attr.property.float(max=0)
    def trigger_mask_threshold(self):
        return self.get_frequency_mask(first_threshold_only=True)

    @trigger_mask_threshold.setter
    def _(self, thresholds):
        """'defined in dB relative to the reference level"""
        self.set_frequency_mask(thresholds, None)

    def set_frequency_mask(
        self,
        thresholds: list[float],
        frequency_offsets: list[float] = None,
        kind=Union[Literal['upper'], Literal['lower']],
        window: int = None,
    ):
        """Define the frequency-dependent trigger threshold values for a frequency mask trigger.

        Arguments:
            thresholds: trigger threshold at each frequency in db relative to the reference level (same size as `frequency_offsets`), or a scalar to use a constant value across the band
            array-like frequency_offsets: frequencies at which the mask is defined, or None (to specify across the whole band)
            kind: either 'upper' or 'lower,' corresponding to a trigger on entering the upper trigger definition or on leaving the lower trigger definition
            window: The window number corresponding to the desired trigger setting (or self.default_window when window=None)
        :return: None
        """
        if window is None:
            window = self.default_window
        if kind.lower() not in ('upper', 'lower'):
            raise ValueError(
                f'frequency mask is "{kind}" but must be "upper" or "lower"'
            )
        if frequency_offsets is None:
            bw = self.iq_bandwidth
            frequency_offsets = -bw / 2, bw / 2

            if not hasattr(thresholds, '__iter__'):
                thresholds = len(frequency_offsets) * [thresholds]
            elif len(thresholds) != 2:
                raise ValueError(
                    'with frequency_offsets=None, thresholds must be a scalar or have length 2'
                )

        self.write(f"CALC{window}:MASK:CDIR '.'")
        self.write(f"CALC{window}:MASK:NAME '{DEFAULT_CHANNEL_NAME}'")
        flat = np.array([frequency_offsets, thresholds]).T.flatten()

        plist = ','.join(flat.astype(str))

        self.write(f'CALC{window}:MASK:{kind} {plist}')

    def get_frequency_mask(
        self,
        kind: Union[Literal['upper'], Literal['lower']] = 'upper',
        window: int = None,
        first_threshold_only: bool = False,
    ):
        """Define the frequency-dependent trigger threshold values for a frequency mask trigger.

        Arguments:
            kind: either 'upper' or 'lower,' corresponding to a trigger on entering the upper trigger definition or on leaving the lower trigger definition
            window: The window number corresponding to the desired trigger setting (or self.default_window when window=None)
            bool first_threshold_only: if True, return only the threshold; otherwise, return a complete parameter dict
        :return: the threshold or a dictionary with keys "frequency_offsets" and "thresholds" and corresponding values (in Hz and dBm, respectively) of equal length
        """

        if window is None:
            window = self.default_window
        if kind.lower() not in ('upper', 'lower'):
            raise ValueError(
                f'frequency mask is "{kind}" but must be "upper" or "lower"'
            )

        plist = self.query(f'CALC{window}:MASK:{kind}?')
        plist = np.array(plist.split(',')).astype(np.float64)

        if first_threshold_only:
            return plist[1]
        else:
            return {'frequency_offsets': plist[::2], 'thresholds': plist[1::2]}

    def setup_spectrogram(
        self,
        center_frequency: float,
        analysis_bandwidth: float,
        reference_level: float,
        time_resolution: float,
        acquisition_time: float,
        input_attenuation: Union[float, None] = None,
        trigger_threshold: Union[float, None] = None,
        detector: Union[Literal['SAMP'], Literal['AVER']] = 'SAMP',
        analysis_window: Union[str, None] = None,
    ):
        """Quick setup for a spectrogram measurement in RTSA mode.

        Arguments:
            center_frequency: in Hz
            frequency_span: in Hz
            reference_level: in dBm
            time_resolution: in s
            acquisition_time: in s
            input_attenuation: in dB (or None to autoset based on the reference level)
            trigger_threshold: in dB (or None to free run)
            detector: 'SAMP' or 'AVER'
            analysis_window: one of ['BLAC','FLAT','GAUS','HAMM','HANN','KAIS','RECT']
        :return:
        """

        self.default_window = 2
        self.default_trace = 1

        if self.load_cache():
            return

        # Work around an apparent SCPI bug by setting
        # frequency parameters in spectrum analyzer mode
        with self.overlap_and_block(timeout=10000):
            self.apply_channel_type('SAN')
        self.channel_preset()
        self.wait()
        self.frequency_center = center_frequency
        self.wait()
        with self.overlap_and_block(timeout=10000):
            self.apply_channel_type('RTIM')
        self.wait()
        self.initiate_continuous = False
        self.frequency_span = analysis_bandwidth

        # Setup traces
        self.remove_window(1)

        # Level
        self.reference_level(reference_level, trace=1)
        if input_attenuation is not None:
            self.input_attenuation = input_attenuation
            if reference_level <= -30 and input_attenuation <= 5:
                self.input_preamplifier_enabled = True

        # Trace acquisition parameters
        self.set_detector_type(detector)

        # Sweep parameters
        self.sweep_time_window2 = time_resolution
        if self.sweep_time_window2 != time_resolution:
            self._logger.warning(
                f'requested time resolution {time_resolution}, '
                f'but instrument adjusted to {self.sweep_time_window2}'
            )
        self.spectrogram_depth = 100000

        # Triggering
        if trigger_threshold is not None:
            self.trigger_source = 'MASK'
            th = 2 * [trigger_threshold] + [0] + 2 * [trigger_threshold]
            rbw = 2 * self.resolution_bandwidth
            fr = [-analysis_bandwidth / 2, -rbw, 0, rbw, analysis_bandwidth / 2]
            self.set_frequency_mask(thresholds=th, frequency_offsets=fr)
            self.trigger_post_time = acquisition_time
            self.trigger_pre_time = 0.0
            self.trigger_post_time = acquisition_time
        else:
            self.sweep_dwell_auto = False
            self.sweep_dwell_time = acquisition_time

        # TODO: Parameterize somehow
        for i in (2, 3):
            self.output_trigger_direction('OUTP', output_trigger_index=i)
            self.output_trigger_type('DEV', output_trigger_index=i)
        if analysis_window is not None:
            self.sweep_window_type = 'BLAC'

        with self.overlap_and_block(timeout=2500):
            self.save_cache()
        lb.sleep(0.05)

        with self.overlap_and_block():
            self.spectrogram_depth

    def acquire_spectrogram_sequence(
        self, loop_time=None, delay_time=0.1, timestamps='fast'
    ):
        """Trigger and fetch data, optionally in a loop that continues for a specified
        duration.

        Arguments:
            loop_time: time (in s) to spend looping repeated trigger-fetch cycles, or None to execute once
            delay_time: delay time before starting (in s)
            timestamps: 'fast' (with potential for rounding errors to ~ 10 ns) or 'exact' (slow and not recommended)
        :return: dictionary structured as {'spectrogram': pd.DataFrame, 'spectrogram_acquisition_time': float, 'spectrogram_active_time': float}
        """
        specs = []

        if self.trigger_source.lower() == 'mask':
            max_trigger_time = self.trigger_post_time
        else:
            max_trigger_time = self.sweep_dwell_time
        t0 = time.time()
        time_remaining = loop_time
        active_time = 0

        while loop_time is None or time_remaining > 0:
            # Setup
            self.clear_spectrogram()
            self.wait()
            # Give the power sensor time to arm
            lb.sleep(delay_time)

            t0_active = time.time()
            # Try to trigger; block until timeout.
            with self.suppress_timeout():
                # print(max(30*max_trigger_time,time_remaining or 0.1))
                with self.overlap_and_block(timeout=int(1e3 * 30 * max_trigger_time)):
                    self.trigger_single(wait=False)
                lb.sleep(0.05)
                active_time += time.time() - t0_active

                self.backend.timeout = 6 * 1e3 * max_trigger_time
                single = self.fetch_spectrogram(
                    timeout=self.backend.timeout, timestamps=timestamps
                )
                self.backend.timeout = 1000
                if single is not None:
                    specs.append(single)
                self.wait()
            self.abort()

            if loop_time is None:
                break
            else:
                time_remaining = loop_time - (time.time() - t0)

        if len(specs) > 0:
            specs = pd.concat(specs, axis=0) if specs else pd.DataFrame().iloc[:, :-1]
        else:
            specs = pd.DataFrame()
            self._logger.warning('no data acquired')

        return {
            'spectrogram_data': specs,
            'spectrogram_acquisition_time': time.time() - t0,
            'spectrogram_active_time': active_time,
        }

    def arm_spectrogram(self):
        self.clear_spectrogram()
        self.wait()

    def acquire_spectrogram(self):
        """Trigger and acquire data, optionally in a loop that continues for a specified
        duration.

        :return: dictionary structured as {'spectrogram_active_time': float}
        """
        t0 = time.time()

        if self.trigger_source.lower() == 'mask':
            max_trigger_time = self.trigger_post_time
        else:
            max_trigger_time = self.sweep_dwell_time

        # Try to trigger; block until timeout.
        # print(max(30*max_trigger_time,time_remaining or 0.1))
        with self.overlap_and_block(timeout=int(1e3 * 30 * max_trigger_time)):
            self.trigger_single(wait=False)

        return {'spectrogram_active_time': time.time() - t0}


class RohdeSchwarzFSW26Base(RohdeSchwarzFSWBase):
    frequency_center = attr.property.float(max=26.5e9, inherit=True)
    frequency_span = attr.property.float(max=26.5e9, inherit=True)
    frequency_start = attr.property.float(max=26.5e9, inherit=True)
    frequency_stop = attr.property.float(max=26.5e9, inherit=True)


class RohdeSchwarzFSW26SpectrumAnalyzer(
    RohdeSchwarzFSW26Base, _RSSpectrumAnalyzerMixIn
):
    pass


class RohdeSchwarzFSW26LTEAnalyzer(RohdeSchwarzFSW26Base, _RSLTEAnalyzerMixIn):
    pass


class RohdeSchwarzFSW26IQAnalyzer(RohdeSchwarzFSW26Base, _RSIQAnalyzerMixIn):
    pass


class RohdeSchwarzFSW26RealTime(RohdeSchwarzFSW26Base, _RSRealTimeMixIn):
    pass


class RohdeSchwarzFSW43Base(RohdeSchwarzFSWBase):
    frequency_center = attr.property.float(max=43.5e9, inherit=True)
    frequency_span = attr.property.float(max=43.5e9, inherit=True)
    frequency_start = attr.property.float(max=43.5e9, inherit=True)
    frequency_stop = attr.property.float(max=43.5e9, inherit=True)


class RohdeSchwarzFSW43SpectrumAnalyzer(
    RohdeSchwarzFSW43Base, _RSSpectrumAnalyzerMixIn
):
    pass


class RohdeSchwarzFSW43LTEAnalyzer(RohdeSchwarzFSW43Base, _RSLTEAnalyzerMixIn):
    pass


class RohdeSchwarzFSW43IQAnalyzer(RohdeSchwarzFSW43Base, _RSIQAnalyzerMixIn):
    pass


class RohdeSchwarzFSW43RealTime(RohdeSchwarzFSW43Base, _RSRealTimeMixIn):
    pass
