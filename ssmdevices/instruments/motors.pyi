"""
Created on Wed Feb  7 10:05:35 2018

@author: aec

This is where we drive things that move: 
    for now this is just the ETS-Lindgren model 2005 Azimuth Positioner
"""
import labbench as lb
from labbench import paramattr as attr
__all__ = ['ETSLindgrenAzi2005']


@attr.adjust('read_termination', default='\n')
@attr.adjust('write_termination', default='\r')
@attr.visa_keying(write_fmt='{key}{value}')
class ETSLindgrenAzi2005(lb.VISADevice):

    def __init__(
        self,
        resource: str='NoneType',
        read_termination: str='str',
        write_termination: str='str',
        open_timeout: str='NoneType',
        timeout: str='int',
        make: str='NoneType',
        model: str='NoneType',
        baud_rate: str='int',
        parity: str='bytes',
        stopbits: str='int',
        xonxoff: str='bool',
        rtscts: str='bool',
        dsrdtr: str='bool'
    ):
        ...
    timeout: float = attr.value.float(default=20, min=0, label='s')
    baud_rate: int = attr.value.int(default=9600, min=1, label='baud')
    parity = attr.value.bytes(default=b'N')
    stopbits = attr.value.float(default=1, min=1, max=2, step=0.5)
    xonxoff = attr.value.bool(default=False)
    rtscts = attr.value.bool(default=False)
    dsrdtr = attr.value.bool(default=False)

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
    speed = attr.property.int(key='S', min=0, max=3, help='speed')
    cwlimit = attr.property.float(key='UL', min=0.0, max=999.9, step=0.1, help='cwlimit')
    cclimit = attr.property.float(key='LL', min=0.0, max=999.9, step=0.1, help='cclimit')
    define_position = attr.property.float(
        key='CP',
        min=0,
        max=360,
        step=0.1,
        help='rotation (degrees)'
    )
    position = attr.property.float(key='SK', min=0, max=360, help='rotation (degrees)', gets=False)
if __name__ == '__main__':
    from pylab import *
    import seaborn as sns
    import time
    sns.set(style='ticks')
    lb.show_messages('debug')
    with ETSLindgrenAzi2005('COM4') as motor:
        motor.set_position('30')
        print(repr(motor.whereami()))
