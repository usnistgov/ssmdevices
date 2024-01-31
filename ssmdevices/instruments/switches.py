__all__ = ['MiniCircuitsUSBSwitch']

from labbench import paramattr as attr

if __name__ == '__main__':
    # allow relative imports for the __main__ block below
    from _minicircuits_usb import SwitchAttenuatorBase
else:
    from ._minicircuits_usb import SwitchAttenuatorBase

__all__ = ['MiniCircuitsUSBSwitch']


class MiniCircuitsUSBSwitch(SwitchAttenuatorBase):
    # Mini-Circuits USB-SP4T-63
    _PID = 0x22

    @attr.property.int(min=1, max=4)
    def port(self):
        """the RF port connected to the COM port"""
        CMD_GET_SWITCH_PORT = 15
        d = self._cmd(CMD_GET_SWITCH_PORT)
        port = d[1]
        return port

    @port.setter
    def _(self, port):
        """the RF port connected to the COM port"""
        if port not in (1, 2, 3, 4):
            raise ValueError('Invalid switch port: %s' % port)
        self._cmd(port)
