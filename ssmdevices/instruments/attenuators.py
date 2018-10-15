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
__all__ = ['MiniCircuitsRCDAT', 'MiniCircuitsRC4DAT']

from labbench import DotNetDevice
import ssmdevices.lib
import labbench as lb
import time,random

class MiniCircuitsRCBase(DotNetDevice):
    ''' Base class for MiniCircuits USB attenuators.
    
        This implementation calls the .NET drivers provided by the
        manufacturer instead of the recommended C DLL drivers in order to
        support 64-bit python.
    '''
    
    library  = ssmdevices.lib    # Must be a module
    dll_name = 'mcl_RUDAT64.dll'
    model_includes = ''
    
    class settings(DotNetDevice.settings):
        resource = lb.Unicode(None, help='Serial number of the USB device. Must be defined if more than one device is connected to the computer', allow_none=True)
    
    class state(DotNetDevice.state):
        model = lb.Unicode(read_only=True, cache=True, is_metadata=True)
        serial_number = lb.Unicode(read_only=True, cache=True, is_metadata=True)

    def connect (self):
        ''' Open the device resource.
        '''
        if self.dll is None:
            raise Exception('Minicircuits attenuator support currently requires pythonnet and windows')
            
        # Validate the input resource
        valid = self.list_available_devices()
        if self.settings.resource is None:
            if len(valid) == 0:
                raise ValueError('no MiniCircuits attenuators were detected on USB')
            elif len(valid) > 1:
                raise ValueError('more than one MiniCircuits USB attenuators are connected, specify one of '+repr(valid))
        else:
            if self.settings.resource not in valid:
                raise ValueError('specified serial number {} but only found {} on USB'\
                                 .format(repr(self.settings.resource),repr(valid)))
                
        self.backend = self.dll.USB_RUDAT()
#        if self.settings.resource == 1
        for retry in range(10):
            ret = self.backend.Connect(self.settings.resource)[0]
            if ret == 1:
                time.sleep(random.uniform(0,0.2))
                break
        else:
            raise Exception('Cannot connect to attenuator resource {}'.format(self.settings.resource))
        
        if self.model_includes and self.model_includes not in self.state.model:
            raise lb.DeviceException('attenuator model {model} does not include the expected {model_has} string'\
                                     .format(model=self.state.model,
                                             model_has=self.model_includes))

        self.logger.debug('Connected to {model} attenuator, SN#{sn}'\
                          .format(model=self.state.model,
                                  sn=self.state.serial_number))

    def disconnect(self):
        ''' Release the attenuator hardware resource via the driver DLL.
        '''
        self.backend.Disconnect()

    @classmethod
    def list_available_devices(cls):
        ''' Return a list of valid resource strings of MiniCircuitsRCDAT and
            MiniCircuitsRC4DAT devices that are found on this computer.
        '''
        # Force the dll to import if no devices have been imported yet
        if not hasattr(cls, '__dll__'):
            cls()
        count, response = cls.__dll__.USB_RUDAT().Get_Available_SN_List('')
        if count > 0:
            return response.split(' ')
        else:
            return []

    @state.model.getter
    def __ (self):
        self._validate_connection()
        return 'MiniCircuits ' + self.backend.Read_ModelName('')[1]
    
    @state.serial_number.getter
    def __ (self):
        self._validate_connection()
        return self.backend.Read_SN('')[1]
    
    def _validate_connection(self):
        if self.backend.GetUSBConnectionStatus() != 1:
            raise lb.DeviceStateError('USB device unexpectedly disconnected')

class MiniCircuitsRCDAT(MiniCircuitsRCBase):
    ''' A digitally-controlled single-channel solid-state attenuator.
    '''

    model_includes = 'RCDAT'
    
    class state(MiniCircuitsRCBase.state):
        attenuation          = lb.Float(min=0, max=115, step=0.25)
        

    @state.attenuation.getter
    def __ (self):
        self._validate_connection()
        ret = self.backend.Read_Att(0)[1]
        self.logger.debug('got attenuation {} dB'.format(ret))
        return ret

    @state.attenuation.setter
    def __ (self, value):
        self._validate_connection()
        self.logger.debug('set attenuation {} dB'.format(value))
        self.backend.SetAttenuation(value)

class MiniCircuitsRC4DAT(MiniCircuitsRCBase):
    ''' A digitally-controlled 4-channel solid-state attenuator.
    '''

    model_includes = 'RC4DAT'

    class settings(DotNetDevice.settings):
        resource = lb.Unicode(None, help='Serial number of the USB device. Must be defined if more than one device is connected to the computer', allow_none=True)

    class state(MiniCircuitsRCBase.state):
        attenuation1 = lb.Float(min=0, max=115, step=0.25, command=1)
        attenuation2 = lb.Float(min=0, max=115, step=0.25, command=2)
        attenuation3 = lb.Float(min=0, max=115, step=0.25, command=3)
        attenuation4 = lb.Float(min=0, max=115, step=0.25, command=4)


    @state.getter
    def __ (self, trait):
        self._validate_connection()
        ret = self.backend.ReadChannelAtt(trait.command)
        self.logger.debug('got attenuation{} {} dB'.format(trait.command,ret))
        return ret    

    @state.setter
    def __ (self, trait, value):
        self._validate_connection()
        self.logger.debug('set attenuation{} {} dB'.format(trait.command,value))
        self.backend.SetChannelAtt(trait.command, value)

if __name__ == '__main__':
    lb.show_messages('debug')
    with MiniCircuitsRC4DAT('11711260039') as atten:
        print(atten.state.model)
        atten.state.attenuation1 = 28.
        print(atten.state.attenuation1)