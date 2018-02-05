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
import logging, time
logger = logging.getLogger('labbench')

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
        timeout = lb.LocalFloat(5, min=0, is_metadata=True)
        port = lb.LocalInt(5003, min=1, is_metadata=True)

    # Define time delays needed after specified commands (in sec)
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

#    resource='COM17'
#    'serial port resource name (COMnn in windows or /dev/xxxx in unix/Linux)'
    
#    def command_get (self, command, trait):        
#        return self.backend.write(command)

    def send(self, msg, data_lines=1, alt_ack=None):
        ''' Send a message, then block while waiting for the response.
        
            :param msg: str or bytes containing the message to send
            :param int data_lines: number of lines in the response string            
            :param alt_ack: expected response indicating acknowledgment of the command, or None to guess
            
            :returns: decoded string containing the response
        '''

        # First, if this is a sequence of messages, work through them one by one
        if hasattr(msg, '__iter__') and not isinstance(msg, (str,bytes)):
            for m in msg:
                self.send(m)

        # Send the message
        logger.debug('{} <- {}'.format(repr(self),msg))        
        if isinstance(msg, str):
            msg = msg.encode('ascii')        
        self.backend.write(msg+b'\r')
        
        # Identify the format of the expected response
        if alt_ack is not None:
            if isinstance(alt_ack, str):
                alt_ack = alt_ack.encode('ascii')
            rsp = alt_ack
        else:
            rsp = msg.split(' ')[0]
            if rsp.startswith(b'#$$'):
                rsp = rsp[3:]
        
        # Block until the expected response is received
        self.backend.read_until(b'C: {}'.format(rsp))
        
        # Receive any status response
        ret = ''
        for i in range(data_lines):
            ret += self.backend.read_until(b'\r').decode('ascii')
        logger.debug('{} -> {}'.format(repr(self), ret))

        # Add a delay, if this message starts with a command that needs a delay
        for delay_msg, delay in self.delays.items():
            if msg.startswith(delay_msg):
                time.sleep(delay)
                break

        # Receive any other data received during the delay
        ret += self.backend.read_very_eager()

        return ret

    def setup (self):
        seq = b"ABOT 0 0 0",\
                b"RSET",\
                b"SCFG SWL",\
                b"STRT",\
                b"forw swl setlicenseserver none",\
                b"RSET",\
                b"SELR 0 0 RC1 COMBINED",\
                b"EREF 0 0 0",\
                b"GETR",\
                b"SCFG MTS_MODE",\
                b"GVER",\
                b"STRT",\
                b"#$$SET_DOCKING_WINDOWS 0 -1 -1 -1 -1 -1 -1 -1 1 1 -1 -1",\
                b"#$$DATA_LOG_OPTIONS 0 0 0",\
                b"#$$LC_CLEAR_ALL",\
                b"#$$LC_GRP 0 0 1 200 0 0 0 L1CELLWATCH",\
                b"#$$LC_CAT 104 0 1 0 #GRP:L1CELLWATCH",\
                b"#$$LC_ITM 1 1 0 FunctionalTestLogging",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 L1L2FTL #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 6002 0 0 0 #GRP:L1L2FTL",\
                b"#$$LC_CAT 6003 0 0 0 #GRP:L1L2FTL",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 L1DLRSPOWER #Radio_Context_ID 0-23 0",\
                b"#$$LC_CAT 1102 0 0 0 #GRP:L1DLRSPOWER",\
                b"#$$LC_CAT 112 0 0 0 #GRP:L1DLRSPOWER",\
                b"#$$LC_CAT 113 0 0 0 #GRP:L1DLRSPOWER",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 L1CSIRSPOWER #Radio_Context_ID 0-23 0",\
                b"#$$LC_CAT 5203 0 0 0 #GRP:L1CSIRSPOWER",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 ULSRS #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 2102 0 0 0 #GRP:ULSRS",\
                b"#$$LC_CAT 212 0 0 0 #GRP:ULSRS",\
                b"#$$LC_GRP 0 1 0 1 0 0 0 DLL1L2CONTROL #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 901 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 902 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 92 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 93 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 94 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 95 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 96 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 97 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 98 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 99 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 903 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_CAT 905 0 0 0 #GRP:DLL1L2CONTROL",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 DLOVERVIEW #UEGROUP: UE 0-31 0 #CellGroup_ComponentCarrier 0-9 0",\
                b"#$$LC_CAT 2402 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 243 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 245 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 242 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 246 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2413 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2414 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 247 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 248 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2415 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2416 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2409 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2410 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2417 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2418 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2411 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2412 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2419 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_CAT 2420 0 0 0 #GRP:DLOVERVIEW",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 CQIREPORTING #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 262 0 0 0 #GRP:CQIREPORTING",\
                b"#$$LC_CAT 263 0 0 0 #GRP:CQIREPORTING",\
                b"#$$LC_CAT 264 0 0 0 #GRP:CQIREPORTING",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 L1CHANCODING #UEGROUP: UE 0-31 0 #CellGroup_ComponentCarrier 0-9 0",\
                b"#$$LC_CAT 702 0 0 0 #GRP:L1CHANCODING",\
                b"#$$LC_CAT 72 0 0 0 #GRP:L1CHANCODING",\
                b"#$$LC_CAT 73 0 0 0 #GRP:L1CHANCODING",\
                b"#$$LC_CAT 74 0 0 0 #GRP:L1CHANCODING",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 DLSCHRX #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 202 0 0 0 #GRP:DLSCHRX",\
                b"#$$LC_CAT 203 0 0 0 #GRP:DLSCHRX",\
                b"#$$LC_CAT 204 0 0 0 #GRP:DLSCHRX",\
                b"#$$LC_GRP 0 1 0 1 0 0 0 ULSCHTX #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 82 1 0 0 #GRP:ULSCHTX",\
                b"#$$LC_CAT 83 1 0 0 #GRP:ULSCHTX",\
                b"#$$LC_CAT 85 1 0 0 #GRP:ULSCHTX",\
                b"#$$LC_CAT 87 1 0 0 #GRP:ULSCHTX",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 PRACHTX #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 3502 0 0 0 #GRP:PRACHTX",\
                b"#$$LC_CAT 352 0 0 0 #GRP:PRACHTX",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 DLHARQRX #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 41 0 0 0 #GRP:DLHARQRX",\
                b"#$$LC_GRP 0 1 0 1 0 0 0 ULHARQTX #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 161 1 0 0 #GRP:ULHARQTX",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 ULHARQSUMMARY #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 171 0 0 0 #GRP:ULHARQSUMMARY",\
                b"#$$LC_CAT 172 0 0 0 #GRP:ULHARQSUMMARY",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 L1THROUGHPUT #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 282 0 0 0 #GRP:L1THROUGHPUT",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 UEOVERVIEW #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 3002 0 0 0 #GRP:UEOVERVIEW",\
                b"#$$LC_CAT 302 0 0 0 #GRP:UEOVERVIEW",\
                b"#$$LC_CAT 303 0 0 0 #GRP:UEOVERVIEW",\
                b"#$$LC_CAT 304 0 0 0 #GRP:UEOVERVIEW",\
                b"#$$LC_CAT 306 0 0 0 #GRP:UEOVERVIEW",\
                b"#$$LC_GRP 0 0 0 100 0 0 0 L1DLRBUSAGE #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 3102 0 0 0 #GRP:L1DLRBUSAGE",\
                b"#$$LC_CAT 312 0 0 0 #GRP:L1DLRBUSAGE",\
                b"#$$LC_CAT 313 0 0 0 #GRP:L1DLRBUSAGE",\
                b"#$$LC_GRP 0 1 0 100 0 0 0 L1ULRBUSAGE #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 3202 1 0 0 #GRP:L1ULRBUSAGE",\
                b"#$$LC_CAT 322 1 0 0 #GRP:L1ULRBUSAGE",\
                b"#$$LC_CAT 323 1 0 0 #GRP:L1ULRBUSAGE",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 MACRX #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 1202 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 122 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 124 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 125 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 126 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 128 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 129 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1210 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1212 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1213 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1214 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1216 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1217 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1218 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1220 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1221 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1222 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1224 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1225 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1226 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1228 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1229 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1230 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1232 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1233 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1234 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1236 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1237 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1238 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1240 0 0 0 #GRP:MACRX",\
                b"#$$LC_CAT 1241 0 0 0 #GRP:MACRX",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 MACTX #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 602 0 0 0 #GRP:MACTX",\
                b"#$$LC_CAT 62 0 0 0 #GRP:MACTX",\
                b"#$$LC_CAT 64 0 0 0 #GRP:MACTX",\
                b"#$$LC_CAT 65 0 0 0 #GRP:MACTX",\
                b"#$$LC_CAT 66 0 0 0 #GRP:MACTX",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 MACTFS #UEGROUP: UE 0-31 0",\
                b"#$$LC_CAT 2702 0 0 0 #GRP:MACTFS",\
                b"#$$LC_CAT 272 0 0 0 #GRP:MACTFS",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 BCHRX #Radio_Context_ID 0-23 0",\
                b"#$$LC_CAT 2502 0 0 0 #GRP:BCHRX",\
                b"#$$LC_CAT 252 0 0 0 #GRP:BCHRX",\
                b"#$$LC_GRP 0 0 0 1 0 0 0 L1DRSOBSERVABILITYINFO #Cell_Instance 0-23 0",\
                b"#$$LC_CAT 10502 0 0 0 #GRP:L1DRSOBSERVABILITYINFO",\
                b"#$$LC_GRP 0 0 0 200 0 0 0 L1CARRIERPOWERS #UEGROUP: UE 0-419 0 #Cell_Group_Instance_ID 0,1 0",\
                b"#$$LC_CAT 5303 0 0 0 #GRP:L1CARRIERPOWERS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 SCCSTATUS #UEGROUP: UE 0-419 0 #Cell_Instance_ID 0 2",\
                b"#$$LC_CAT 6103 0 0 0 #GRP:SCCSTATUS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 L1DLSTATS #UEGROUP: UE 0-419 0",\
                b"#$$LC_CAT 8705 0 0 0 #GRP:L1DLSTATS",\
                b"#$$LC_CAT 8702 0 0 0 #GRP:L1DLSTATS",\
                b"#$$LC_CAT 8703 0 0 0 #GRP:L1DLSTATS",\
                b"#$$LC_CAT 8704 0 0 0 #GRP:L1DLSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 L1DLCARRIERSTATS #UEGROUP: UE 0-419 0 #CellGroup_ComponentCarrier 0-9 0",\
                b"#$$LC_CAT 8105 0 0 0 #GRP:L1DLCARRIERSTATS",\
                b"#$$LC_CAT 8102 0 0 0 #GRP:L1DLCARRIERSTATS",\
                b"#$$LC_CAT 8104 0 0 0 #GRP:L1DLCARRIERSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 L1ULSTATS #UEGROUP: UE 0-419 0",\
                b"#$$LC_CAT 8805 0 0 0 #GRP:L1ULSTATS",\
                b"#$$LC_CAT 8802 0 0 0 #GRP:L1ULSTATS",\
                b"#$$LC_CAT 8803 0 0 0 #GRP:L1ULSTATS",\
                b"#$$LC_CAT 8804 0 0 0 #GRP:L1ULSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 L1ULCARRIERSTATS #UEGROUP: UE 0-419 0 #CellGroup_ComponentCarrier 0-9 0",\
                b"#$$LC_CAT 7702 0 0 0 #GRP:L1ULCARRIERSTATS",\
                b"#$$LC_CAT 7703 0 0 0 #GRP:L1ULCARRIERSTATS",\
                b"#$$LC_CAT 7705 0 0 0 #GRP:L1ULCARRIERSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 L1CELLDLOVERVIEW #Cell_Instance_ID 0 0",\
                b"#$$LC_CAT 9102 0 0 0 #GRP:L1CELLDLOVERVIEW",\
                b"#$$LC_CAT 9103 0 0 0 #GRP:L1CELLDLOVERVIEW",\
                b"#$$LC_CAT 9104 0 0 0 #GRP:L1CELLDLOVERVIEW",\
                b"#$$LC_CAT 9105 0 0 0 #GRP:L1CELLDLOVERVIEW",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 L1CELLDLCARRIEROVERVIEW #Cell_Instance_ID 0 0",\
                b"#$$LC_CAT 8002 0 0 0 #GRP:L1CELLDLCARRIEROVERVIEW",\
                b"#$$LC_GRP 0 1 1 500 0 0 0 L1CELLULOVERVIEW #Cell_Instance_ID 0 0",\
                b"#$$LC_CAT 9202 1 1 0 #GRP:L1CELLULOVERVIEW",\
                b"#$$LC_CAT 9203 1 1 0 #GRP:L1CELLULOVERVIEW",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 L1CELLULCARRIEROVERVIEW #Cell_Instance_ID 0 0",\
                b"#$$LC_CAT 7602 0 0 0 #GRP:L1CELLULCARRIEROVERVIEW",\
                b"#$$LC_GRP 0 0 1 500 0 0 0 SYSOVERVIEW",\
                b"#$$LC_CAT 9302 0 1 0 #GRP:SYSOVERVIEW",\
                b"#$$LC_CAT 9304 0 1 0 #GRP:SYSOVERVIEW",\
                b"#$$LC_CAT 9303 0 1 0 #GRP:SYSOVERVIEW",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 THROUGHPUT3D #UEGROUP: UE 0-419 0",\
                b"#$$LC_CAT 9932 0 0 0 #GRP:THROUGHPUT3D",\
                b"#$$LC_CAT 9933 0 0 0 #GRP:THROUGHPUT3D",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 CARRIERTHROUGHPUT3D #UEGROUP: UE 0-419 0 #CellGroup_ComponentCarrier 0-9 0",\
                b"#$$LC_CAT 9952 0 0 0 #GRP:CARRIERTHROUGHPUT3D",\
                b"#$$LC_CAT 9953 0 0 0 #GRP:CARRIERTHROUGHPUT3D",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 THROUGHPUTGRID #UEGROUP: UE 0-419 0",\
                b"#$$LC_CAT 9942 0 0 0 #GRP:THROUGHPUTGRID",\
                b"#$$LC_CAT 9943 0 0 0 #GRP:THROUGHPUTGRID",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 CARRIERTHROUGHPUTGRID #UEGROUP: UE 0-419 0 #CellGroup_ComponentCarrier 0-9 0",\
                b"#$$LC_CAT 9962 0 0 0 #GRP:CARRIERTHROUGHPUTGRID",\
                b"#$$LC_CAT 9963 0 0 0 #GRP:CARRIERTHROUGHPUTGRID",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 CARRIERTHROUGHPUTOVERVIEW #UEGROUP: UE 0-419 0 #CellGroup_ComponentCarrier 0-9 0",\
                b"#$$LC_CAT 9972 0 0 0 #GRP:CARRIERTHROUGHPUTOVERVIEW",\
                b"#$$LC_CAT 9973 0 0 0 #GRP:CARRIERTHROUGHPUTOVERVIEW",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 CARRIERTHROUGHPUTTEXT #UEGROUP: UE 0 0",\
                b"#$$LC_CAT 7902 0 0 0 #GRP:CARRIERTHROUGHPUTTEXT",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 MACRXSTATS #UEGROUP: UE 0-419 0 #Logical_Channel_ID 0-13 1",\
                b"#$$LC_CAT 9405 0 0 0 #GRP:MACRXSTATS",\
                b"#$$LC_CAT 9402 0 0 0 #GRP:MACRXSTATS",\
                b"#$$LC_CAT 9403 0 0 0 #GRP:MACRXSTATS",\
                b"#$$LC_CAT 9404 0 0 0 #GRP:MACRXSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 MACTXSTATS #UEGROUP: UE 0-419 0 #Logical_Channel_ID 0-10 1",\
                b"#$$LC_CAT 9505 0 0 0 #GRP:MACTXSTATS",\
                b"#$$LC_CAT 9502 0 0 0 #GRP:MACTXSTATS",\
                b"#$$LC_CAT 9503 0 0 0 #GRP:MACTXSTATS",\
                b"#$$LC_CAT 9504 0 0 0 #GRP:MACTXSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 RLCRXSTATS #UEGROUP: UE 0-419 0 #Radio_Bearer_ID -3-34 1",\
                b"#$$LC_CAT 9604 0 0 0 #GRP:RLCRXSTATS",\
                b"#$$LC_CAT 9602 0 0 0 #GRP:RLCRXSTATS",\
                b"#$$LC_CAT 9603 0 0 0 #GRP:RLCRXSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 RLCTXSTATS #UEGROUP: UE 0-419 0 #Radio_Bearer_ID 0-34 1",\
                b"#$$LC_CAT 9704 0 0 0 #GRP:RLCTXSTATS",\
                b"#$$LC_CAT 9702 0 0 0 #GRP:RLCTXSTATS",\
                b"#$$LC_CAT 9703 0 0 0 #GRP:RLCTXSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 PDCPRXSTATS #UEGROUP: UE 0-419 0 #Access_Bearer_ID -3-18 1",\
                b"#$$LC_CAT 9802 0 0 0 #GRP:PDCPRXSTATS",\
                b"#$$LC_CAT 9803 0 0 0 #GRP:PDCPRXSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 PDCPTXSTATS #UEGROUP: UE 0-419 0 #Access_Bearer_ID 0-18 1",\
                b"#$$LC_CAT 9902 0 0 0 #GRP:PDCPTXSTATS",\
                b"#$$LC_CAT 9903 0 0 0 #GRP:PDCPTXSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 RRCSTATS #Cell_Instance -1-273 0",\
                b"#$$LC_CAT 8402 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8403 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8404 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8405 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8406 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8407 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8410 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8408 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8409 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8411 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8412 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_CAT 8413 0 0 0 #GRP:RRCSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 NASSTATS #Cell_Instance -1-273 0",\
                b"#$$LC_CAT 8503 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8504 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8505 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8506 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8507 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8508 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8509 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8510 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8511 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8512 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8513 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8514 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8515 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8516 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8517 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8518 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8519 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_CAT 8520 0 0 0 #GRP:NASSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 EPSBEARERSTATS #Cell_Instance -1-273 0",\
                b"#$$LC_CAT 8602 0 0 0 #GRP:EPSBEARERSTATS",\
                b"#$$LC_CAT 8603 0 0 0 #GRP:EPSBEARERSTATS",\
                b"#$$LC_CAT 8604 0 0 0 #GRP:EPSBEARERSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 RACHSTATS #Cell_Instance -1,0 0",\
                b"#$$LC_CAT 7502 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7503 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7504 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7505 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7506 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7507 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7508 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7509 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7510 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7511 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_CAT 7512 0 0 0 #GRP:RACHSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 MCHSTATS #Index 0-24 0",\
                b"#$$LC_CAT 10002 0 0 0 #GRP:MCHSTATS",\
                b"#$$LC_CAT 10003 0 0 0 #GRP:MCHSTATS",\
                b"#$$LC_CAT 10004 0 0 0 #GRP:MCHSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 MACMBMSSTATS #Index 0-24 0",\
                b"#$$LC_CAT 10102 0 0 0 #GRP:MACMBMSSTATS",\
                b"#$$LC_CAT 10103 0 0 0 #GRP:MACMBMSSTATS",\
                b"#$$LC_GRP 0 0 0 500 0 0 0 RLCMBMSSTATS #Index 0-24 0",\
                b"#$$LC_CAT 10202 0 0 0 #GRP:RLCMBMSSTATS",\
                b"#$$LC_CAT 10203 0 0 0 #GRP:RLCMBMSSTATS",\
                b"#$$LC_GRP 0 0 1 1 0 0 0 ProtocolLog",\
                b"#$$LC_CAT 1030 0 1 0 #GRP:ProtocolLog",\
                b"#$$LC_GRP 0 1 0 1000 0 0 0 RealDataApplicationLog #UEGROUP: UE 0-419 0",\
                b"#$$LC_CAT 1031 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_CAT 1032 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_CAT 1033 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_CAT 1034 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_CAT 1035 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_CAT 1036 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_CAT 1037 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_CAT 1038 1 0 0 #GRP:RealDataApplicationLog",\
                b"#$$LC_END"

        self.send(seq)

    def start (self):
        seq = b"#$$START_LOGGING",\
              b"forw l1 SetPortMapping 1",\
              b"forw mte SetMueRadioContextCell 0 0 18700 10",\
              b"forw mte PhyCalibrateUlPowerOffset [0]",\
              b"forw mte PhyConfigUlInterference -37 [0] [0]",\
              b"forw mte DeConfigRdaStartTestCase 1 10.133.0.204 [] [1_UE_UDP] [] [1]",\
              b"forw mte MtsConfigEnb 1{0 0 0 1{0 18700 200 [0 120 0 0(0)] [9]}} [1]",\
              b"forw mte MtsConfigUeGroup 0 0 1{0}",\
              b"forw mte MtsConfigPath 0 1{24 53}",\
              b"forw mte MtsConfigMobility 0 0 0 1 0 0 0 -80",\
              b"forw mte MtsConfigTrafficProfile 0 1{internet 2{0(ctera_DL -1) 0 [],0(ctera_UL -1) 0 []} [] [] []} []",\
              b"forw mte MtsConfigTraffic 0 0 0 [0 0 0 -1(1)] [] [0]",\
              b"forw mte MtsConfigScenario 1{11520 1{0 0} 1{0 0} []}",\
              b"forw mte SetUEGroupContext 0",\
              b"forw mte UsimConfig 1([001010123456063+1 2] [] [1] [] []) [] [] [000102030405060708090A0B0C0D0E0F] [] [] []",\
              b"forw mte PhyConfigSysCap 1 4 4",\
              b"forw mte RrcAptConfigCellSelection 18700 [0 [0]]",\
              b"forw mte RrcAptConfigUeCap [[] [] [] [] [] [] []] [0]",\
              b"forw mte NasAptConfigCapability [3] [224] [224] [] [] [] [3]",\
              b"forw mte NasAptConfigIdentity [1234567898UE%5] [12345678987UE%5]",\
              b"forw mte NasAptConfigPlmnSelection 001001",\
              b"forw mte Activate -1"

        self.send(seq)

    def stop (self):
        self.send(b"#$$STOP_LOGGING")

    def connect (self):
        super(CobhamTM500,self).connect()
        self.send("#$$PORT 10.133.0.203 5001 5002 5003")
        self.send('#$$CONNECT')
    
    def disconnect (self):
        try:
            self.stop()
        except:
            pass

        try:
            self.send('#$$DISCONNECT')
        except:
            pass
        super(CobhamTM500,self).disconnect()