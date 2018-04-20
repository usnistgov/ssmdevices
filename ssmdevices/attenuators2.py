# -*- coding: utf-8 -*-
"""
Created on Fri Apr 20 16:06:39 2018

@author: ynm5
"""

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
__all__ = ['MiniCircuitsRCDAT2']

from labbench import DotNetDevice
import ssmdevices.lib
import labbench as core

class MiniCircuitsRCDAT2(DotNetDevice):
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
        if self.dll is None:
            raise Exception('Minicircuits attenuator support currently requires pythonnet and windows')
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
    #def _ (self,channel):
        #return self.backend.Read_Att(0)[1]
    def Read_att(self,channel):        
        return self.backend.ReadChannelAtt(channel)

    @state.attenuation.setter
    #def _ (self, channel,value):
        #self.backend.SetAttenuation(value)
    def Set_att(self,channel,value):    
        self.backend.SetChannelAtt(channel,value)        
'''        

      
    @state.attenuation.getter
    def _ (self):
        ret = self.backend.Read_Att(0)[1]
        self.logger.debug('got attenuation {} dB'.format(ret))
        return ret

    @state.attenuation.setter
    def _ (self, value):
        self.logger.debug('set attenuation {} dB'.format(value))
        self.backend.SetAttenuation(value)
'''