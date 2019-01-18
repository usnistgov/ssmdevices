import labbench as lb

__all__ = ['RigolDP800Series']

class RigolDP800Series(lb.VISADevice):
    class state(lb.VISADevice.state):
        enable1 = lb.Bool(command=':OUTP CH1',
                          remap={False: 'OFF', True: 'ON'},
                                 help='enable DC output on channel 1')
        enable2 = lb.Bool(command=':OUTP CH2',
                          remap={False: 'OFF', True: 'ON'},
                                 help='enable DC output on channel 2')
        enable3 = lb.Bool(command=':OUTP CH3',
                          remap={False: 'OFF', True: 'ON'},
                                 help='enable DC output on channel 3')

        voltage_setting1 = lb.Float(command=':SOUR1:VOLT',
                                   help='output voltage setting on channel 1')
        voltage_setting2 = lb.Float(command=':SOUR2:VOLT',
                                   help='output voltage setting on channel 2')
        voltage_setting3 = lb.Float(command=':SOUR3:VOLT',
                                   help='output voltage setting on channel 3')
        
        voltage1 = lb.Float(command=':MEAS:VOLT CH1', read_only=True,
                                   help='output voltage measured on channel 1')
        voltage2 = lb.Float(command=':MEAS:VOLT CH2', read_only=True,
                                   help='output voltage measured on channel 2')
        voltage3 = lb.Float(command=':MEAS:VOLT CH3', read_only=True,
                                   help='output voltage measured on channel 3')
        
        current1 = lb.Float(command=':MEAS:CURR CH1', read_only=True,
                                   help='current draw measured on channel 1')
        current2 = lb.Float(command=':MEAS:CURR CH2', read_only=True,
                                   help='current draw measured on channel 2')
        current3 = lb.Float(command=':MEAS:CURR CH3', read_only=True,
                                   help='current draw measured on channel 3')        
        

    @lb.retry(Exception, 3)
    def connect(self):
        ''' Do a dummy read on *IDN until the instrument responds.
            Sometimes it needs an extra poke before it responds.
        '''
        try:
            timeout, self.backend.timeout = self.backend.timeout, 0.2
            self.state.identity
        finally:
            self.backend.timeout = timeout

    @state.getter
    def __(self, trait):
        ''' This instrument expects queries to have syntax :COMMAND? PARAM,
            instead of :COMMAND PARAM? as implemented in lb.VISADevice.
            
            Implement this behavior here.
        '''
        if ' ' in trait.command:
            command = trait.command.replace(' ', '? ', 1)
        else:
            command = trait.command + '?'
        return self.query(command)
    
    @state.setter
    def __(self, trait, value):
        ''' This instrument expects sets to have syntax :COMMAND? PARAM,VALUE
            instead of :COMMAND PARAM VALUE? as implemented in lb.VISADevice.
            
            Implement this behavior here.
        '''
        if ' ' in trait.command:
            cmd = '{},{}'.format(trait.command, value)
        else:
            cmd = '{} {}'.format(trait.command, value)
        return self.write(cmd)

if __name__ == '__main__':
    import time
    
    lb.show_messages('debug')
    
    inst = RigolDP800Series('USB0::0x1AB1::0x0E11::DP8C180200079::INSTR')
    
    with inst:
        print(inst.state.identity)
        inst.state.enable1
        inst.state.voltage_setting1 = 15.
        inst.state.enable1 = True
        time.sleep(.1)
        print(inst.state.voltage1, inst.state.current1)