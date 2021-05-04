import labbench as lb

__all__ = ['RigolDP800Series']

class RigolDP800Series(lb.VISADevice):
    REMAP_BOOL = {False: 'OFF', True: 'ON'}

    # values are simply local variable attributes with bounds checking (and callback hooks for logging)
    local_variable = lb.value.str('how to do stuff', help='some configuration for this class')

    # properties accept the "key" argument and/or decorators for custom implementation
    enable1 = lb.property.bool(key=':OUTP CH1', remap=REMAP_BOOL, help='enable DC output on channel 1')
    enable2 = lb.property.bool(key=':OUTP CH2', remap=REMAP_BOOL, help='enable DC output on channel 2')
    enable3 = lb.property.bool(key=':OUTP CH3', remap=REMAP_BOOL, help='enable DC output on channel 3')

    voltage_setting1 = lb.property.float(key=':SOUR1:VOLT', help='output voltage setting on channel 1')
    voltage_setting2 = lb.property.float(key=':SOUR2:VOLT', help='output voltage setting on channel 2')
    voltage_setting3 = lb.property.float(key=':SOUR3:VOLT', help='output voltage setting on channel 3')

    voltage1 = lb.property.float(key=':MEAS:VOLT CH1', settable=False, help='output voltage reading on channel 1')
    voltage2 = lb.property.float(key=':MEAS:VOLT CH2', settable=False, help='output voltage reading channel 2')
    voltage3 = lb.property.float(key=':MEAS:VOLT CH3', settable=False, help='output voltage reading channel 3')

    current1 = lb.property.float(key=':MEAS:CURR CH1', settable=False, help='current draw reading on channel 1')
    current2 = lb.property.float(key=':MEAS:CURR CH2', settable=False, help='current draw reading on channel 2')
    current3 = lb.property.float(key=':MEAS:CURR CH3', settable=False, help='current draw reading on channel 3')

    @lb.datareturn.DataFrame
    def fetch_data_trace(self, whichone):
        """ a silly example for a power supply, no? """
        return self.backend.dosomethingtogettrace(whichone)
        
    @lb.retry(BaseException, 3)
    def open(self):
        ''' Poll *IDN until the instrument responds.
            Sometimes it needs an extra poke before it responds.
        '''
        try:
            timeout, self.backend.timeout = self.backend.timeout, 0.2
            self.identity
        finally:
            self.backend.timeout = timeout

    def get_key(self, scpi_key, trait_name=None):
        ''' This instrument expects keys to have syntax ":COMMAND? PARAM",
            instead of ":COMMAND PARAM?" as implemented in lb.VISADevice.
            
            Insert the "?" in the appropriate place here.
        '''
        if ' ' in scpi_key:
            key = scpi_key.replace(' ', '? ', 1)
        else:
            key = scpi_key + '?'
        return self.query(key)

    def set_key(self, scpi_key, value, trait_name=None):
        ''' This instrument expects sets to have syntax :COMMAND? PARAM,VALUE
            instead of :COMMAND PARAM VALUE? as implemented in lb.VISADevice.
            
            Implement this behavior here.
        '''
        if ' ' in scpi_key:
            key = f'{scpi_key},{value}'
        else:
            key = f'{scpi_key} {value}'
        return self.write(key.rstrip())


if __name__ == '__main__':
    import time

    lb.show_messages('debug')

    inst = RigolDP800Series('USB0::0x1AB1::0x0E11::DP8C180200079::INSTR')

    with inst:
        print(inst.identity)
        inst.enable1
        inst.voltage_setting1 = 15.
        inst.enable1 = True
        time.sleep(.1)
        print(inst.voltage1, inst.current1)
