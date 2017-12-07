from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
from builtins import super
from builtins import int
from future import standard_library
standard_library.install_aliases()
from builtins import str,range
import os,pyvisa,datetime,logging
import numpy as np

logger = logging.getLogger('labbench')

__all__ = ['RohdeSchwarzFSW26Base',
           'RohdeSchwarzFSW26SpectrumAnalyzer',
           'RohdeSchwarzFSW26IQAnalyzer',
           'RohdeSchwarzFSW26LTEAnalyzer',
           'RohdeSchwarzFSW26RealTime']

import labbench as lb
from labbench import Bool, CaselessStrEnum, Int, Float
from labbench.visa import VISADevice
import pandas as pd
from pyvisa.constants import VI_SUCCESS_DEV_NPRESENT,VI_SUCCESS_MAX_CNT

class RohdeSchwarzFSW26Base(VISADevice):
    expect_channel_type = None

    class state(VISADevice.state):
        frequency_center        = Float     (command='FREQ:CENT',  min=2, max=26.5e9, step=1e-9, label='Hz')
        frequency_span          = Float     (command='FREQ:SPAN',  min=2, max=26.5e9, step=1e-9, label='Hz')
        frequency_start         = Float     (command='FREQ:START', min=2, max=26.5e9, step=1e-9, label='Hz')
        frequency_stop          = Float     (command='FREQ:STOP',  min=2, max=26.5e9, step=1e-9, label='Hz')
        
        resolution_bandwidth    = Float     (command='BAND',       min=45e3, max=5.76e6, label='Hz')
        sweep_time              = Float     (command='SWE:TIME',   label='Hz')
        sweep_time_trace2       = Float     (command='SENS2:SWE:TIME',   label='Hz')
    
        initiate_continuous     = Bool      (command='INIT:CONT', trues=['1'], falses=['0'])
    
        reference_level         = Float     (command='DISP:TRAC1:Y:RLEV', step=1e-3,label='dB')
        reference_level_trace2  = Float     (command='DISP:TRAC2:Y:RLEV', step=1e-3,label='dB')
        reference_level_trace3  = Float     (command='DISP:TRAC3:Y:RLEV', step=1e-3,label='dB')
        reference_level_trace4  = Float     (command='DISP:TRAC4:Y:RLEV', step=1e-3,label='dB')
        reference_level_trace5  = Float     (command='DISP:TRAC5:Y:RLEV', step=1e-3,label='dB')
        reference_level_trace6  = Float     (command='DISP:TRAC6:Y:RLEV', step=1e-3,label='dB')
        
        amplitude_offset        = Float     (command='DISP:TRAC1:Y:RLEV:OFFS',step=1e-3,label='dB')
        amplitude_offset_trace2 = Float     (command='DISP:TRAC2:Y:RLEV:OFFS',step=1e-3,label='dB')
        amplitude_offset_trace3 = Float     (command='DISP:TRAC3:Y:RLEV:OFFS',step=1e-3,label='dB')
        amplitude_offset_trace4 = Float     (command='DISP:TRAC4:Y:RLEV:OFFS',step=1e-3,label='dB')
        amplitude_offset_trace5 = Float     (command='DISP:TRAC5:Y:RLEV:OFFS',step=1e-3,label='dB')
        amplitude_offset_trace6 = Float     (command='DISP:TRAC6:Y:RLEV:OFFS',step=1e-3,label='dB')
        
        channel_type            = CaselessStrEnum (command='INST', values=['SAN','IQ','RTIM'], is_metadata=True)
        format                  = CaselessStrEnum (command='FORM', values=['ASC,0','REAL,32','REAL,64', 'REAL,16'])
        sweep_points            = Int       (command='SWE:POIN', min=1, max=100001)
         
        display_update          = Bool      (command='SYST:DISP:UPD', trues=['ON'], falses=['OFF'])

        default_window          = lb.LocalUnicode('', help='data window number to use if unspecified')
        default_trace           = lb.LocalUnicode('', help='data trace number to use if unspecified')

    def verify_channel_type (self):
        if self.expect_channel_type is not None and self.state.channel_type != self.expect_channel_type:
            raise Exception('{} expects {} mode, but insrument mode is {}'\
                            .format(type(self).__name__, self.expect_channel_type, self.state.channel_type))        

    def setup(self):
        super().setup()
        self.verify_channel_type()
        self.state.format = 'REAL,32'

    def cleanup(self):
        try:
            self.abort()
        except:
            pass
        try:
            self.clear_status()
        except:
            pass

    def clear_status (self):
        self.write('*CLS')

    def status_preset (self):
        self.write('STAT:PRES')

    def save_state (self, path):
        ''' Save current state of the device to the default directory.
            :param path: state file location on the instrument
            :type path: string

        '''
        self.write('MMEMory:STORe:STATe 1,"{}""'.format(path))
    
    def load_state(self, path):
        ''' Loads a previously saved state file in the instrument
        
            :param path: state file location on the instrument
            :type path: string
        '''
        cmd = "MMEM:LOAD:STAT 1,'{}'".format(path)
        self.write(cmd)
        self.verify_channel_type()

    def mkdir(self, path, recursive=True):
        ''' Make a new directory (optionally recursively) on the instrument
            if we haven't tried to make it already.
        '''
        try:
            if path in self.__prev_dirs:
                return
        except AttributeError:
            self.__prev_dirs = set()
        
        if recursive:
            subs=path.replace('/','\\').split('\\')
            for i in range(1,len(subs)+1):
                self.mkdir('\\'.join(subs[:i]), recursive=False)              
        else:
            with self.overlap_and_block:
                self.write(r"MMEM:MDIR '{}'".format(path))
            self.__prev_dirs.add(path)
        
    def trigger_single (self, wait=True, disable_continuous=True):
        ''' Trigger once.
        '''
        if disable_continuous:
            self.state.initiate_continuous = False
        self.write('INIT')
        if wait:
            self.wait()

    def autolevel (self):
        ''' Try to automatically set the reference level on the instrument, which sets the
            internal attenuation and preamplifier enable settings.
        '''
        self.write("ADJ:LEV")

    def abort (self):
        self.write('ABORT')

    def query_ieee_array (self, msg):
        ''' An alternative to self.backend.query_binary_values for fetching block data. This
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

        :param msg: The SCPI command to send
        :return: a numpy array containing the response.
        '''

        logger.debug(logger.debug('{}.query <- {}'.format(repr(self),msg)))

        # The read_termination seems to cause unwanted behavior in self.backend.visalib.read
        self.backend.read_termination, old_read_term = None, self.backend.read_termination
        self.backend.write(msg)

        with self.backend.ignore_warning(VI_SUCCESS_DEV_NPRESENT, VI_SUCCESS_MAX_CNT):
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

        self.backend.read_termination = old_read_term

        data = np.frombuffer(raw, np.float32)
        logger.debug('{}.query -> {} bytes ({} values)'.format(repr(self), data_size,data.size))
        return data

    def fetch_horizontal (self, window=None, trace=None):
        if window is None:
            window = self.state.default_window
        if trace is None:
            trace = self.state.default_trace

        return self.query_ieee_array("TRAC{window}:DATA:X? TRACE{trace}"\
                                        .format(window=window,trace=trace))

    def fetch_trace(self, trace=None, horizontal=False, window=None):
        ''' Fetch trace data with 'TRAC:DATA TRACE?' and return the result in
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
                count = inst.query("SENSE:SWEEP:COUNT?")
                self.write("SENSE:SWEEP:COUNT 1")

        :param trace: The trace number to query (or None, the default, to use self.state.default_trace)
        :param horizontal: Set the index of the returned Series by a call to :method:`fetch_horizontal`
        :param window: The window number to query (or None, the default, to use self.state.default_window)
        :return: a pd.Series object containing the returned data
        '''

        if trace is None:
            trace = self.state.default_trace
        if window is None:
            window = self.state.default_window
        if hasattr(trace, '__iter__'):
            return pd.concat([self.fetch_trace(t,horizontal=horizontal) for t in trace])
        
        if horizontal:
            index = self.fetch_horizontal(trace)
            values = self.query_ieee_array("TRAC{window}:DATA? TRACE{trace}"\
                                              .format(trace=trace, window=window))
            name = 'Trace {}'.format(trace)
            return pd.DataFrame(values, columns=[name], index=index)
        else:
            values = self.query_ieee_array("TRAC{window}:DATA? TRACE{trace}"\
                                              .format(trace=trace, window=window))
            return pd.DataFrame(values)

    def fetch_timestamps (self, window=None, all=True, timeout=50000):
        ''' Fetch data timestamps associated with acquired data. Not all types of acquired data support timestamping,
            and not all modes support the trace argument. A choice that is incompatible with the current state
            of the signal analyzer should lead to a pyvisa.TimeoutError.

        :param all: If True, acquire and return all available timestamps; if False, only the most current timestamp.
        :param window: The window number corresponding to the desired timestamp data (or self.state.default_window when window=None)
        :return: A number (when `all` is False) or a np.array (when `all` is True)
        '''

        if window is None:
            window = self.state.default_window

        if all:
            _to, self.backend.timeout = self.backend.timeout, timeout

        try:
            scope = 'ALL' if all else 'CURR'
            timestamps = self.backend.query_ascii_values(r'CALC{window}:SGR:TST:DATA? {scope}'\
                                                          .format(window=window, scope=scope),\
                                                         container=np.array)
            timestamps = timestamps.reshape((timestamps.shape[0]//4,4))[:,:2]
            ret = timestamps[:,0] + 1e-9*timestamps[:,1]
        finally:
            if all:
                self.backend.timeout = _to

        if not all:
            return ret[0]
        else:
            return ret

    def fetch_spectrogram (self, window=None, freqs='exact', timestamps='exact', timeout=50000):
        '''
        Fetch a spectrogram without initiating a new trigger. This has been tested in IQ Analyzer and real time
        spectrum analyzer modes. Not all instrument operating modes support trace selection; a choice that is
        incompatible with the current state of the signal analyzer should lead to a pyvisa.TimeoutError.

        :param freqs: 'exact' (to fetch the frequency axis), 'fast' (to guess at index values based on FFT parameters), or None (leaving the integer indices)
        :param timestamps: 'exact' (to fetch the frequency axis), 'fast' (to guess at index values based on sweep time), or None (leaving the integer indices)
        :param window: The window number corresponding to the desired timestamp data (or self.state.default_window when window=None)
        :return: a pandas DataFrame containing the acquired data
        '''

        with self.suppress_timeout():
            if window is None:
                window = self.state.default_window

            data = self.query_ieee_array('TRAC{window}:DATA? SPEC'.format(window=window))

            # Fetch time axis
            if timestamps == 'fast':
                sweep_time = self.state.sweep_time_trace2
                ts0 = self.fetch_timestamps(all=False, window=window)
                dt0=datetime.datetime.fromtimestamp(ts0)
            elif timestamps == 'exact':
                t = self.fetch_timestamps(all=True, window=window, timeout=timeout)
            elif timestamps == None:
                t = None
            else:
                raise ValueError("timestamps argument must be 'fast', 'exact', or None")

            # Fetch frequency axis
            if freqs == 'fast':
                fc = self.state.frequency_center
                fsamp = self.state.iq_sample_rate
                Nfreqs = self.state.sweep_points
                f_ = fc+np.linspace(-fsamp*(1.-1./Nfreqs)/2,+fsamp*(1.-1./Nfreqs)/2, Nfreqs)
            if freqs == 'exact':
                f_  = self.fetch_horizontal(window)
                Nfreqs = len(f_)
            elif freqs == None:
                f_ = None
                Nfreqs = self.state.sweep_points

            # Reshape data according to frequency axis, since we'll be most certain
            # to know that dimension
            if data.size > 1:
                data = data.reshape((data.size//Nfreqs,Nfreqs))

            # Generate timestamps if we're going to guesstimate
            if timestamps == 'fast':
                t = dt0+pd.to_timedelta(sweep_time*1e9*np.arange(data.shape[0]), unit='ns')

            if data.size > 1:
                return pd.DataFrame(data[::-1], columns=f_, index=None if t is None else t[::-1])
            else:
                return pd.DataFrame([], columns=f_)

        # If there is a timeout, the return above will not happen.
        # In this case, abort the acquisition and return
        # None.
        logger.warning('received no spectrogram data')
        self.abort()
        #self.clear_status()
        #self.wait()
        return None
    
    def fetch_marker(self, marker, axis):
        ''' Get marker value
        
            :param marker: marker number on instrument display
            :type marker: int
            :param axis: 'X' for x axis or 'Y' for y axis
            :type axis: str
        '''
        mark_cmd = "CALC:MARK"+ str(marker) + ":" + axis + "?"
        marker_val = float(self.query(mark_cmd))
        return marker_val

    def get_marker_enables(self):
        enable_cmd = 'CALC:MARK{}:STATE?'
        bw_cmd = 'CALC:MARK{}:FUNC:BPOW:STATE?'

        markers = list(range(1,17))
        states = [[self.query(enable_cmd.format(m)),
                   self.query(bw_cmd.format(m))] for m in markers]

        df = pd.DataFrame(states, columns=['Marker', 'Band'],
                          index=markers).astype(int).astype(bool)
        df.index.name = 'Marker'
        
        return df
        
    def get_marker_power(self, marker):
        ''' Get marker value (on vertical axis)
        
            :param marker: marker number on instrument display
            
            :type marker: int
            
            :param axis: 'X' for x axis or 'Y' for y axis
            
            :type axis: str
        '''
        mark_cmd = "CALC:MARK{}:Y?".format(marker)
        return float(self.query(mark_cmd))

    def get_marker_position(self, marker):
        ''' Get marker position (on horizontal axis)
        
            :param marker: marker number on instrument display
            
            :type marker: int
            
            :param axis: 'X' for x axis or 'Y' for y axis
            
            :type axis: str
        '''
        mark_cmd = "CALC:MARK{}:X?".format(marker)
        return float(self.query(mark_cmd))
    
    def set_marker_position(self, marker, position):
        ''' Get marker position (on horizontal axis)
        
            :param marker: marker number on instrument display
            
            :type marker: int
            
            :param axis: 'X' for x axis or 'Y' for y axis
            
            :type axis: str
        '''
        mark_cmd = "CALC:MARK{}:X {}".format(marker,position)
        return self.write(mark_cmd)

    def trigger_output_pulse (self, port):
        '''

        :param port: Trigger port number
        :param duration: "On" time duration of pulse(in s)
        :return: None
        '''
        self.write('OUTPUT:TRIGGER{port}:PULS:IMM'.format(port=port))
    

class RohdeSchwarzFSW26SpectrumAnalyzer(RohdeSchwarzFSW26Base):
    expect_channel_type = 'SAN'
    
    def get_marker_band_power(self, marker):
        ''' Get marker band power measurement
        
            :param marker: marker number on instrument display
e            
            :type marker: int
            
            :return: power in dBm
            
            :rtype: float
        '''
        
        mark_cmd = "CALC:MARK{}:FUNC:BPOW:RES?".format(marker)
        return float(self.query(mark_cmd))
        
    def get_marker_band_span(self, marker):
        ''' Get span of marker band power measurement
        
            :param marker: marker number on instrument display
            
            :type marker: int
            
            :return: bandwidth
            
            :rtype: float
        '''

        mark_cmd = "CALC:MARK{}:FUNC:BPOW:SPAN?".format(marker)
        return float(self.query(mark_cmd))

    def get_marker_power_table(self):
        ''' Get the values of all markers.
        '''
        enables = self.get_marker_enables()
        values = pd.DataFrame(columns=['Frequency']+enables.columns.values.tolist(),index=enables.index,
                              dtype=float, copy=True)

        for m in enables.index:
            if enables.loc[m,'Marker'] == True:
                values.loc[m,'Marker'] = self.get_marker_power(m)
                values.loc[m,'Frequency'] = self.get_marker_position(m)
                if enables.loc[m,'Band'] == True:
                    values.loc[m,'Band'] = self.get_marker_band_power(m)

        values.dropna(how='all',inplace=True)
        return values
    
    def fetch_marker_bpow(self, marker):
        ''' Get marker band power measurement
        
            :param marker: marker number on instrument display
            
            :type marker: int
            
            :return: power in dBm
            
            :rtype: float
        '''
        
        mark_cmd = "CALC:MARK"+ str(marker) + ":FUNC:BPOW:RES?"
        marker_val = float(self.query(mark_cmd))
        return marker_val

    def fetch_marker_bpow_span(self, marker):
        ''' Get marker band power measurement
        
            :param marker: marker number on instrument display
            
            :type marker: int
            
            :return: bandwidth
            
            :rtype: float
        '''
        
        mark_cmd = "CALC:MARK"+ str(marker) + ":FUNC:BPOW:SPAN?"
        marker_span = float(self.query(mark_cmd))
        return marker_span    


class RohdeSchwarzFSW26LTEAnalyzer(RohdeSchwarzFSW26Base):
    class state(RohdeSchwarzFSW26Base.state):
        format = CaselessStrEnum(command='FORM', values=['REAL', 'ASCII'])
        uplink_sample_rate = Float(min=0)
        downlink_sample_rate = Float(min=0)

    @state.uplink_sample_rate.getter
    def __ (self, *args, **kws):
        response = self.query('CONF:LTE:UL:BW?')
        return float(response[2:].replace('_','.'))*1e6

    @state.downlink_sample_rate.getter
    def __ (self, *args, **kws):
        response = self.query('CONF:LTE:DL:BW?')
        return float(response[2:].replace('_','.'))*1e6

    def connect (self):
        VISADevice.connect(self)
        self.verify_channel_type()
        self.state.format = 'REAL'

    def fetch_power_vs_symbol_x_carrier (self, window, trace):
        data = self.fetch_trace(window=window, trace=trace)

        # Dimensioning is based on LTE standard definitions
        # of the resource block
        Ncarrier = int(50*self.state.uplink_sample_rate/10e6)
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
    def get_ascii_window_trace(self,window,trace):
        self.write('FORM ASCII')
        data = self.backend.query_ascii_values("TRAC{window}:DATA? TRACE{trace}".format(window=window,trace=trace), container=pd.Series)
        return data

    def get_binary_window_trace(self,window,trace):
        self.write('FORM REAL')
        data=self.backend.query_binary_values("TRAC{window}:DATA? TRACE{trace}".format(window=window,trace=trace), datatype='f', is_big_endian=False, container=pd.Series)
        return data

    def get_allocation_summary(self,window):
        self.write('FORM ASCII')
        data=self.query("TRAC{window}:DATA? TRACE1".format(window=window)).split(',')
        return data
    
    
class RohdeSchwarzFSW26IQAnalyzer(RohdeSchwarzFSW26Base):
    expect_channel_type = 'RTIM'
    
    class state(RohdeSchwarzFSW26Base.state):
        iq_simple_enabled     = Bool      (command='CALC:IQ', trues=['ON'], falses=['OFF'])
        iq_evaluation_enabled = Bool      (command='CALC:IQ:EVAL', trues=['ON'], falses=['OFF'])
        iq_mode               = CaselessStrEnum (command='CALC:IQ:MODE', values=['TDOMain','FDOMain','IQ'])
        iq_record_length      = Int       (command='TRAC:IQ:RLEN', min=1, max=461373440)
        iq_sample_rate        = Float     (command='TRAC:IQ:SRAT', min=1e-9, max=160e6)
        iq_format             = CaselessStrEnum (command='CALC:FORM', values=['FREQ','MAGN', 'MTAB','PEAK','RIM','VECT'])
        iq_format_window2     = CaselessStrEnum (command='CALC2:FORM', values=['FREQ','MAGN', 'MTAB','PEAK','RIM','VECT'])

    def fetch_trace(self, horizontal=False, trace=None):
        fmt = self.state.iq_format
        if fmt == 'VECT':
            df = RohdeSchwarzFSW26Base.fetch_trace(self,horizontal=False,trace=trace)
        else:
            df = RohdeSchwarzFSW26Base.fetch_trace(self,horizontal=horizontal,trace=trace)
        
        if fmt == 'RIM':
            if hasattr(df,'columns'):
                df = pd.DataFrame(df.iloc[:len(df)//2].values+1j*df.iloc[len(df)//2:].values,
                                  index=df.index[:len(df)//2],
                                  columns=df.columns)
            else:
                df = pd.Series(df.iloc[:len(df)//2].values+1j*df.iloc[len(df)//2:].values,
                                  index=df.index[:len(df)//2])
        if fmt == 'VECT':
            df = pd.DataFrame(df.iloc[1::2].values,index=df.iloc[::2].values)
            
        return df

    def store_trace(self, path):
        self.write("MMEM:STOR:IQ:STAT 1, '{}'".format(path))


class RohdeSchwarzFSW26RealTime(RohdeSchwarzFSW26Base):
    expect_channel_type = 'RTIM'
    
    class state(RohdeSchwarzFSW26Base.state):
        pass
    
#        
#    def fetch_trace(self, horizontal=False):
#        fmt = self.state.iq_format
#        if fmt == 'VECT':
#            df = RohdeSchwarzFSW26Base.fetch_trace(self,1,False)
#        else:
#            df = RohdeSchwarzFSW26Base.fetch_trace(self,1,horizontal)
#        
#        if fmt == 'RIM':
#            if hasattr(df,'columns'):
#                df = pd.DataFrame(df.iloc[:len(df)//2].values+1j*df.iloc[len(df)//2:].values,
#                                  index=df.index[:len(df)//2],
#                                  columns=df.columns)
#            else:
#                df = pd.Series(df.iloc[:len(df)//2].values+1j*df.iloc[len(df)//2:].values,
#                                  index=df.index[:len(df)//2])
#        if fmt == 'VECT':
#            df = pd.DataFrame(df.iloc[1::2].values,index=df.iloc[::2].values)
#            
#        return df

    def store_spectrogram(self, path, window=2):
        self.mkdir(os.path.split(path)[0])
        self.write("MMEM:STOR{window}:SGR '{path}'"\
                   .format(window=window,path=path))   

    def clear_spectrogram(self, window=2):
        self.write("CALC{window}:SGR:CLE"\
                   .format(window=window))

    def fetch_horizontal (self, window=2, trace=1):
        return self.backend.query_binary_values(r"TRAC{window}:X? TRACE{trace}"\
                                                .format(window=window,trace=trace),
                                                datatype='f', container=np.array)

    def set_frequency_mask (self, frequency_offsets, thresholds, kind='upper', window=None):
        ''' Define the frequency-dependent trigger threshold values for a frequency mask trigger.

        :param array-like frequency_offsets: frequencies at which the mask is defined
        :param thresholds: trigger threshold at each frequency (same size as `frequency_offsets`)
        :param kind: either 'upper' or 'lower,' corresponding to a trigger on entering the upper trigger definition or on leaving the lower trigger definition
        :param window: The window number corresponding to the desired trigger setting (or self.state.default_window when window=None)
        :return: None
        '''
        if window is None:
            window = self.state.default_window
        if kind.lower() not in ('upper','lower'):
            raise ValueError('frequency mask is {} but must be "upper" or "lower"'\
                             .format(repr(kind)))


        flat = np.array([frequency_offsets, thresholds]).T.flatten()

        plist = ','.join(flat.astype(str))

        self.write("CALC{window}:MASK:{kind} {list}".format(window=window,kind=kind,list=plist))

    def get_frequency_mask (self, kind='upper', window=None):
        ''' Define the frequency-dependent trigger threshold values for a frequency mask trigger.

        :param kind: either 'upper' or 'lower,' corresponding to a trigger on entering the upper trigger definition or on leaving the lower trigger definition
        :param window: The window number corresponding to the desired trigger setting (or self.state.default_window when window=None)
        :return: A dictionary with keys "frequency_offsets" and "thresholds" and corresponding values (in Hz and dBm, respectively) of equal length
        '''

        if window is None:
            window = self.state.default_window
        if kind.lower() not in ('upper','lower'):
            raise ValueError('frequency mask is {} but must be "upper" or "lower"'\
                             .format(repr(kind)))

        plist = self.query("CALC{window}:MASK:{kind}?".format(window=window, kind=kind))
        plist = np.array(plist.split(',')).astype(np.float64)

        return {'frequency_offsets': plist[::2],
                'thresholds': plist[1::2]}