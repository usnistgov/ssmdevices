# -*- coding: utf-8 -*-

__all__ = ['MiniCircuitsRCDAT', 'MiniCircuitsRC4DAT']

from labbench import DotNetDevice
import ssmdevices.lib
import labbench as lb
import time,random
from . import minicircuits

class MiniCircuitsRCDAT(minicircuits.SingleChannelAttenuator):
    pass

#class MiniCircuitsRC4DAT(minicircuits.FourChannelAttenuator):
#    pass

class MiniCircuitsRC4DAT(DotNetDevice):
    ''' Base class for MiniCircuits USB attenuators.
    
        This implementation calls the .NET drivers provided by the
        manufacturer instead of the recommended C DLL drivers in order to
        support 64-bit python.
    '''
    
    library  = ssmdevices.lib    # Must be a module
    dll_name = 'mcl_RUDAT64.dll'
    model_includes = ''
    
    resource: lb.Unicode(None,
                         help='Serial number of the USB device. Must be defined if more than one device is connected to the computer', allow_none=True)

    def open (self):
        ''' Open the device resource.
        '''
        @lb.retry(ConnectionError, 10, delay=0.25)
        def do_connect():
            self.backend = self.dll.USB_RUDAT()
    #        if self.settings.resource == 1
            for retry in range(10):
                ret = self.backend.Connect(self.settings.resource)[0]
                if ret == 1:
                    time.sleep(random.uniform(0,0.2))
                    break
            else:
                time.sleep(0.25)
                raise ConnectionError('Cannot connect to attenuator resource {}'.format(self.settings.resource))
            
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
                
        do_connect()
        if self.model_includes and self.model_includes not in self.model:
            raise lb.DeviceException('attenuator model {model} does not include the expected {model_has} string'\
                                     .format(model=self.model,
                                             model_has=self.model_includes))

        self.logger.debug('Connected to {model} attenuator, SN#{sn}'\
                          .format(model=self.model,
                                  sn=self.serial_number))

    def _validate_connection(self):
        if self.backend.GetUSBConnectionStatus() != 1:
            raise lb.DeviceStateError('USB device unexpectedly disconnected')

    def close(self):
        ''' Release the attenuator hardware resource via the driver DLL.
        '''
        self.backend.Disconnect()

    @classmethod
    def list_available_devices(cls, inst=None):
        ''' Return a list of valid resource strings of MiniCircuitsRCDAT and
            MiniCircuitsRC4DAT devices that are found on this computer.
            
            If inst is not None, it should be a MiniCircuitsRCBase instance.
            In this case its backend will be used instead of temporarily
            making a new one.
        '''
        lb.logger.debug('checking available devices')
        # Force the dll to import if no devices have been imported yet
        if inst is None:
            if not hasattr(cls, 'dll'):
                cls.__imports__()
            backend = cls.dll.USB_RUDAT()
        else:
            backend = inst.backend

        count, response = backend.Get_Available_SN_List('')
        
        lb.logger.debug('response was {}'.format(response))
        if count > 0:
            return response.split(' ')
        else:
            return []

    @lb.Unicode(settable=False, cache=True)
    def model(self):
        self._validate_connection()
        return 'MiniCircuits ' + self.backend.Read_ModelName('')[1]
    
    @lb.Unicode(settable=False, cache=True)
    def serial_number(self):
        self._validate_connection()
        return self.backend.Read_SN('')[1]

    attenuation1 = lb.Float(min=0, max=115, step=0.25, key=1)
    attenuation2 = lb.Float(min=0, max=115, step=0.25, key=2)
    attenuation3 = lb.Float(min=0, max=115, step=0.25, key=3)
    attenuation4 = lb.Float(min=0, max=115, step=0.25, key=4)

    def __get_by_key__ (self, key, name):
        self._validate_connection()
        ret = self.backend.ReadChannelAtt(key)
        self.logger.debug(f'got attenuation {key} {ret} dB')
        return ret    

    def __set_state_(self, key, name, value):
        self._validate_connection()
        self.logger.debug(f'set attenuation {key} {value} dB')
        self.backend.SetChannelAtt(key, value)

if __name__ == '__main__':
    lb.show_messages('info')
    for i in range(1000):
        lb.logger.warning(str(i))
        atten = MiniCircuitsRCDAT('11604210014')
        atten2 = MiniCircuitsRCDAT('11604210008')
        with atten,atten2:
            atten.attenuation = 63.
            lb.logger.info(str(atten.attenuation))