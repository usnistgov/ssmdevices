#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  7 10:05:35 2018

@author: aec

This is where we drive things that move: 
    for now this is just the ETS-Lindgren model 2005 Azimuth Positioner
"""

import labbench as lb

__all__ = ["ETSLindgrenAzi2005"]


class ETSLindgrenAzi2005(lb.VISADevice):
    timeout = lb.value.float(20, min=0,)
    baud_rate = lb.value.int(9600, min=1,)
    parity = lb.value.bytes(b"N",)
    stopbits = lb.value.float(1, min=1, max=2, step=0.5,)
    xonxoff = lb.value.bool(False,)
    rtscts = lb.value.bool(False,)
    dsrdtr = lb.value.bool(False,)
    read_termination = lb.value.str("\n")  # this is an acknowledge byte
    write_termination = lb.value.str("\r")  # this is a carriage return

    def config(self, mode):
        if mode is "CR" or "NCR":
            self.write(self, mode)
        else:
            print("check your spelling!")

    def whereami(self):
        return self.query("CP?")

    def wheredoigo(self):
        return self.query("DIR?")

    def set_speed(self, value):
        self.write("S" + value)

    # return self.query_speed

    def set_limits(self, side, value):
        """Probably should put some error checking in here to make sure value is a float
        Also, note we use write here becuase property.setter inserts a space"""
        if side is "lower":
            self.write("LL" + value)
        elif side is "upper":
            self.write("UL" + value)
        else:
            print("you typed the wrong thing.")

    def set_position(self, value):
        self.write("CP" + value)
        """Important note: 
            This command labels the position with a value. It does not move the turntable!"""

    def seek(self, value):
        self.write("SK" + value)

    def stop(self):
        self.write("ST")
        lb.sleep(3)
        print(self.wheredoigo())
        """If wheredoigo returns N, we are stopped"""
        # didistop = self.wheredoigo()
        # if didistop[0] == 'N':
        #    print('yay we stopped!')
        # else:
        #   print('oops still moving!')

    # A bunch of command-keyed states
    speed = lb.property.int(key="S", min=0, max=3, help="speed")
    cwlimit = lb.property.float(
        key="UL", min=000.0, max=999.9, step=0.1, help="cwlimit"
    )
    cclimit = lb.property.float(
        key="LL", min=000.0, max=999.9, step=0.1, help="cclimit"
    )
    define_position = lb.property.float(
        key="CP", min=0, max=360, step=0.1, help="rotation (degrees)"
    )
    position = lb.property.float(
        key="SK", min=0, max=360, help="rotation (degrees)", gets=False
    )

    def set_key(self, key, value, trait_name=None):
        self.write(key + str(value))


if __name__ == "__main__":
    from pylab import *
    import seaborn as sns

    import time

    sns.set(style="ticks")

    # Enable labbench debug messages
    # log_to_screen()
    lb.show_messages("debug")

    with ETSLindgrenAzi2005("COM4") as motor:

        #        print(motor.query('?'))
        motor.set_position("30")
        print(repr(motor.whereami()))
        # Configure
#        print(motor.define_position)
#        motor.position = 30
#        motor.write('*WAI')
#        print(motor.define_position)
# print(motor.position)
