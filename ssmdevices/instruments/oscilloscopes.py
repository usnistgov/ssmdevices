from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import super
from future import standard_library
standard_library.install_aliases()
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