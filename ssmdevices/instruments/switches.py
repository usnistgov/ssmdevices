# -*- coding: utf-8 -*-

__all__ = ['MiniCircuitsUSBSwitch']

from labbench import DotNetDevice
import ssmdevices.lib
import labbench as lb

if __name__ == '__main__':
    # allow relative imports for the __main__ block below
    from _minicircuits_usb import SwitchAttenuatorBase
else:
    from ._minicircuits_usb import SwitchAttenuatorBase

__all__ = ['MiniCircuitsUSBSwitch']

class MiniCircuitsUSBSwitch(DotNetDevice):
    ''' A digitally controlled solid-state switch.

        This implementation calls the .NET drivers provided by the
        manufacturer instead of the recommended C DLL drivers in order to
        support 64-bit python.

        The .NET documentation is located here:
        https://www.minicircuits.com/softwaredownload/Prog_Manual-Solid_State_Switch.pdf
    '''

    library  = ssmdevices.lib    # Must be a module
    dll_name = 'mcl_SolidStateSwitch64.dll'

    def open (self):
        ''' Open the device resource.
        '''
        if self.dll is None:
            raise Exception('Minicircuits attenuator support currently requires pythonnet and windows')
        # The USB_Digital_Switch namespace is given in the minicircuits docs
        self.backend = self.dll.USB_Digital_Switch()
        if self.backend.Connect(self.settings.resource)[0] != 1:
            raise Exception('Cannot connect to USB switch resource {}'.format(self.settings.resource))

    def close(self):
        ''' Release the attenuator hardware resource via the driver DLL.
        '''
        try:
            self.backend.Disconnect()
        except:
            pass

    @lb.Int(min=1)
    def port(self):
        ret = self.backend.Get_SP4T_State()
        self.logger.debug('got switch state {}'.format(repr(ret)))
        return ret
    @port
    def port(self, value):
        self.logger.debug('set switch state {}'.format(repr(value)))
        self.backend.Set_SP4T_COM_To(value)


# TODO: Test this and replace the above
#class MiniCircuitsUSBSwitch(SwitchAttenuatorBase):
#    # Mini-Circuits USB-SP4T-63
#    PID = 0x22
#    
#    @lb.Int(min=1, max=4)
#    def port(self, port):
#        """ the RF port connected to COM port indexed from 1 """
#        if port not in (1, 2, 3, 4):
#            raise ValueError("Invalid switch port: %s" % port)
#        self._cmd(port)
#
#    def port(self):
#        CMD_GET_SWITCH_PORT = 15
#        d = self._cmd(CMD_GET_SWITCH_PORT)
#        port = d[1]
#        return port