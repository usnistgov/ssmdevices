# -*- coding: utf-8 -*-
''' Driver classes for signal generators.
:author: Ryan Jacobs <ryan.jacobs@nist.gov>, Aziz Kord <aziz.kord@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
Paul.Blanchard <paul.blanchard@nist.gov>
'''

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from builtins import int
from future import standard_library
standard_library.install_aliases()

import labbench as lb

__all__ = ['RohdeSchwarzSMW200A']

class RohdeSchwarzSMW200A(lb.VISADevice):
    class state(lb.VISADevice.state):
#        frequency = FLoat 
        frequency_center        = lb.Float     (command=':freq',  min=2e3, max=26.5e9, step=1e3, label='Hz')
        rf_output_power         = lb.Float     (command=':pow',  min=-145, max=20, step=1e-2, label='dBm')
        rf_output_enable        = lb.Bool      (command ='OUTP', remap={False: '0', True: '1'})
        

    def save_state(self, FileName, num="4"):
        ''' Save current state of the device to the default directory.
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param num: state number in the saved filename
            :type num: int
        
        '''
        self.write('MMEMory:STORe:STATe {},"{}.savrcltxt"'.format(num,FileName))
    
    def load_state(self, FileName, opc=False, num="4"):
        ''' Loads a previously saved state file in the instrument
        
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param opc: set the VISA op complete flag?
            :type opc: bool
            
            :param num: state number in the saved filename
            :type num: int
        '''
        cmd = "MMEM:LOAD:STAT {},'{}.savrcltxt';*RCL {}".format(num,FileName,num)
        self.write(cmd, opc=opc)

# Example code works nicely in this if statement, which only runs if we're
# running this file (not if it's being imported by another file :))
if __name__ == '__main__':
    with RohdeSchwarzSMW200A("USB::2733::146::102240::0::INSTR") as siggen:
        siggen.state.rf_output_enable = True