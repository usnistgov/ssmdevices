from __future__ import print_function
from builtins import str,range
import os,pyvisa,datetime
import numpy as np

__all__ = ['RohdeSchwarzFSW26Base',
           'RohdeSchwarzFSW26SpectrumAnalyzer',
           'RohdeSchwarzFSW26IQAnalyzer',
           'RohdeSchwarzFSW26LTEAnalyzer',
           'RohdeSchwarzFSW26RealTime']

from labbench import Bool, CaselessStrEnum, Int, Float
from labbench.visa import VISADevice
import pandas as pd

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
    
        initiate_continuous     = Bool      (command='INIT:CONT')
    
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
        
        channel_type            = CaselessStrEnum (command='INST', values=['SAN','IQ','RTIM'])
        format                  = CaselessStrEnum (command='FORM', values=['ASC,0','REAL,32','REAL,64', 'REAL,16'])
        sweep_points            = Int       (command='SWE:POIN', min=1, max=100001)
         
        display_update          = Bool      (command='SYST:DISP:UPD')
    

    def verify_channel_type (self):
        if self.expect_channel_type is not None and self.state.channel_type != self.expect_channel_type:
            raise Exception('{} expects {} mode, but insrument mode is {}'\
                            .format(type(self).__name__, self.expect_channel_type, self.state.channel_type))        

    def connect (self):
        super().connect()
        self.state.format = 'REAL,32'

    def save_state (self, path):
        ''' Save current state of the device to the default directory.
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param num: state number in the saved filename
            :type num: int
        
        '''
        self.write('MMEMory:STORe:STATe 1,"{}""'.format(path))
    
    def load_state(self, path):
        ''' Loads a previously saved state file in the instrument
        
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param num: state number in the saved filename
            :type num: int
        '''
#        print "Loading state"
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
        
    def trigger_single (self):
        ''' Trigger once.
        '''
        self.state.initiate_continuous = False        
        self.write('INIT')
        self.wait()

    def autolevel (self):
        ''' Run the signal analyzer autolevel tool.
        '''

        self.write("ADJ:LEV") #see if this is enough, or if we need something more detailed
   
    def fetch_horizontal (self, trace=None):
        return self.backend.query_binary_values("TRAC:DATA:X? TRACE{trace}".format(trace=trace or ''))

    def fetch_trace(self, trace=None, horizontal=False):
        ''' Get and return the current trace data.
        
            If necessary, we can read the count, set count to 1, read, adjust level
            then set the count back, and read again like this:

            ::
                count = inst.query("SENSE:SWEEP:COUNT?")
                self.write("SENSE:SWEEP:COUNT 1")
                
            :return: x and y data formatted as np.array([xdata,ydata])
            
            :rtype: np.array
        '''
        if hasattr(trace, '__iter__'):
            return pd.concat([self.fetch_trace(t,horizontal=horizontal) for t in trace])
        
        if horizontal:
            index = self.fetch_horizontal(trace)
            values = self.backend.query_binary_values("TRAC:DATA? TRACE{trace}".format(trace=trace or ''),\
                                                      container=pd.Series, datatype='d')
            name = 'Trace {}'.format(trace)
            return pd.DataFrame(values.values, columns=[name], index=index)
        else:
            return self.backend.query_binary_values("TRAC:DATA? TRACE{trace}".format(trace=trace or ''),\
                                                    container=pd.Series, datatype='d')

    def fetch_timestamps (self, all=True, trace=None):
        scope = 'ALL' if all else 'CURR'
        timestamps = self.backend.query_ascii_values(r'CALC{trace}:SGR:TST:DATA? {scope}'\
                                                      .format(trace=trace or '', scope=scope),\
                                                     container=np.array)
        timestamps = timestamps.reshape((timestamps.shape[0]//4,4))[:,:2]
        ret = timestamps[:,0] + 1e-9*timestamps[:,1]
        if not all:
            return ret[0]
        else:
            return ret    

    def fetch_spectrogram (self, freqs='exact', timestamps='exact', trace=None):
        '''
        '''
        if timestamps == 'fast':
            sweep_time = self.state.sweep_time_trace2
            ts0 = self.fetch_timestamps(all=False, trace=trace)
            dt0=datetime.datetime.fromtimestamp(ts0)
        elif timestamps == 'exact':
            t = self.fetch_timestamps(all=True, trace=trace)
        elif timestamps == None:
            t = None
        else:
            raise ValueError("timestamps argument must be 'fast', 'exact', or None")

    
        if freqs == 'fast':
            fc = self.state.frequency_center
            fsamp = self.state.iq_sample_rate      
            Nfreqs = self.state.sweep_points
            f_ = fc+np.linspace(-fsamp*(1.-1./Nfreqs)/2,+fsamp*(1.-1./Nfreqs)/2, Nfreqs)
        if freqs == 'exact':
            f_  = self.fetch_horizontal(trace)
            Nfreqs = len(f_)
        elif freqs == None:
            f_ = None
            Nfreqs = self.state.sweep_points

        self.backend.read_termination, old_read_term = None, self.backend.read_termination
        self.backend.write('TRAC{trace}:DATA? SPEC'.format(trace=trace))
        
        # This is very hacky, because for some reason performance via
        # the pyvisa functions like .write and .query was poor
        raw,_ = self.backend.visalib.read(self.backend.session, 2)
        digits=int(raw.decode('ascii')[1])
        raw,_ = self.backend.visalib.read(self.backend.session, digits)
        N=int(raw.decode('ascii'))
        raw,_ = self.backend.visalib.read(self.backend.session, N)
        self.backend.read_termination = old_read_term
        data = np.frombuffer(raw, np.float32)
        data = data.reshape((data.size//Nfreqs,Nfreqs))
        
        if timestamps == 'fast':
            t = dt0+pd.to_timedelta(sweep_time*1e9*np.arange(data.shape[0]), unit='ns')            
        return pd.DataFrame(data[::-1], columns=f_, index=t)
    
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
        iq_simple_enabled     = Bool      (command='CALC:IQ')
        iq_evaluation_enabled = Bool      (command='CALC:IQ:EVAL')
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
            
    def fetch_horizontal (self, window=2, trace=1):
        return self.backend.query_binary_values(r"TRAC{window}:X? TRACE{trace}"\
                                                .format(window=window,trace=trace),
                                                datatype='f', container=np.array)

if __name__ == '__main__':
    import labbench as lb
    lb.log_to_screen('DEBUG')

    with RohdeSchwarzFSW26IQAnalyzer('TCPIP::TILSIT::HISLIP0::INSTR') as fsw:
#        fsw.state.iq_simple_enabled = True
#        fsw.wait()
#        fsw.state.iq_mode = 'IQ'
        fsw.state.iq_record_length = 80*1000*1000
        fsw.state.iq_format = 'RIM'        
        fsw.trigger_single()
        fsw.wait()

        # Give the timeout a long enough enough to complete
        fsw.link.timeout = 1000*60 # in ms
        with fsw.overlap_and_block:
            fsw.store_trace(r'C:\test.iq.tar')
        print('Done!')