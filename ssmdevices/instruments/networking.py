# -*- coding: utf-8 -*-

""" Network test instrument control classes

:author: Aziz Kord <azizollah.kord@nist.gov>, Dan Kuester <daniel.kuester@nist.gov>
"""
from __future__ import unicode_literals
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()

__all__ = ['CobhamTM500']

import labbench as lb
import time, os, ssmdevices.etc

class CobhamTM500(lb.TelnetDevice):
    ''' Control a Cobham TM500 network tester with a
        telnet connection.

        The approach here is to iterate through lines of bytes, and
        add delays as needed for special cases as defined in the
        `delays` attribute.

        At some point, these lines should just be loaded directly
        from a file that could be treated as a config file.
    '''

    class state(lb.TelnetDevice.state):
        timeout = lb.LocalFloat(1, min=0, is_metadata=True,
                                help='leave the timeout small to allow keyboard interrupts')
        ack_retries = lb.LocalInt(20, min=1, is_metadata=True)
        port    = lb.LocalInt(5003, min=1, is_metadata=True)
        config_path  = lb.LocalUnicode('', is_metadata=True,
                                       help='path to the directory containing sequences of commands')

    # Define time delays needed after a few command special cases (in sec)
    delays = {b'SCFG MTS_MODE':   2,
              b'GVER':            1,
              b'STRT':            2,
              b'#$$LMA_STATE':    1,
              b"#$$LC_CLEAR_ALL": 1,
              b'#$$LC_GRP 0 0 0 1 0 0 0 MACTX': 1,
              b'#$$LC_GRP 0 0 0 1 0 0 0 BCHRX': 1,
              b'#$$LC_GRP 0 0 0 500 0 0 0 L1DLCARRIERSTATS': 1,
              b'#$$LC_GRP 0 0 0 500 0 0 0 THROUGHPUT3D': 1,
              b'#$$LC_GRP 0 0 0 500 0 0 0 MACTXSTATS': 1,
              b'#$$LC_GRP 0 0 0 500 0 0 0 RRCSTATS': 1,
              b'#$$LC_GRP 0 0 0 500 0 0 0 NASSTATS': 1,
              b'#$$LC_GRP 0 1 0 1000 0 0 0 RealDataApplicationLog': 1,
              b'#$$LC_END': 1,
              b'#$$START_LOGGING': 1,
              b'forw mte Activate': 1
              }

    # Special cases of acknowledgment responses
    alt_responses = {b'forw mte MtsClearMts': b'I: CMPI MTE 0',
                     b'forw mte DeConfigRdaStartTestCase': b'I: CMPI DTE RDA TEST GROUP STARTED IND'}

    def send(self, msg, data_lines=1):
        ''' Send a message, then block while waiting for the response.
        
            :param msg: str or bytes containing the message to send
            :param int data_lines: number of lines in the response string            
            :param alt_ack: expected response indicating acknowledgment of the command, or None to guess
            
            :returns: decoded string containing the response
        '''

        # First, if this is a sequence of messages, work through them one by one
        if hasattr(msg, '__iter__') and not isinstance(msg, (str, bytes)):
            return [self.send(m) for m in msg]

        # Send the message
        if isinstance(msg, str):
            msg = msg.encode('ascii')
        msg = msg.strip().rstrip()
        if len(msg) == 0:
            return ''
        lb.logger.debug('{} - send {}'.format(repr(self),repr(msg)))
        self.backend.write(msg + b'\r')
        
        # Identify the format of the expected response. Use the exception
        # if there is one, otherwise default to the response that starts 'C: '
        for check_msg, alt_ack in self.alt_responses.items():
            if msg.lower().startswith(check_msg.lower()):
                rsp = alt_ack
                break
        else:
            rsp = msg.split(b' ')[0]
            if rsp.startswith(b'#$$'):
                rsp = rsp[3:]
            rsp = b'C: ' + rsp + b' '

        # Add a delay, if this message starts with a command that needs a delay
        for delay_msg, delay in self.delays.items():
            if msg.lower().startswith(delay_msg.lower()):
                lb.logger.debug('sleep {} sec'.format(delay))
                time.sleep(delay)
                break

        # Block until the expected response is received
        lb.logger.debug('{} - waiting for {}'.format(repr(self),repr(rsp)))
        for i in range(self.state.ack_retries):
            ret = self.backend.read_until(rsp.upper(), self.state.timeout)
            if len(ret.strip()) > 0:
                break
        else:
            raise TimeoutError('response timeout')
        
        # Receive any status response
        ret = b''
        for i in range(data_lines):
            ret += self.backend.read_until(b'\r')
            if i == 0 and int(ret.strip().split(b' ',1)[0],16) != 0:
                raise ValueError('Error in message {}: {}'\
                                 .format(repr(msg), repr(ret)))

        # Receive any other data received during the delay
        extra = self.backend.read_very_eager().strip().rstrip()
        if extra:
            lb.logger.debug('{} -> {}'.format(repr(self), extra))
            ret += b'\n'+extra

        lb.logger.debug('{} - received {}'.format(repr(self), ret.decode('ascii')))

        return ret.decode('ascii')

    def send_from_config(self, name):
        path = os.path.join(self.state.config_path, name)
        lb.logger.debug('loading message sequence from {}'.format(repr(path)))
        with open(path, 'r') as f:
            seq = f.readlines()
        return self.send(seq)

    def setup(self):
        try:
            self.send('#$$DISCONNECT')
        except ValueError:
            pass

        return self.send_from_config('setup.txt')

    def start(self):
        return self.send_from_config('start.txt')

    def stop(self):
        return self.send_from_config('stop.txt')

    def reboot(self):
        self.send('RBOT')

    def connect(self):
        if self.state.config_path == '':
            self.state.config_path = ssmdevices.etc.default_path(self.__class__)
        super(CobhamTM500, self).connect()

    def disconnect(self):
        try:
            self.stop()
        except:
            pass

        try:
            self.backend.write('#$$DISCONNECT')
        except:
            pass
        super(CobhamTM500, self).disconnect()
