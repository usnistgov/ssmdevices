__all__ = ['RigolOscilloscope']

import labbench as lb

class RigolOscilloscope(lb.VISADevice):
    time_offset = lb.property.float(key=':TIM:OFFS', label='s')
    time_scale = lb.property.float(key=':TIM:SCAL', label='s')
    
    def open (self, horizontal=False):
        self.write(':WAVeform:FORMat ASCii')
        
    def fetch (self):
        return self.backend.query_asci_values(':WAV:DATA?')
    
    def fetch_rms (self):
        return float(self.backend.query(':MEAS:VRMS?').rstrip().lstrip())