# -*- coding: utf-8 -*-
"""
Created on Tue Mar 07 14:38:10 2017

@author: dkuester
"""

#__all__ = ['MiniCircuitsRCDAT']

from labbench.dotnet import import_dotnet
import ssmdevices.lib

import logging
logger = logging.getLogger('labbench')

try:
    dll = import_dotnet('mcl_RUDAT64.dll', ssmdevices.lib)
except Exception,e:
    print logger.warn('could not load mcl_RUDAT64.dll; MiniCircuits variable attenuator driver will not work')
    
import labbench as core

class MiniCircuitsRCDAT(core.Device):
    ''' A digitally controlled, 0 to 110 dB variable attenuator.
    
        Ensure that the windows DLL driver is installed by copying mcl_RUDAT64.dll from
        the manufacturer website or install CD into C:\Windows\SysWOW64\.
 
        This implementation calls the .NET drivers provided by the manufacturer
        instead of the C DLL drivers recommended by the manufacturer in order
        to support 64-bit python.
    '''
    
    class state(core.Device.state):
        attenuation = core.Float(min=0, max=115, step=0.25)
               
    def connect (self):
        ''' Open the device resource.
        '''
        backend = dll.USB_RUDAT()
        if backend.Connect(self.resource)[0] != 1:
            raise Exception('Cannot connect to attenuator resource {}'.format(self.resource))
        return backend

    def disconnect(self):
        ''' Release the attenuator hardware resource via the driver DLL.
        '''
        self.backend.Disconnect()
        
    @state.attenuation.getter
    def _ (self):
        return self.backend.Read_Att(0)[1]

    @state.attenuation.setter
    def _ (self, value):
        self.backend.SetAttenuation(value)