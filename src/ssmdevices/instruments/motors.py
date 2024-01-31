#!/usr/bin/env python3

"""
Created on Wed Feb  7 10:05:35 2018

@author: aec

This is where we drive things that move: 
    for now this is just the ETS-Lindgren model 2005 Azimuth Positioner
"""

import labbench as lb
from labbench import paramattr as attr

__all__ = ['ETSLindgrenAzi2005']


@attr.visa_keying(write_fmt='{key}{value}')
class ETSLindgrenAzi2005(lb.VISADevice):
    # constructor argument fields
    timeout: float = attr.value.float(default=20, min=0, label='s')
    baud_rate: int = attr.value.int(default=9600, min=1, label='baud')
    parity = attr.value.bytes(default=b'N')
    stopbits = attr.value.float(default=1, min=1, max=2, step=0.5)
    xonxoff = attr.value.bool(default=False)
    rtscts = attr.value.bool(default=False)
    dsrdtr = attr.value.bool(default=False)

    read_termination: str = attr.value.str('\n', inherit=True)
    write_termination: str = attr.value.str('\r', inherit=True)

    def config(self, mode):
        if mode in ('CR' or 'NCR'):
            self.write(self, mode)
        else:
            print('check your spelling!')

    def whereami(self):
        return self.query('CP?')

    def wheredoigo(self):
        return self.query('DIR?')

    def set_speed(self, value):
        self.write('S' + value)

    # return self.query_speed

    def set_limits(self, side, value):
        """Probably should put some error checking in here to make sure value is a float
        Also, note we use write here becuase property.setter inserts a space"""
        if side == 'lower':
            self.write('LL' + value)
        elif side == 'upper':
            self.write('UL' + value)
        else:
            print('you typed the wrong thing.')

    def set_position(self, value):
        self.write('CP' + value)
        """Important note: 
            This command labels the position with a value. It does not move the turntable!"""

    def seek(self, value):
        self.write('SK' + value)

    def stop(self):
        self.write('ST')
        lb.sleep(3)
        print(self.wheredoigo())
        """If wheredoigo returns N, we are stopped"""
        # didistop = self.wheredoigo()
        # if didistop[0] == 'N':
        #    print('yay we stopped!')
        # else:
        #   print('oops still moving!')

    # A bunch of command-keyed states
    speed = attr.property.int(key='S', min=0, max=3, help='speed')
    cwlimit = attr.property.float(
        key='UL', min=000.0, max=999.9, step=0.1, help='cwlimit'
    )
    cclimit = attr.property.float(
        key='LL', min=000.0, max=999.9, step=0.1, help='cclimit'
    )
    define_position = attr.property.float(
        key='CP', min=0, max=360, step=0.1, help='rotation (degrees)'
    )
    position = attr.property.float(
        key='SK', min=0, max=360, help='rotation (degrees)', gets=False
    )


if __name__ == '__main__':
    # Enable labbench debug messages
    # log_to_screen()
    lb.show_messages('debug')

    with ETSLindgrenAzi2005('COM4') as motor:
        #        print(motor.query('?'))
        motor.set_position('30')
        print(repr(motor.whereami()))
        # Configure
#        print(motor.define_position)
#        motor.position = 30
#        motor.write('*WAI')
#        print(motor.define_position)
# print(motor.position)
