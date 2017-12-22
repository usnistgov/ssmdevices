# -*- coding: utf-8 -*-
"""
Created on Tue Mar 07 14:38:10 2017

@author: dkuester
"""
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
__all__ = ['MiniCircuitsRCDAT']

from labbench.dotnet import DotNetDevice
import ssmdevices.lib
import labbench as core

class MiniCircuitsRCDAT(DotNetDevice):
    ''' A digitally controlled, 0 to 110 dB variable attenuator.
    
        This implementation calls the .NET drivers provided by the
        manufacturer instead of the recommended C DLL drivers in order to
        support 64-bit python.
    '''
    
    library  = ssmdevices.lib    # Must be a module
    dll_name = 'mcl_RUDAT64.dll'
    
    class state(DotNetDevice.state):
        attenuation = core.Float(min=0, max=115, step=0.25)

    def connect (self):
        ''' Open the device resource.
        '''
        super().connect()
        self.backend = self.dll.USB_RUDAT()
        if self.backend.Connect(self.resource)[0] != 1:
            raise Exception('Cannot connect to attenuator resource {}'.format(self.resource))

    def disconnect(self):
        ''' Release the attenuator hardware resource via the driver DLL.
        '''
        try:
            self.backend.Disconnect()
        except:
            pass
        
    @state.attenuation.getter
    def _ (self):
        return self.backend.Read_Att(0)[1]

    @state.attenuation.setter
    def _ (self, value):
        self.backend.SetAttenuation(value)