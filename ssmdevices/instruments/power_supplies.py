import labbench as lb

__all__ = ['RigolDP800Series']


class RigolDP800Series(lb.VISADevice):
    enable1 = lb.Bool(key=':OUTP CH1',
                      remap={False: 'OFF', True: 'ON'},
                      help='enable DC output on channel 1')
    enable2 = lb.Bool(key=':OUTP CH2',
                      remap={False: 'OFF', True: 'ON'},
                      help='enable DC output on channel 2')
    enable3 = lb.Bool(key=':OUTP CH3',
                      remap={False: 'OFF', True: 'ON'},
                      help='enable DC output on channel 3')
    voltage_setting1 = lb.Float(key=':SOUR1:VOLT',
                                help='output voltage setting on channel 1')
    voltage_setting2 = lb.Float(key=':SOUR2:VOLT',
                                help='output voltage setting on channel 2')
    voltage_setting3 = lb.Float(key=':SOUR3:VOLT',
                                help='output voltage setting on channel 3')
    voltage1 = lb.Float(key=':MEAS:VOLT CH1', settable=False,
                        help='output voltage measured on channel 1')
    voltage2 = lb.Float(key=':MEAS:VOLT CH2', settable=False,
                        help='output voltage measured on channel 2')
    voltage3 = lb.Float(key=':MEAS:VOLT CH3', settable=False,
                        help='output voltage measured on channel 3')
    current1 = lb.Float(key=':MEAS:CURR CH1', settable=False,
                        help='current draw measured on channel 1')
    current2 = lb.Float(key=':MEAS:CURR CH2', settable=False,
                        help='current draw measured on channel 2')
    current3 = lb.Float(key=':MEAS:CURR CH3', settable=False,
                        help='current draw measured on channel 3')

    @lb.retry(Exception, 3)
    def open(self):
        ''' Do a dummy read on *IDN until the instrument responds.
            Sometimes it needs an extra poke before it responds.
        '''
        try:
            timeout, self.backend.timeout = self.backend.timeout, 0.2
            self.identity
        finally:
            self.backend.timeout = timeout

    def __get_by_key__(self, key, name):
        ''' This instrument expects queries to have syntax :COMMAND? PARAM,
            instead of :COMMAND PARAM? as implemented in lb.VISADevice.
            
            Implement this behavior here.
        '''
        if ' ' in key:
            key = key.replace(' ', '? ', 1)
        return self.query(key)

    def __set_by_key__(self, key, name, value):
        ''' This instrument expects sets to have syntax :COMMAND? PARAM,VALUE
            instead of :COMMAND PARAM VALUE? as implemented in lb.VISADevice.
            
            Implement this behavior here.
        '''
        if ' ' in key:
            key = f'{key},{value}'
        else:
            key = f'{key} {value}'
        return self.write(key)


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
