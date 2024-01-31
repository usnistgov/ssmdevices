# -*- coding: utf-8 -*-
"""
Author: Keith Forsyth

Instrument driver for CMW500 base station emulator, initially created with intent of controlling band, 
power, and scheduling dynamics for UE IQ UL acquisitions.
"""

import time

import labbench as lb
from labbench import paramattr as attr

__all__ = ['RohdeSchwarzCMW500']

default_cmw_address = 'TCPIP0::10.0.0.3::inst0::INSTR'


@attr.visa_keying(remap={False: 'OFF', True: 'ON'})
class RohdeSchwarzCMW500(lb.VISADevice):
    """A base station emulator"""

    UPDATE_RATE = 20

    # Enhancement would be to change the SIGN1 to be a variable of some sort, and potentially the PCC to be a variable(SCC)
    channel_bandwidth = attr.method.str(
        key='CONF:LTE:SIGN1:CELL:BAND:PCC:DL',
        only=['B014', 'B030', 'B050', 'B100', 'B150', 'B200'],
    )
    lte_signaling = attr.method.bool(
        key='SOUR:LTE:SIGN1:CELL:STAT',
    )
    scheduling_type = attr.method.str(
        key='CONF:LTE:SIGN1:CONN:PCC:STYPE', only=['RMC', 'UDCH', 'UDTT']
    )  # not comprehensive

    # channel_band             = attr.method.str(key=NEED TO FIND COMMAND,values =[NEED TO FIND BAND CODES'OB66'])
    ue_attached = attr.method.bool(key='SENS:LTE:SIGN1:RRCS?')
    ulrmc_num_rbs = attr.method.int(key='CONF:LTE:SIGN1:CONN:PCC:RMCUL', min=1, max=100)
    ulrmc_modulation = attr.method.str(
        key='CONF:LTE:SIGN1:CONN:PCC:RMC:UL', only=['QPSK', 'Q16']
    )
    ulrmc_transblocksize = attr.method.int(
        key='CONF:LTE:SIGN1:CONN:PCC:RMC:UL', min=-1, max=100
    )
    ul_chan_freq = attr.method.float(key='CONF:LTE:SIGN1:RFS:PCC:CHAN:UL', sets=False)
    ue_target_power = attr.method.float(
        key='CONF:LTE:SIGN1:UL:PCC:PUSC:TPC:CLTP', min=-50, max=-20
    )
    ue_rsrp = attr.method.float(key='SENS:LTE:SIGN1:UER:PCC:RSRP?', sets=False)
    ue_rsrq = attr.method.float(key='SENS:LTE:SIGN1:UER:PCC:RSRQ?', sets=False)
    # spectrogram_num_avg      = attr.method.int(key='NEED TO FIND COMMAND',min=1,max=100)

    @ul_chan_freq.getter
    def _(self):
        command = 'CONF:LTE:SIGN1:RFS:PCC:CHAN:UL? Hz'
        return self.query(command)

    @ulrmc_num_rbs.getter
    def _(self):
        msg = self.query('CONF:LTE:SIGN1:CONN:PCC:RMC:UL?')
        value = msg.split(',')[0]
        num_rbs = value.split('N')[1]
        return num_rbs

    @ulrmc_modulation.getter
    def _(self):
        msg = self.query('CONF:LTE:SIGN1:CONN:PCC:RMC:UL?')
        modulation = msg.split(',')[1]
        return modulation

    @ulrmc_transblocksize.getter
    def _(self):
        msg = self.query('CONF:LTE:SIGN1:CONN:PCC:RMC:UL?')
        value = msg.split(',')[2]
        if value == 'KEEP':
            return -1
        if value == 'ZERO':
            return 0
        value = value.split('T')[1]
        return value

    @ulrmc_num_rbs.setter
    def _(self, value):
        modulation = self.state.ulrmc_modulation
        transblocksize = self.state.ulrmc_transblocksize
        if transblocksize == -1:
            transblocksize = 'KEEP'
        if transblocksize == 0:
            transblocksize = 'ZERO'
        if isinstance(transblocksize, int):
            transblocksize = 'T' + str(transblocksize)
        arg = f'N{value},{modulation},{transblocksize}'
        lb.logger.debug(f'ULRMC arg is: {arg}')
        self.write(f'CONF:LTE:SIGN1:CONN:PCC:RMC:UL {arg}')

    @ulrmc_modulation.setter
    def _(self, value):
        num_rbs = self.state.ulrmc_num_rbs
        transblocksize = self.state.ulrmc_transblocksize
        if transblocksize == -1:
            transblocksize = 'KEEP'
        if transblocksize == 0:
            transblocksize = 'ZERO'
        if isinstance(transblocksize, int):
            transblocksize = 'T' + str(transblocksize)
        arg = f'N{num_rbs},{value},{transblocksize}'
        lb.logger.debug(f'ULRMC arg is: {arg}')
        self.write(f'CONF:LTE:SIGN1:CONN:PCC:RMC:UL {arg}')

    @ulrmc_transblocksize.setter
    def _(self, value):
        num_rbs = self.state.ulrmc_num_rbs
        modulation = self.state.ulrmc_modulation
        if value == -1:
            value = 'KEEP'
        if value == 0:
            value = 'ZERO'
        if isinstance(value, int):
            value = 'T' + str(value)
        arg = f'N{num_rbs},{modulation},{value}'
        lb.logger.debug(f'ULRMC arg is: {arg}')
        self.write(f'CONF:LTE:SIGN1:CONN:PCC:RMC:UL {arg}')

    def wait_for_cell_activate(self, timeout=180):
        """a blocking wait until the cell has been stood up,checking the packet
        switched state as indicated by the CMW500
        SCPI = FETC:LTE:SIGN1:PSW:STAT?"""
        for i in range(timeout):
            cell_state = self.query('FETC:LTE:SIGN1:PSW:STAT?')
            packet_switched = None
            if cell_state == 'ATT':
                packet_switched = True
                break
            if cell_state == 'OFF':
                packet_switched = False
            time.sleep(1)
            if i % self.UPDATE_RATE == 0:
                lb.logger.info('Waiting for Cell to activate...')
        lb.logger.info('Packet Switching Activated: ' + str(packet_switched))
        return packet_switched

    def wait_for_cell_deactivate(self, timeout=180):
        """a blocking wait until the cell has been dekeyed,checking the packet
        switched state as indicated by the CMW500
        SCPI = FETCH:LTE:SIGN1:PSW:STAT?"""
        for i in range(timeout):
            cell_state = self.query('FETC:LTE:SIGN1:PSW:STAT?')
            packet_switched = None
            if cell_state == 'OFF':
                packet_switched = False
                break
            if cell_state == 'ATT':
                packet_switched = True
            time.sleep(1)
            if i % self.UPDATE_RATE == 0:
                lb.logger.info('Waiting for Cell to deactivate...')
        lb.logger.info('Packet Switching Activated: ' + str(packet_switched))
        return packet_switched

    def wait_for_ue_to_attach(self, timeout=180):
        """a blocking wait until the UE has attached,checking the RRC
        state as indicated by the CMW500
        SCPI = SENS:LTE:SIGN1:RRCS?"""
        for i in range(timeout):
            ue_state = self.query('SENS:LTE:SIGN1:RRCS?')
            attached = None
            if ue_state == 'CONN':
                attached = True
                break
            if ue_state == 'IDLE':
                attached = False
            time.sleep(1)
            if i % self.UPDATE_RATE == 0:
                lb.logger.info('Waiting for UE to attach...')
        lb.logger.info('UE is Attached: ' + str(attached))
        return attached

    def fetch_spectrogram(self):
        """a request to pull the spectrogram down from the cmw500, input
        values are fixed with a RBW of 30kHz and the frequency span x array
        calculated on that assumption.  Would be better to generalize this.
        May also want to add the ability to trigger the measurement
        SCPI = FETC:LTE:MEAS:MEV:TRAC:SEM:RBW:AVER?"""
        values = self.query_ascii_values('FETC:LTE:MEAS:MEV:TRAC:SEM:RBW30:AVER?')
        cent_freq = self.state.ul_chan_freq
        values.pop(0)
        freq_from_cent_list = []
        abs_freq_list = []
        for i in range(len(values)):
            abs_freq = cent_freq + (i - (len(values) - 1) / 2) * 30000
            freq_from_cent = (i - (len(values) - 1) / 2) * 30000
            freq_from_cent_list.append(freq_from_cent)
            abs_freq_list.append(abs_freq)
        return {
            'abs_freq': abs_freq_list,
            'freq_from_cent': freq_from_cent_list,
            'power': values,
        }

    def fetch_iq(self):
        """a request to pull the iq down from the cmw500, not implemented yet"""
        raise NotImplementedError

    def config_ul_udtti(self, tti, start_rb, num_rb, mod):
        """Configure the CMW for User Defined TTI scheduling and send
        start rb,number of rb's and type of modulation to CMW for a given TTI.
        Available modulations for UL are QPSK and 16QAM (Q16).
        SCPI = CONF:LTE:SIGN1:CONN:PCC:UDTT:UL {tti},{start_rb},{num_rb},{mod}"""
        self.state.scheduling_type = 'UDTT'
        self.write(f'CONF:LTE:SIGN1:CONN:PCC:UDTT:UL {tti},{start_rb},{num_rb},{mod},0')
        ul_udtti = self.query(f'CONF:LTE:SIGN1:CONN:PCC:UDTT:UL? {tti}').split(',')
        if int(ul_udtti[0]) != start_rb:
            self._logger.error('ul_udtti write failed')
            return False
        if int(ul_udtti[1]) != int(num_rb):
            self._logger.error('ul_udtti write failed')
            return False
        if ul_udtti[2] != str(mod):
            self._logger.error('ul_udtti write failed')
            return False
        self._logger.debug(
            'ul_udtti written, tti:{tti},start_rb:{start_rb},num_rb:{num_rb},mod:{mod}'
        )
        return True


def test_cmw_idn():
    """Use the IDN query to check that the manf and model # match the expected"""
    cmw500 = RohdeSchwarzCMW500(default_cmw_address)
    cmw500.connect()
    cmw_identity = cmw500.query('*IDN?').split(',')
    if cmw_identity[0] == 'Rohde&Schwarz' and cmw_identity[1] == 'CMW':
        return True
    else:
        return False


def test_cmw():
    """Test to:
        1.  connect to the instrument
        2.  set the bandwidth
        3.  set UE target power
        4.  set RMC #RBs
        5.  stand the cell up
        6.  wait for the UE to attach
        7.  shut the cell down.
    This requires the UE to be in a state that in can connect with the instrument"""
    cmw500 = RohdeSchwarzCMW500(default_cmw_address)
    cmw500.connect()
    cmw500.state.channel_bandwidth = 'B014'
    # cmw500.state.channel_band = 'NEED VALUE'
    cmw500.state.ue_target_power = -21
    cmw500.state.ulrmc_num_rbs = 5
    cmw500.state.lte_signaling = True
    cmw500.wait_for_ue_to_attach(timeout=60)
    cmw500.state.lte_signaling = False
    cmw500.wait_for_cell_deactivate(timeout=60)
    return True


if __name__ == '__main__':
    print('IDN test pass: ' + str(test_cmw_idn()))
    print('UE Attach test pass: ' + str(test_cmw()))
