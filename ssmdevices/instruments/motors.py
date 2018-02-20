#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  7 10:05:35 2018

@author: aec

This is where we drive things that move: 
    for now this is just the ETS-Lindgrem model 2005 Azimuth Positioner
"""
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
#from builtins import super
from future import standard_library
standard_library.install_aliases()

import time
import labbench as lb
#import pandas as pd

__all__=['ETSLindgrenAzi2005']

class ETSLindgrenAzi2005(lb.VISADevice):    

    class state(lb.VISADevice.state):
        '''This does not quality as a "modern" VX11 device, so the core functions are of limited use here
        I may end up writing this using self.query
        '''
        
        speed = lb.Int(command='S', min=0, max=3, help='speed')
        cwlimit = lb.Float(command='UL', min=000.0, max=999.9, step=0.1, help='cwlimit')
        cclimit = lb.Int(command='LL',  min=000.0, max=999.9, step=0.1, help='cclimit')
        define_position = lb.Float(command='CP', min=0, max=360, step=0.1, help='rotation (degrees)')
        position = lb.Float(command='SK', min=0, max=360, help='rotation (degrees)', write_only=True)
        
        read_termination  = lb.LocalUnicode('\n', read_only='connected')
        #this is an acknowledge byte
        write_termination = lb.LocalUnicode('\r', read_only='connected')
        #this is a carriage return    
        
        timeout = lb.LocalFloat(20, min=0, is_metadata=True)
        baud_rate = lb.LocalInt(9600, min=1, is_metadata=True,)
        parity = lb.LocalBytes(b'N', is_metadata=True,)
        stopbits = lb.LocalFloat(1, min=1, max=2, step=0.5, is_metadata=True,)
        xonxoff = lb.LocalBool(False, is_metadata=True,)
        rtscts = lb.LocalBool(False, is_metadata=True,)
        dsrdtr = lb.LocalBool(False, is_metadata=True,)
        
    def command_set(self, command, trait, value):
        ''' Send an SCPI command to set a state value on the
            device. This is
            automatically called for `state` attributes that
            define a message.

            :param str command: The SCPI command to send
            :param trait: The trait state corresponding with the command (ignored)
            :param str value: The value to assign to the parameter
        '''
        self.write(command + str(value))    

    def config(self, mode):
        if mode is 'CR' or 'NCR':
            self.write(self, mode)
        else:
            print('check your spelling!')
        
    def whereami(self):
        return self.query('CP?')
        
    def wheredoigo(self):
        return self.query('DIR?')
        
    def set_speed(self, value):
        self.write('S'+value)
       # return self.state.query_speed
    
    def set_limits(self, side, value):
        '''Probably should put some error checking in here to make sure value is a float
        Also, note we use write here becuase command_set inserts a space'''
        if side is 'lower':
            self.write('LL'+value)
        elif side is 'upper':
            self.write('UL'+value)
        else:
            print('you typed the wrong thing.')
                
    def set_position(self, value):
        self.write('CP'+value)
        '''Important note: 
            This command labels the position with a value. It does not move the turntable!'''
    
    def seek(self, value):
        self.write('SK'+value)
    
    def stop(self):
        self.write('ST')
        time.sleep(3)
        print(self.wheredoigo())
        '''If wheredoigo returns N, we are stopped'''
        #didistop = self.wheredoigo()
        #if didistop[0] == 'N':
        #    print('yay we stopped!')
        #else:
        #   print('oops still moving!')
     
if __name__ == '__main__':
    from pylab import *
    import seaborn as sns
    
    import time

    sns.set(style='ticks')

    # Enable labbench debug messages
    # log_to_screen()
    lb.show_messages('debug')

    with ETSLindgrenAzi2005('COM4') as motor:
        
#        print(motor.query('?'))
        motor.set_position('30')
        print(repr(motor.whereami()))
        # Configure
#        print(motor.state.define_position)
#        motor.state.position = 30
#        motor.write('*WAI')
#        print(motor.state.define_position)
        #print(motor.state.position)