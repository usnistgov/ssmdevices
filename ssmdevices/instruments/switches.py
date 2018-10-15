# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
__all__ = ['MiniCircuitsUSBSwitch']

from labbench import DotNetDevice
import ssmdevices.lib
import labbench as lb

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

    class state(DotNetDevice.state):
        port = lb.Int(min=1)

    def connect (self):
        ''' Open the device resource.
        '''
        if self.dll is None:
            raise Exception('Minicircuits attenuator support currently requires pythonnet and windows')
        # The USB_Digital_Switch namespace is given in the minicircuits docs
        self.backend = self.dll.USB_Digital_Switch()
        if self.backend.Connect(self.settings.resource)[0] != 1:
            raise Exception('Cannot connect to USB switch resource {}'.format(self.settings.resource))

    def disconnect(self):
        ''' Release the attenuator hardware resource via the driver DLL.
        '''
        try:
            self.backend.Disconnect()
        except:
            pass

    @state.port.getter
    def _ (self):
        ret = self.backend.Get_SP4T_State()
        self.logger.debug('got switch state {}'.format(repr(ret)))
        return ret

    @state.port.setter
    def _ (self, value):
        self.logger.debug('set switch state {}'.format(repr(value)))
        self.backend.Set_SP4T_COM_To(value)
