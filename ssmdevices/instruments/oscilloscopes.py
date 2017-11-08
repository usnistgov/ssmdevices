__all__ = ['RigolOscilloscope']

import labbench as lb
from labbench.visa import VISADevice
import pandas as pd

class RigolOscilloscope(lb.VISADevice):
    class state(lb.VISADevice.state):
        time_offset        = lb.Float (command=':TIM:OFFS', label='s')
        time_scale         = lb.Float (command=':TIM:SCAL', label='s')
    
    def connect (self, horizontal=False):
        super(RigolOscilloscope,self).connect()
        self.write(':WAVeform:FORMat ASCii')
        
    def fetch (self):
        return self.backend.query_asci_values(':WAV:DATA?')
    
    def fetch_rms (self):
        return float(self.backend.query(':MEAS:VRMS?').rstrip().lstrip())