import labbench as lb
from labbench import paramattr as attr

__all__ = ['RigolDP800Series']


class dp800_property_adapter(attr.visa_keying):
    def get(self, device: lb.Device, scpi_key: str, trait_name=None):
        """This instrument expects keys to have syntax ":COMMAND? PARAM",
        instead of ":COMMAND PARAM?" as implemented in lb.VISADevice.

        Insert the "?" in the appropriate place here.
        """
        if ' ' in scpi_key:
            key = scpi_key.replace(' ', '? ', 1)
        else:
            key = scpi_key + '?'
        return device.query(key)

    def set(self, device: lb.Device, scpi_key: str, value, trait_name=None):
        """This instrument expects sets to have syntax :COMMAND PARAM,VALUE
        instead of :COMMAND attr.VALUE. as implemented in lb.VISADevice.

        Implement this behavior here.
        """
        if ' ' in scpi_key:
            key = f'{scpi_key},{value}'
        else:
            key = f'{scpi_key} {value}'
        return device.write(key.rstrip())


@dp800_property_adapter(remap={True: 'ON', False: 'OFF'})
class RigolDP800Series(lb.VISADevice):
    # properties accept the "key" argument and/or decorators for custom implementation
    enable1 = attr.property.bool(key=':OUTP CH1', help='enable channel 1 output')
    enable2 = attr.property.bool(key=':OUTP CH2', help='enable channel 2 output')
    enable3 = attr.property.bool(key=':OUTP CH3', help='enable channel 3 output')

    voltage_setting1 = attr.property.float(
        key=':SOUR1:VOLT', help='output voltage setting on channel 1'
    )
    voltage_setting2 = attr.property.float(
        key=':SOUR2:VOLT', help='output voltage setting on channel 2'
    )
    voltage_setting3 = attr.property.float(
        key=':SOUR3:VOLT', help='output voltage setting on channel 3'
    )

    voltage1 = attr.property.float(
        key=':MEAS:VOLT CH1', sets=False, help='output voltage reading on channel 1'
    )
    voltage2 = attr.property.float(
        key=':MEAS:VOLT CH2', sets=False, help='output voltage reading channel 2'
    )
    voltage3 = attr.property.float(
        key=':MEAS:VOLT CH3', sets=False, help='output voltage reading channel 3'
    )

    current1 = attr.property.float(
        key=':MEAS:CURR CH1', sets=False, help='current draw reading on channel 1'
    )
    current2 = attr.property.float(
        key=':MEAS:CURR CH2', sets=False, help='current draw reading on channel 2'
    )
    current3 = attr.property.float(
        key=':MEAS:CURR CH3', sets=False, help='current draw reading on channel 3'
    )

    @lb.retry(BaseException, 3)
    def open(self):
        """Poll *IDN until the instrument responds.
        Sometimes it needs an extra poke before it responds.
        """
        try:
            timeout, self.backend.timeout = self.backend.timeout, 0.2
            self.identity
        finally:
            self.backend.timeout = timeout


if __name__ == '__main__':
    import time

    lb.show_messages('debug')

    inst = RigolDP800Series('USB0::0x1AB1::0x0E11::DP8C180200079::INSTR')

    with inst:
        print(inst.identity)
        inst.enable1
        inst.voltage_setting1 = 15.0
        inst.enable1 = True
        time.sleep(0.1)
        print(inst.voltage1, inst.current1)
