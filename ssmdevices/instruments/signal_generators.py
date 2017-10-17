# -*- coding: utf-8 -*-

"""
.. This software was developed by employees of the National Institute of
.. Standards and Technology (NIST), an agency of the Federal Government. Pursuant
.. to title 17 United States Code Section 105, works of NIST employees are not
.. subject to copyright protection in the United States and are considered to be
.. in the public domain. Permission to freely use, copy, modify, and distribute
.. this software and its documentation without fee is hereby granted, provided
.. that this notice and disclaimer of warranty appears in all copies.

.. THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND, EITHER
.. EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY
.. THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF
.. MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND FREEDOM FROM INFRINGEMENT,
.. AND ANY WARRANTY THAT THE DOCUMENTATION WILL CONFORM TO THE SOFTWARE, OR ANY
.. WARRANTY THAT THE SOFTWARE WILL BE ERROR FREE. IN NO EVENT SHALL NASA BE LIABLE
.. FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR
.. CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED
.. WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR
.. OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR
.. OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE
.. RESULTS OF, OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.

.. Distributions of NIST software should also include copyright and licensing
.. statements of any third-party software that are legally bundled with the code
.. in compliance with the conditions of those licenses.
"""
''' Driver classes for signal generators.
:author: Ryan Jacobs <ryan.jacobs@nist.gov>, Aziz Kord <aziz.kord@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
Paul.Blanchard <paul.blanchard@nist.gov>
'''
from __future__ import print_function

from labbench import Bool, Bytes, EnumBytes, Int, Float
from labbench.visa import VISADevice
import pandas as pd
__all__ = ['RohdeSchwarzSMW200A']

class RohdeSchwarzSMW200A(VISADevice):
    class state(VISADevice.state):
#        frequency = FLoat 
        frequency_baseband        = Float     (command=':freq',  min=2e3, max=26.5e9, step=1e3, label='Hz')
        power_out                 = Float     (command=':pow',  min=-60, max=20, step=1e-2, label='dBm')
        rf_enable                 = Bool      (command ='OUTP')
        
        
    def save_state(self, FileName, num="4"):
        ''' Save current state of the device to the default directory.
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param num: state number in the saved filename
            :type num: int
        
        '''
        print("Saving State")
        self.write('MMEMory:STORe:STATe {},"{}.savrcltxt"'.format(num,FileName))
        print("Complete")
    
    def load_state(self, FileName, opc=False, num="4"):
        ''' Loads a previously saved state file in the instrument
        
            :param FileName: state file location on the instrument
            :type FileName: string
            
            :param opc: set the VISA op complete flag?
            :type opc: bool
            
            :param num: state number in the saved filename
            :type num: int
        '''
#        print "Loading state"
        cmd = "MMEM:LOAD:STAT {},'{}.savrcltxt';*RCL {}".format(num,FileName,num)
        self.write(cmd, opc=opc)

#        # Activates the memory state
#        self.write("*RCL {}".format(num))
#        print "Complete"
    
    @property
    def rf_output_enable(self):
        ''' Get or set RF enable state getter
        '''
        return bool(int(self.inst.query('OUTP?')))
    
    @rf_output_enable.setter
    def rf_output_enable(self, state):
        ''' Enables or disables RF output of device
            Options are "ON", "1", 'true', True, or a non-zero number to enable.
            Any other value will disable.
        '''
        valid_on_strings = 'on', '1', 'true'
        
        if isinstance(state, str):
            state = int(state.lower() in valid_on_strings)
        else:
            state = int(bool(state))
        
        self.inst.write("OUTP {}".format(state))
        
    @property
    def rf_output_power (self):
        ''' Get or set RF output power level
        '''
#        return float(self.inst.query(':pow?',timeout=5))
        return float(self.query(':pow?',timeout=5))
        
    @rf_output_power.setter
    def rf_output_power (self, level_dBm):
        self.inst.write(':pow {}'.format(level_dBm))
    
    @property
    def rf_output_freq (self):
        """ Get or set RF LO frequency
        """
        return float(self.query(':freq?',timeout=5))

    @rf_output_freq.setter
    def rf_output_freq (self, freq_Hz):
        self.inst.write(':freq {}'.format(freq_Hz))
        
        

# Example code works nicely in this if statement, which only runs if we're
# running this file (not if it's being imported by another file :))
if __name__ == '__main__':
    import visa
    rm = visa.ResourceManager('@ni')
    siggen = RohdeSchwarzSMW200A("USB::2733::146::102240::0::INSTR", rm)