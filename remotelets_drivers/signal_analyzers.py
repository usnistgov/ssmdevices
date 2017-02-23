__all__ = ['RohdeSchwarzFSW26']

from remotelets import Bool, Bytes, EnumBytes, Int, Float
from remotelets.visa import SCPI, Remotelets, Instrument
import pandas as pd
import numpy as np

class RohdeSchwarzFSW26(Instrument):
    class state(Remotelets):
        frequency_center        = SCPI(Float(min=2, max=26.5e9, step=1e-9, label='Hz'), 'FREQ:CENT')
        frequency_span          = SCPI(Float(min=2, max=26.5e9, step=1e-9, label='Hz'), 'FREQ:SPAN')
        frequency_start         = SCPI(Float(min=2, max=26.5e9, step=1e-9, label='Hz'), 'FREQ:START')
        frequency_stop          = SCPI(Float(min=2, max=26.5e9, step=1e-9, label='Hz'), 'FREQ:STOP') 
    
        initiate_continuous     = SCPI(Bool(), 'INIT:CONT')
    
        reference_level         = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC1:Y:RLEV')
        reference_level_trace2  = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC2:Y:RLEV')
        reference_level_trace3  = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC3:Y:RLEV')
        reference_level_trace4  = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC4:Y:RLEV')
        reference_level_trace5  = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC5:Y:RLEV')
        reference_level_trace6  = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC6:Y:RLEV')
        
        amplitude_offset        = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC1:Y:RLEV:OFFS')
        amplitude_offset_trace2 = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC2:Y:RLEV:OFFS')
        amplitude_offset_trace3 = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC3:Y:RLEV:OFFS')
        amplitude_offset_trace4 = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC4:Y:RLEV:OFFS')
        amplitude_offset_trace5 = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC5:Y:RLEV:OFFS')
        amplitude_offset_trace6 = SCPI(Float(step=1e-3,label='dB'), 'DISP:TRAC6:Y:RLEV:OFFS')

    
    def save_state (self, FileName, num="1"):
        ''' Save current state of the device to the default directory.
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param num: state number in the saved filename
            :type num: int
        
        '''
        self.write('MMEMory:STORe:STATe {},"{}""'.format(num,FileName))
    
    def load_state(self, FileName, num="1"):
        ''' Loads a previously saved state file in the instrument
        
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param num: state number in the saved filename
            :type num: int
        '''
#        print "Loading state"
        cmd = "MMEM:LOAD:STAT {},'{}'".format(num,FileName)
        self.write(cmd)
        
    def trigger_single (self):
        ''' Trigger once.
        '''
        self.write('INIT')

    def autolevel (self):
        ''' Run the signal analyzer autolevel tool.
        '''
        
        self.write("ADJ:LEV") #see if this is enough, or if we need something more detailed
   
    def fetch_horizontal (self, trace=1):
        response = self.query("TRAC:DATA:X? TRACE{trace}".format(trace=trace))
        return pd.to_numeric(pd.Series(response.split(',')))

    def fetch_trace(self, trace=1, horizontal=False):
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
            values = self.link.query_ascii_values("TRAC:DATA? TRACE{trace}".format(trace=trace), container=pd.Series)
            name = 'Trace {}'.format(trace)
            return pd.DataFrame(values.values, columns=[name], index=index)
        else:
            return self.link.query_ascii_values("TRAC:DATA? TRACE{trace}".format(trace=trace), container=pd.Series)
        
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
    
    def get_marker_enables(self):
        enable_cmd = 'CALC:MARK{}:STATE?'
        bw_cmd = 'CALC:MARK{}:FUNC:BPOW:STATE?'

        markers = range(1,17)
        states = [[self.query(enable_cmd.format(m)),
                   self.query(bw_cmd.format(m))] for m in markers]

        df = pd.DataFrame(states, columns=['Marker', 'Band'],
                          index=markers).astype(int).astype(bool)
        df.index.name = 'Marker'
        
        return df
    
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

if __name__ == '__main__':
#    import remotelets as rlts
#    rlts.log_to_screen('DEBUG')
    
    with RohdeSchwarzFSW26('TCPIP::TILSIT::HISLIP0::INSTR') as fsw:
#        fsw.set_marker_position(5,1.58e9)
#        fsw.trigger_single()
#        fsw.wait()
#        print fsw.get_marker_power_table()
        df = fsw.fetch_trace([1,2,4],horizontal=True)
    df.plot()