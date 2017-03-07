# -*- coding: utf-8 -*-
"""
Created on Tue Mar 07 14:38:10 2017

@author: dkuester
"""

__all__ = ['MiniCircuitsRCDAT']

from labbench.dotnet import import_dotnet
import ssmdevices

try:
    dll = import_dotnet('ssmdevices/lib/mcl_RUDAT64.dll',
                        path=['.','..',ssmdevices])
except Exception,e:
    print 'ssmdevices: could not load dll; no support for MiniCircuits variable attenuators'

else:
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
            
            @attenuation.getter
            def attenuation(self, device):
                return device.driver.Read_Att(0)[1]
        
            @attenuation.setter
            def attenuation(self, device, value):
                device.driver.SetAttenuation(value)
           
        def connect (self):
            ''' Open the device resource.
            '''
            self.driver = dll.USB_RUDAT()
            if self.driver.Connect(self.resource)[0] != 1:
                raise Exception('Cannot connect to attenuator resource {}'.format(self.resource))
            self.state.connected = True
    
        def disconnect(self):
            ''' Release the attenuator hardware resource via the driver DLL.
            '''
            try:
                self.driver.Disconnect()
            except:
                self.state.connected = False
            self.driver = None