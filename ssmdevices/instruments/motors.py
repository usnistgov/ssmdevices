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
from labbench.visa import VISADevice
#import pandas as pd

__all__=['ETSLindgrenAzi2005']

class ETSLindgrenAzi2005(VISADevice):    

    read_termination = '0x06'
    #this is an acknowledge byte
    
    write_termination = '0x0D'
    #this is a carriage return    
    
    class state(lb.VISADevice.state):
        '''This does not quality as a "modern" VX11 device, so the core functions are of limited use here
        I may end up writing this using self.query
        '''
        
        query_speed = lb.Int(command=':S?', min=0, max=3, label='speed')
        query_cwlimit = lb.Float(command=':UL?', min=000.0, max=999.9, step=0.1, label='cwlimit')
        query_cclimit = lb.Int(command='LL?',  min=000.0, max=999.9, step=0.1, label='cclimit')
        
    def config(self, mode):
        if mode is 'CR' or 'NCR':
            self.write(self, mode)
        else:
            print('check your spelling!')
        
    def whereami(self):
        return self.command_get('CP?', 'pos')
        
    def wheredoigo(self):
        return self.command_get('DIR?','dir')
        
    def set_speed(self, value):
        self.write('S'+value)
        return self.state.query_speed
    
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
        
#still not clear on how seek will behave vs set position - does set position set a home?
    
    def seek_position(self, value):
        self.write('SK'+value)
    
    def stop(self):
        self.command_set('ST')
        didistop = self.whereami
        time.sleep(2)
        if didistop is 'N':
            print('yay we stopped!')
        else:
            print('oops still moving!')
            
        
 
    