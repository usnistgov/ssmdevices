# -*- coding: utf-8 -*-

""" Network test instrument control classes

:author: Aziz Kord <azizollah.kord@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()

__all__ = ['CobhamTM500']

import labbench as lb

import logging
logger = logging.getLogger('labbench')

class CobhamTM500(lb.TelnetDevice):   
    ''' Control a Cobham TM500 network tester with a
        telnet connection.
    '''

#    class state(lb.TelnetDevice.state):
#        timeout = lb.LocalFloat(2, min=0, is_metadata=True)
#        port = lb.LocalInt(23, min=1, is_metadata=True)
        
#    resource='COM17'
#    'serial port resource name (COMnn in windows or /dev/xxxx in unix/Linux)'
    
#    def command_get (self, command, trait):        
#        return self.backend.write(command)

    def send (self, msg, data_lines=1, alt_ack=None):
        ''' Send a message, then block while waiting for the response.
        
            :param msg: str or bytes containing the message to send
            :param int data_lines: number of lines in the response string            
            :param alt_ack: expected response indicating acknowledgment of the command, or None to guess
            :returns: bytes containing the response
        '''
        logger.debug('{} <- {}'.format(repr(self),msg))        
        if isinstance(msg, str):
            msg = msg.encode()        
        self.backend.write(msg)
        
        # Choose the format of the expected response
        if alt_ack is not None:
            if isinstance(alt_ack, str):
                alt_ack = alt_ack.encode()
            rsp = alt_ack
        if msg.startswith(b'#$$'):
            rsp = msg[3:]
        else:
            rsp = msg
        
        # Block until the expected response is received
        self.backend.read_until(b'C: {}'.format(rsp))
        
        # Receive returned data
        ret = ''
        for i in range(data_lines):
            ret += self.backend.read_until(b'\r').decode()
        logger.debug('{} -> {}'.format(repr(self), ret))
        return ret
            
    def setup (self):
        pass
    
    def start (self):
        pass
    
    def stop (self):
        pass

    def connect (self):
        super(CobhamTM500,self).connect()
        self.backend.write('#$$CONNECT')
    
    def disconnect (self):
        self.backend.write('#$$DISCONNECT')        
        super(CobhamTM500,self).disconnect()