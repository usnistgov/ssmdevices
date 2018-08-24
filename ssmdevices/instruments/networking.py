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
import numbers

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

    class settings(lb.TelnetDevice.settings):
        timeout = lb.Float(1, min=0, help='leave the timeout small to allow keyboard interrupts')
        ack_timeout = lb.Float(30, min=0.1, help='how long to wait for a command acknowledgment from the TM500 (s)')
        busy_retries = lb.Int(20, min=0)
        remote_ip = lb.Unicode('10.133.0.203', help='ip address of TM500 backend')
        remote_ports = lb.Unicode('5001 5002 5003', help='port of TM500 backend')
        min_acquisition_time = lb.Int(30, min=0, help='minimum time to spend acquiring logs (s)')
        port = lb.Int(5003, min=1)
        config_root  = lb.Unicode('.', help='path to the command scripts directory')
        data_root  = lb.Unicode('.', help='remote save root directory')
        convert_files = lb.List([], help='text to match in the filename of data output files to convert')


    def arm(self, scenario_name):
        ''' Load the scenario from the command listing in a local TM500
            configuration file.
            The the full path to the configuration file is
            `os.path.join(self.settings.config_root, self.settings.config_file)+'.conf'`
            (on the host computer running this python instance).

            If the last script that was run is the same as the selected config
            script, then the script is loaded and sent to the TM500 only
            if force=True. It always runs on the first call after AeroflexTM500
            is instantiated.

            :returns: A list of responses to each command sent
        '''
        if isinstance(scenario_name, numbers.Number):
            scenario_name = str(scenario_name)
        if scenario_name == self.__latest.setdefault('scenario_name',None) is not None:
            raise TM500Error('the TM500 is already armed with the scenario named {}'.format(scenario_name))

        config_path = os.path.join(self.settings.config_root, scenario_name)+'.conf'
        self.logger.debug('arming TM500 scenario {}'\
                          .format(repr(config_path)))

        t0 = time.time()
        with open(config_path, 'r') as f:
            seq = f.readlines()
        self._reconnect()
        ret = self._send(seq)
        if self.settings.data_root is not None:
            self._send('#$$DATA_LOG_FOLDER 1 "{}"'.format(self.settings.data_root))
        self.logger.debug('armed in {:.2f}s'.format(time.time()-t0))
        self.__latest['scenario_name'] = scenario_name
        return ret

    def trigger(self):
        ''' Start logging and return the path to the directory where the data
            is being saved.
        '''
        if self.__latest.get('scenario_name') is None:
            raise TM500Error('arm before triggering')
        self._reconnect()
        self.__latest['data'] = self._send('#$$START_LOGGING').split("'")[1]
        self.__latest['trigger_time'] = time.time()
        return self.__latest['data']

    def stop(self, convert=True):
        ''' Stop logging.
            :param bool convert: Whether to convert the output binary files to text
            
            :returns: If convert=True, a dictionary of {'name': path} items pointing to the converted text output
        '''
        ret = {} if convert else None
        self._block_until_min_acquisition()
        try:
            # Stop running
            self._reconnect()
            self._send('forw mte MtsClearMts')
            self._send('WAIT FOR "I: CMPI MTE 0 MTSCLEARMTS COMPLETE IND" TIMEOUT 60')
            self._send('forw mte DeConfigRdaStopTestCase')
            self._send('WAIT FOR "I: CMPI DTE RDA TEST GROUP STOPPED IND" TIMEOUT 300')
        except TM500Error as e:
            self.logger.debug('exception on attempt to stop scenario: {}'.format(str(e)))
        else:
            if self.__latest.setdefault('data', None) is None:
                self.logger.debug('there is no active logging to stop')
            else:
                self._send('#$$STOP_LOGGING')
                if convert:
                    ret = self._convert_to_text()
                self._send('forw mte GetRrcStats [] [] [] [1] [1]')
                self._send('forw mte GetNasStats [] [] [] [] [1] [1]')
        finally:
            try:
                self._send('SDLI LTE_RADIO_CONTEXT 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000')
                self._send('SDLI LTE_NAS_STATUS 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000')
                self._send('SDLI LTE_RRC_STATUS 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000')
            except TM500Error as e:
                self.logger.debug('exception on attempt to cleanup scenario: {}'.format(str(e)))

        self.__latest['scenario_name'] = None
        self.__latest['data'] = None
        self.__latest['trigger_time'] = 0
        return ret        
    
    @staticmethod
    def command_log_to_script(path):
        ''' Scrape a script out of a TM500 "screen save" text file. The output
            for an input that takes the form <path>/<to>/<filename>.txt
            will be <path>/<to>/<filename>-script.txt.
        '''
        import re
        
        with open(path, 'rb') as f:
            txt = f.read()
            
        # Remove the timestamp.
        # Assumes tab-delimiter separtaes timestamps from the telnet traffic. 
        txt = b'\r\n'.join([line.split(b'\t',1)[-1] for line in txt.splitlines()])
        
        # start where things get interesting
#        i = txt.lower().find(b'abot 0 0 0')
        lines = txt.splitlines()
        for i,line in enumerate(lines):
            if line.lower().strip().startswith(b'rset'):
                break
        else:
            raise ValueError('no start delimited by RSET command found in command log')
        txt = b'\r\n'.join(lines[i:])

        # end at activate
        i = txt.upper().find(b'C: FORW 0X00 OK MTE ACTIVATE')
        if i == -1:
            raise ValueError('no activate found in command log')
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
            elif b'START_LOGGING' in matches[0].rstrip().upper():
                pass
            else:
                commands.append(matches[0].rstrip())
                
        with open(os.path.splitext(path)[0]+'.conf', 'wb') as f:
            f.write(b'\r\n'.join(commands))

    def disconnect(self):
        if self.__latest.get('scenario_name') is not None:
            try:
                self.stop(convert=False)
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
        self.__latest = {}
        
        try:
            self._send('#$$DISCONNECT', timeout=1)
        except:
            pass

        self._reconnect(force=True)
        
        # Set up licensing
        self._send('ABOT 0 0 0')
        self._send('SCFG SWL')
        self._send('STRT')
        self._send('forw swl setlicenseserver none')

    def _tma_is_connected(self):
        try:
            self._send('CHOW')
        except TM500Error as e:
            if e.errcode in (0x02, 0x06):
                return False
            else:
                raise
        return True

    def _reconnect(self, force=False):
        ''' Ensure the TMA software is connected to the TM500
        '''
        if not force and self._tma_is_connected():
            return
        else:
            # Now connect
            self._send('#$$PORT {ip} {ports}'\
                      .format(ip=self.settings.remote_ip, ports=self.settings.remote_ports),
                      timeout=1)
            self._send('#$$CONNECT')
            
    def _block_until_min_acquisition(self):
        ''' Make sure the minimum acquisition time has elapsed to avoid putting
            the TM500 in a sad state
        '''

        if self.__latest.get('trigger_time',0) > 0:
            elapsed = time.time()-self.__latest.get('trigger_time',0)
            if elapsed < self.settings.min_acquisition_time:
                time.sleep(self.settings.min_acquisition_time-elapsed)
        
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

    def _convert_to_text(self):
        ''' Convert the latest data to text
        '''
        root = self.__latest['data']

        t0 = time.time()
        time.sleep(0.25) # TODO Is this really necessary?
#            pre_entries = [f for f in os.listdir(root)]
        self._send('#$$CONVERT_TO_TEXT')
        entries = [f for f in os.listdir(root)\
                   if f.lower().endswith(('csv','txt'))]
        names = ['_'.join(e.split('_')[3:-1]).replace('-','_')\
                 for e in entries]
        paths = [os.path.join(root, e) for e in entries]
        ret = dict(zip(names,paths))
        
        # Remove items not listed in self.settings.convert_files
        if len(self.settings.convert_files)>0:
            for name in list(ret.keys()):
                for inc in self.settings.convert_files:
                    if inc.upper() in name.upper():
                        break
                else:
                    del ret[name]
        
        self.logger.info('converted TM500 logs from binary in {:0.2f}s'
                       .format(time.time()-t0))

        return ret

    def _read_until (self, rsp, timeout=None):
        if timeout is None:
            ack_timeout = self.settings.ack_timeout
        else:
            ack_timeout = timeout
#        self.logger.debug('awaiting response {}'.format(repr(rsp)))
        
        # Block until the expected response is received
        t0 = time.time()
        rsp = rsp.upper()
        ret = b''
        while time.time()-t0 < ack_timeout:
            # Looping on short blocking makes it easier to
            # cancel execution with a KeyboardInterrupt
            ret += self.backend.read_until(rsp, self.settings.timeout)
            if rsp in ret:
                break
        else:
            raise TimeoutError('response timeout')
#        self.logger.debug('    -> {}'.format(ret))
        return ret

if __name__ == '__main__':
    AeroflexTM500.command_log_to_script(r'C:\Users\dkuester\Desktop\TM500_2Sec_8UEs_withTime.txt')
    
#    path = r'e:\TM500ScriptForPaulDebug'
#    lb.show_messages('debug')
#    tm500 = AeroflexTM500('10.133.0.202')
#    with tm500:
##    tm500.connect()
#        t0 = time.time()
#        tm500.configure(path)
#        print(time.time()-t0)