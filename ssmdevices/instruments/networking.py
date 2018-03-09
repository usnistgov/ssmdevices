# -*- coding: utf-8 -*-

""" Network test instrument control classes

:author: Aziz Kord <azizollah.kord@nist.gov>, Dan Kuester <daniel.kuester@nist.gov>
"""
from __future__ import unicode_literals
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()

import labbench as lb
import time, os, ssmdevices.etc

__all__ = ['AeroflexTM500']

class TM500Error(ValueError):
    def __init__ (self, msg, errcode=None):
        super(TM500Error, self).__init__(msg)
        self.errcode = errcode

class AeroflexTM500(lb.TelnetDevice):
    ''' Control an Aeroflex TM500 network tester with a
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
        ack_timeout = lb.LocalFloat(30, min=0.1, is_metadata=True,
                                    help='how long to wait for a command acknowledgment from the TM500 (s)')
        busy_retries = lb.LocalInt(20, min=0, is_metadata=True)
        remote_ip = lb.LocalUnicode('10.133.0.203', is_metadata=True,
                                    help='ip address of TM500 backend')
        remote_ports = lb.LocalUnicode('5001 5002 5003', is_metadata=True,
                                       help='port of TM500 backend')

        port = lb.LocalInt(5003, min=1, is_metadata=True)
        config_root  = lb.LocalUnicode('', is_metadata=True,
                                       help='path to the command scripts directory')
        data_root  = lb.LocalUnicode(write_only=True, help='remote save root directory',
                                     is_metadata=True)

    def configure(self, name, force=False):
        ''' Ensure that config script at :param path: has been run.
            The configuration script loaded is determined as
            `os.path.join(self.state.config_root, self.state.config_file)+'.conf'`.

            If the last script that was run is the same as the selected config
            script, then the script is loaded and sent to the TM500 only
            if force=True. It always runs on the first call after AeroflexTM500
            is instantiated.

            :returns: None
        '''
        if name == self.__last_config and not force:
            self.logger.debug('not running script {} because it is already running'\
                              .format(name))
            return
        else:
            self.__last_config = name
            config_path = os.path.join(self.state.config_root, name)+'.conf'
            self.logger.debug('loading configuration from {}'\
                              .format(name))
        t0 = time.time()

        with open(config_path, 'r') as f:
            seq = f.readlines()
        ret = self._send(seq)
        self._send('#$$DATA_LOG_FOLDER 1 "{}"'.format(self.state.data_root))
        self.logger.debug('run configured in {:.2f}s'.format(time.time()-t0))        
        return ret

    def start_logging(self):
        ''' Start logging and return the path to the directory where the data
            is saved.
        '''
        return self._send('#$$START_LOGGING').split("'")[1]

    def stop_logging(self):
        self._send('#$$STOP_LOGGING')

    def convert_to_text(self):
        ''' Convert the most recently acquired data to text.
        '''
        self._send('#$$CONVERT_TO_TEXT')

    def stop_running(self):
        self._send('forw mte MtsClearMts')
        self._send('WAIT FOR "I: CMPI MTE 0 MTSCLEARMTS COMPLETE IND" TIMEOUT 60')
        self._send('forw mte DeConfigRdaStopTestCase')
        self._send('WAIT FOR "I: CMPI DTE RDA TEST GROUP STOPPED IND" TIMEOUT 300')
        self._send('#$$STOP_LOGGING')
        self._send('forw mte GetRrcStats [] [] [] [1] [1]')
        self._send('forw mte GetNasStats [] [] [] [] [1] [1]')
        self._send('SDLI LTE_RADIO_CONTEXT 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000')
        self._send('SDLI LTE_NAS_STATUS 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000')
        self._send('SDLI LTE_RRC_STATUS 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000')

    @staticmethod
    def screensave_to_script(path):
        ''' Scrape a script out of a TM500 "screen save" text file. The output
            for an input that takes the form <path>/<to>/<filename>.txt
            will be <path>/<to>/<filename>-script.txt.
        '''
        import re
        
        with open(path, 'rb') as f:
            txt = f.read()
        
        # start where things get interesting
        i = txt.lower().find(b'abot 0 0 0')
        if i != -1:
            txt = txt[i:]

        # end at activate
        i = txt.upper().find(b'C: FORW 0X00 OK MTE ACTIVATE')
        if i == -1:
            raise ValueError('no activate found in script')
        i_eol = txt[i:].find(b'\r\n')
        if i_eol != -1:
            i = i+i_eol
        txt = txt[:i]

        blocks = re.split(b'(^C: .*)', txt, flags=re.MULTILINE|re.IGNORECASE)
        
        # Throw out odd-numbered leftover at the end
        blocks = blocks[:2*(len(blocks)//2)]
        
        # The result is organized by pairs of (big chunk of data, command response).
        # Get the command from the first word of the incoming command
        commands = []
        for i in range(0,len(blocks),2):
            # Get the 2nd field in the response field. That's the start of command 
            # the full line command.
            rsp = blocks[i+1].split()
            if len(rsp)>1:
                cmd = rsp[1]
            else:
                print("\n\nWARNING: Don't know what to do with command response ", blocks[i+1])
                
            # Find the line that starts with the line in the previous block of
            # text. Throw a warning unless there was exactly 1 match in the
            # block of text.
            matches = re.findall(br'^([\#\$]*'+cmd+b'.*)', blocks[i], re.MULTILINE|re.IGNORECASE)
            if len(matches) == 0:
                print('\n\nWARNING: Found no command for ', blocks[i+1].rstrip().strip(),
                      '\n after ', repr(blocks[i]))
            elif len(matches) > 1:
                print('\n\nWARNING: More than one match for ', blocks[i+1].rstrip().strip(),
                      ': ', repr(matches))
            else:
                commands.append(matches[0].rstrip())#[matches[0], rsp])
                
        with open(os.path.splitext(path)[0]+'-script.txt', 'wb') as f:
            f.write(b'\r\n'.join(commands))

    def disconnect(self):
        try:
            self.stop_running()
        except TM500Error as e:
            if e.errcode not in (0x02, 0x06):
                raise

        try:
            self._send('#$$DISCONNECT', confirm=False)
        except:
            pass
        
        super(AeroflexTM500, self).disconnect()

    def setup(self):
        # Invalidate any incomplete previous commands in the remote telnet buffer
        try:
            self._send('***', timeout=1)
        except (ValueError,TimeoutError):
            pass

        # Ensure we are disconnected
        try:
            self._send('#$$DISCONNECT', timeout=1)
        except (ValueError,TimeoutError):
            pass

        # Now connect
        self._send('#$$PORT {ip} {ports}'\
                  .format(ip=self.state.remote_ip, ports=self.state.remote_ports),
                  timeout=1)
        self._send('#$$CONNECT')
        self.__last_config = None

    def _send(self, msg, data_lines=1, confirm=True, timeout=None):
        ''' Send a message, then block until a confirmation message is received.
        
            :param msg: str or bytes containing the message to send
            :param int data_lines: number of lines in the response string            

            :returns: decoded string containing the response
        '''
        
        # First, if this is a sequence of messages, work through them one by one
        if hasattr(msg, '__iter__') and not isinstance(msg, (str, bytes)):
            return [self._send(m) for m in msg]

        # Send the message
        if isinstance(msg, str):
            msg = msg.encode('ascii')
        msg = msg.strip().rstrip()
        if len(msg) == 0:
            return ''
        elif msg.strip().lower().startswith(b'wait for')\
             and b'timeout' in msg.lower():
            timeout = int(msg.lower().rsplit(b'timeout',1)[1].strip())

        self.logger.debug('write {}'.format(repr(msg)))
        self.backend.write(msg + b'\r')

        if not confirm:
            return
        
        # Figure out the expected response
        rsp = msg.split(b' ', 1)[0]
        if rsp.startswith(b'#$$'):
            rsp = rsp[3:]
        rsp = b'C: ' + rsp + b' '

        # Block until the response
        ret = self._read_until(rsp, timeout)
        # Receive through the end of line for the rest of the status response
        ret = rsp
        for i in range(data_lines):
            ret = ret + self.backend.read_until(b'\r')
            code = int(ret.strip().split(b'0x',1)[1].split(maxsplit=1)[0],16)
            if i == 0 and code != 0:
                raise TM500Error('Error in message {}: {}'\
                                 .format(repr(msg), repr(ret)), code)
        # Receive any other data received during the delay
        extra = self.backend.read_very_eager().strip().rstrip()
        if extra:
            if extra.count(b'\r') <=1:
                self.logger.debug('extra -> {}'.format(extra.decode()))
            else:
                self.logger.debug('extra -> ({} lines)'.format(extra.count(b'\r')))
        return ret.decode('ascii')

    def _read_until (self, rsp, timeout=None):
        if timeout is None:
            ack_timeout = self.state.ack_timeout
        else:
            ack_timeout = timeout
#        self.logger.debug('awaiting response {}'.format(repr(rsp)))
        
        # Block until the expected response is received
        t0 = time.time()
        rsp = rsp.upper()
        ret = b''
        while time.time()-t0 < ack_timeout:
            # Brief blocking makes it easier to trigger a KeyboardInterrupt
            ret += self.backend.read_until(rsp, self.state.timeout)
            if rsp in ret:
                break
        else:
            raise TimeoutError('response timeout')
#        self.logger.debug('    -> {}'.format(ret))
        return ret

if __name__ == '__main__':
    AeroflexTM500.screensave_to_script(r'g:\dgk\PSCRup32UEsScreenSave.txt')
    path = r'g:\dgk\PSCRup32UEsScreenSave-script.txt'
    lb.show_messages('debug')
    with AeroflexTM500('10.133.0.202') as tm500:
        tm500.run(path)
        time.sleep(5)