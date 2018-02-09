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

    class state(lb.VISADevice.state):
        '''This does not quality as a "modern" VX11 device, so the core functions are of limited use here
        I may end up writing this using self.query
        '''
        
        query_speed = lb.Int(command=':S?', min=0, max=3, label='speed')
        query_cwlimit = lb.Float(command=':UL?', min=000.0, max=999.9, step=0.1, label='cwlimit')
        query_cclimit = lb.Int(command='LL?',  min=000.0, max=999.9, step=0.1, label='cclimit')
        
        read_termination  = lb.LocalUnicode('0x06', read_only='connected')
        #this is an acknowledge byte
        write_termination = core.LocalUnicode('0x0D', read_only='connected')
        #this is a carriage return    
        
        timeout = core.LocalFloat(2, min=0, is_metadata=True)
        baud_rate = core.LocalInt(9600, min=1, is_metadata=True,)
        parity = core.LocalBytes('N', is_metadata=True,)
        stopbits = core.LocalFloat(1, min=1, max=2, step=0.5, is_metadata=True,)
        xonxoff = core.LocalBool(False, is_metadata=True,)
        rtscts = core.LocalBool(False, is_metadata=True,)
        dsrdtr = core.LocalBool(False, is_metadata=True,)
        
    
    # Overload methods as needed to implement RemoteDevice
    def connect(self):
        ''' Connect to the VISA instrument defined by the VISA resource
            set by `self.resource`. The pyvisa backend object is assigned
            to `self.backend`.

            :returns: None

            Instead of calling `connect` directly, consider using 
            `with` statements to guarantee proper disconnection
            if there is an error. For example, the following
            sets up a connected instance::

                with VISADevice('USB0::0x2A8D::0x1E01::SG56360004::INSTR') as inst:
                    print inst.state.identity
                    print inst.state.status_byte
                    print inst.state.options                

            would instantiate a `VISADevice` and guarantee
            it is disconnected either at the successful completion
            of the `with` block, or if there is any exception.
        '''
        keys = 'read_termination', 'write_termination'
        params = dict([[k, getattr(self, k)] for k in keys])
        self.backend = VISADevice._rm.open_resource(self.resource, **params)

    def disconnect(self):
        ''' Disconnect the VISA instrument. If you use a `with` block
            this is handled automatically and you do not need to 
            call this method.

            :returns: None
        '''
        

    @classmethod
    def set_backend(cls, backend_name):
        ''' Set the pyvisa resource manager for all VISA objects.

            :param backend_name str: '@ni' (the default) or '@py'
            :returns: None
        '''
        VISADevice._rm = pyvisa.ResourceManager(backend_name)

    
    
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
     
if __name__ == '__main__':
    from pylab import *
    import seaborn as sns

    sns.set(style='ticks')

    # Enable labbench debug messages
    # log_to_screen()

    with ETSLindgrenAzi2005('USB0::0x2A8D::0x1E01::SG56360004::INSTR') as motor:

        # Configure
        motor.

   
    