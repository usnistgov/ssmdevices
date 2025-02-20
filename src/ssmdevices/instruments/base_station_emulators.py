# -*- coding: utf-8 -*-
"""
Author: Keith Forsyth

Instrument driver for CMW500 base station emulator, initially created with intent of controlling band,
power, and scheduling dynamics for UE IQ UL acquisitions.
"""

import time

import labbench as lb
from labbench import paramattr as attr
import re

__all__ = ['RohdeSchwarzCMW500']



def field_as_int(x):
    if x == 'ZERO':
        return 0
    return int(re.sub('[^0-9]', '', x))


@attr.visa_keying(remap={False: 'OFF', True: 'ON'})
class RohdeSchwarzCMW500(lb.VISADevice):
    """TODO: Update this docstring
    A base station emulator
    """

    UPDATE_RATE = 20

    """
    LTE signaling parameters
    LTE Cell setup, order based on the LTE signaling menu on the CMW
    """

    # DL/UL Band, excluding channel/frequency
    # Enhancement would be to change the SIGN1 to be a variable of some sort, and potentially the PCC to be a variable(SCC)
    @attr.property.int(min=1, max=255)
    def operating_band(self):
        resp = self.query('CONF:LTE:SIGN1:PCC:BAND?')
        return field_as_int(resp)

    @operating_band.setter
    def _(self, int_value):
        self.write(f'CONF:LTE:SIGN1:PCC:BAND OB{int_value}')

    # ************ FDD: cyclic prefix(norm/ext), broadcast message len (nothing explicit, deeper in menus), partially empty subframes/slot
    # rb number important
    # Channel duplexing, FDD or TDD
    duplex_mode = attr.property.str(key='CONFigure:LTE:SIGN1:PCC:DMODE', only=('TDD', 'FDD'))
    # Channel frequency
    # UL and DL are both dependent, set DL in this case
    ul_chan_freq = attr.property.int(key='CONF:LTE:SIGN1:RFS:PCC:CHAN:UL', sets=False)
    dl_chan_freq = attr.property.str(key='CONF:LTE:SIGN1:RFS:PCC:CHAN:DL')

    # Cell Bandwidth
    @attr.property.int(only=(1.4, 3, 5, 10, 15, 20))
    def cell_bw_mhz(self):
        resp = self.query('CONFigure:LTE:SIGN:CELL:BANDwidth:PCC:DL?')
        return field_as_int(resp)

    @cell_bw_mhz.setter
    def _(self, int_val):
        self.write(f'CONFigure:LTE:SIGN:CELL:BANDwidth:PCC:DL B{str(int_val).zfill(2)}0')

    # RS EPRE
    # TODO: implement dependencies to limit range of set point
    rs_epre = attr.property.float(
        key='CONFigure:LTE:SIGN:DL:PCC:RSEPre:LEVel',
        help='range dependent on connector, external attenuation, and num rbs configured',
    )

    # PUSCH open loop nominal power
    pusch_olnp = attr.property.float(
        key='CONFigure:LTE:SIGN1:UL:SETA:PUSCh:OLNPower', min=-50, max=-20, help='software limited to -20dbm'
    )
    # PUSCH closed loop target power
    pusch_cltp = attr.property.float(
        key='CONF:LTE:SIGN1:UL:PCC:PUSC:TPC:CLTP', min=-50, max=-20, help='software limited to -20dbm'
    )

    # LTE scheduling
    scheduling_type = attr.property.str(
        key='CONF:LTE:SIGN1:CONN:PCC:STYPE', only=['RMC', 'UDCH', 'UDTT', 'CQI', 'EMAM', 'EMCS']
    )

    # Downlink allocation parameters, rb and modulation configuration
    def _get_link_params(self, dlul):
        """
        Private function retrieve downlink parameters independent of scheduling type
        Be carful, querying each type of scheduling type will change the set scheduling type, this logic takes care of that
        param uldl: string with either 'dl' or 'ul' to specifiy downlink or uplink parameters
        returns: dictionary with all of the fields for getting/setting the downlink parameters
        """
        if dlul not in {'dl', 'ul'}:
            raise ValueError('invalid input to get link params private func')
        # TODO: hmm we could refactor this func to input a dl_params dict to either query or write commands...
        sched_type = self.scheduling_type
        field_dict = {'scheduling': sched_type}
        try:
            # Python requirment for ssmdevices is 3.9-3.12 TODO: update to python >= 3.10 for match, case
            if sched_type == 'RMC':
                vals = self.query(f'CONFigure:LTE:SIGN:CONNection:PCC:RMC:{dlul.upper()}?')
                fields = vals.split(',')
                field_dict.update(
                    {
                        'num_rbs': field_as_int(fields[0]),
                        'modulation': fields[1],
                        'transblkszidx': field_as_int(fields[2]),
                    }
                )
            elif sched_type == 'UDCH':
                # TODO: implement more than one DL channel, currently set to DL1
                vals = self.query(f'CONFigure:LTE:SIGN:CONNection:PCC:UDCHannels:{dlul.upper()}?')
                fields = vals.split(',')
                # for some god-awful reason, num_rbs reported here is numeric rather than format 'N[x]' (where x is numeric)
                field_dict.update(
                    {
                        'num_rbs': field_as_int(fields[0]),
                        'start_rb': fields[1],
                        'modulation': fields[2],
                        'transblkszidx': field_as_int(fields[3]),
                    }
                )
            elif sched_type == 'UDTT':
                raise NotImplementedError('UDTT scheduling type not handled')
            elif sched_type == 'CQI':
                raise NotImplementedError('CQI scheduling type not handled')
            elif sched_type == 'EMAM':
                raise NotImplementedError('EMAM scheduling type not handled')
            elif sched_type == 'EMCS':
                raise NotImplementedError('EMCS scheduling type not handled')
            else:
                raise ValueError(f'Unexpected scheduling type returned: {sched_type}')
        except Exception as e:
            try:
                print(fields)
            except NameError:
                raise e('Error somewhere parsing')
            finally:
                raise Exception

        return field_dict

    def _format_link_params(self, param_dict):
        sched_type = self.scheduling_type
        if sched_type == 'RMC':
            output_string = 'N{},{},T{}'.format(
                param_dict['num_rbs'], param_dict['modulation'], param_dict['transblkszidx']
            )
        elif sched_type == 'UDCH':
            output_string = '{},{},{},{}'.format(
                param_dict['num_rbs'],
                param_dict['start_rb'],
                param_dict['modulation'],
                param_dict['transblkszidx'],
            )
        elif sched_type == 'UDTT':
            raise NotImplementedError()
            #TODO: fill lists with zeros for all ttis
            for index in param_dict["num_rb"]:
                if len(index) != 10:
                    rbs_list = []

        elif sched_type in ('CQI', 'EMAM', 'EMCS'):
            # TODO: check if uplink and downlink are the same for these scheduling types as they are implemented
            raise NotImplementedError(f'{sched_type} scheduling type not handled')
        else:
            raise ValueError(f'Unexpected scheduling type returned: {sched_type}')

        return output_string

    @attr.property.int(min=0, max=100)
    def dl_num_rbs(self):
        return self._get_link_params('dl')['num_rbs']

    @dl_num_rbs.setter
    def _(self, int_val):
        dl_params = self._get_link_params('dl')
        if dl_params['scheduling'] == 'RMC':
            dl_params['num_rbs'] = int_val
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:RMC:DL {self._format_link_params(dl_params)}')
        elif dl_params['scheduling'] == 'UDCH':
            dl_params['num_rbs'] = int_val
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:UDCHannels:DL1 {self._format_link_params(dl_params)}')
        elif dl_params['scheduling'] in ('UDTT', 'CQI', 'EMAM', 'EMCS'):
            raise NotImplementedError(f'{dl_params["scheduling"]} scheduling type not handled')
        else:
            raise ValueError(f'Unexpected scheduling type returned: {dl_params["scheduling"]}')

    @attr.property.any()
    def dl_start_rb(self):
        dl_params = self._get_link_params('dl')
        if dl_params['scheduling'] == 'RMC':
            return self.query('CONFigure:LTE:SIGN:CONNection:PCC:RMC:RBPosition:DL?')
        elif dl_params['scheduling'] == 'UDCH':
            return dl_params['start_rb']
        else:
            raise NotImplementedError(f'{dl_params["scheduling"]} scheduling type not handled')

    @dl_start_rb.setter
    def _(self, val):
        dl_params = self._get_link_params('dl')
        if dl_params['scheduling'] == 'RMC':
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:RMC:RBPosition:DL {val}')
        elif dl_params['scheduling'] == 'UDCH':
            dl_params['start_rb'] = val
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:UDCHannels:DL1 {self._format_link_params(dl_params)}')
        else:
            raise NotImplementedError(f'{dl_params["scheduling"]} scheduling type not handled')

    @attr.property.str(only=('QPSK', 'Q16', 'Q64', 'Q256'))
    def dl_modulation(self):
        dl_params = self._get_link_params('dl')
        return dl_params['modulation']

    @dl_modulation.setter
    def _(self, str_val):
        dl_params = self._get_link_params('dl')
        dl_params['modulation'] = str_val
        setter_string = self._format_link_params(dl_params)
        if dl_params['scheduling'] == 'RMC':
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:RMC:DL {setter_string}')
        elif dl_params['scheduling'] == 'UDCH':
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:UDCHannels:DL1 {setter_string}')
        else:
            raise NotImplementedError(f'{dl_params["scheduling"]} scheduling type not handled')

    # Uplink allocation parameters, rb and modulation configuration
    @attr.property.int(min=0, max=100)
    def ul_num_rbs(self):
        num_rbs = self._get_link_params('ul')['num_rbs']
        if num_rbs == 'ZERO':
            num_rbs = 0
        return int(num_rbs)

    @ul_num_rbs.setter
    def _(self, int_val):
        ul_params = self._get_link_params('ul')
        ul_params['num_rbs'] = int_val
        if ul_params['num_rbs'] == 0:
            ul_params['num_rbs'] = 'ZERO'
        setter_string = self._format_link_params(ul_params)
        if ul_params['scheduling'] == 'RMC':
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:RMC:UL {setter_string}')
        elif ul_params['scheduling'] == 'UDCH':
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:UDCHannels:UL {setter_string}')
        else:
            raise NotImplementedError(f'{ul_params["scheduling"]} scheduling type not handled')

    @attr.property.any()
    def ul_start_rb(self):
        ul_params = self._get_link_params('ul')
        if ul_params['scheduling'] == 'RMC':
            return self.query('CONFigure:LTE:SIGN:CONNection:PCC:RMC:RBPosition:UL?')
        elif ul_params['scheduling'] == 'UDCH':
            return ul_params['start_rb']

    @ul_start_rb.setter
    def _(self, val):
        ul_params = self._get_link_params('ul')
        if ul_params['scheduling'] == 'RMC':
            if val == 0:
                self.write('CONFigure:LTE:SIGN:CONNection:PCC:RMC:RBPosition:UL LOW')
            else:
                self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:RMC:RBPosition:UL P{val}')
        elif ul_params['scheduling'] == 'UDCH':
            ul_params['start_rb'] = val
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:UDCHannels:UL {self._format_link_params(ul_params)}')
        else:
            raise NotImplementedError(f'{ul_params["scheduling"]} scheduling type not handled')

    @attr.property.str(only=('QPSK', 'Q16', 'Q64', 'Q256'))
    def ul_modulation(self):
        ul_params = self._get_link_params('ul')
        return ul_params['modulation']

    @ul_modulation.setter
    def _(self, str_val):
        ul_params = self._get_link_params('ul')
        ul_params['modulation'] = str_val
        setter_string = self._format_link_params(ul_params)
        if ul_params['scheduling'] == 'RMC':
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:RMC:UL {setter_string}')
        elif ul_params['scheduling'] == 'UDCH':
            self.write(f'CONFigure:LTE:SIGN:CONNection:PCC:UDCHannels:UL {setter_string}')
        else:
            raise NotImplementedError(f'{ul_params["scheduling"]} scheduling type not handled')

    # Control channel power offsets, all relative to RS EPRE
    # PBCH
    pbch_offset = attr.property.float(key='CONFigure:LTE:SIGN:DL:PCC:PBCH:POFFset', min=-30, max=0)
    # PCFICH
    pcfich_offset = attr.property.float(key='CONFigure:LTE:SIGN:DL:PCC:PBCH:POFFset', min=-30, max=0)
    # PDCCH
    pdcch_offset = attr.property.float(key='CONFigure:LTE:SIGN:DL:PCC:PDCCh:POFFset', min=-30, max=0)
    # PSS
    pss_offset = attr.property.float(key='CONFigure:LTE:SIGN:DL:PCC:PSS:POFFset', min=-30, max=0)
    # SSS
    sss_offset = attr.property.float(key='CONFigure:LTE:SIGN:DL:PCC:SSS:POFFset', min=-30, max=0)

    # System setup
    def save_state(self, config_name: str):
        # TODO: DOCME
        self.write(f'MMEMory:SAV {config_name}')

    def load_state(self, config_name: str):
        self.write(f'MMEMory:RCL {config_name}')

    def reset_cmw(self):
        self.write('*RST')

    # Trigger Settings
    trig_a_direction = attr.property.str(key='TRIGger:BASE:EXTA:DIRection', only=('IN', 'OUT'))
    # TODO: make enum for the lte trigger types
    trig_a_source = attr.property.str(
        key='TRIGger:BASE:EXTA:SOURce', only=('"LTE Sig1: FrameTrigger"', '"LTE Sig1: PRACH Trigger"', '"LTE Sig1:TPC Trigger"')
    )
    trig_b_direction = attr.property.str(key='TRIGger:BASE:EXTB:DIRection', only=('IN', 'OUT'))
    trig_b_source = attr.property.str(
        key='TRIGger:BASE:EXTB:SOURce', only=('LTE Sig1:FrameTrigger', 'LTE Sig1:PRACH Trigger', 'LTE Sig1:TPC Trigger')
    )
    # ulrmc_num_rbs = attr.property.int(key='CONF:LTE:SIGN1:CONN:PCC:RMCUL', min=1, max=100)
    # ulrmc_modulation = attr.property.str(key='CONF:LTE:SIGN1:CONN:PCC:RMC:UL', only=['QPSK', 'Q16'])
    # ulrmc_transblocksize = attr.property.int(key='CONF:LTE:SIGN1:CONN:PCC:RMC:UL', min=-1, max=100)

    lte_signaling = attr.property.bool(
        key='SOUR:LTE:SIGN1:CELL:STAT',
    )
    ue_attached = attr.property.bool(key='SENS:LTE:SIGN1:RRCS?')

    ue_rsrp = attr.method.float(key='SENS:LTE:SIGN1:UER:PCC:RSRP?', sets=False)
    ue_rsrq = attr.method.float(key='SENS:LTE:SIGN1:UER:PCC:RSRQ?', sets=False)
    # spectrogram_num_avg      = attr.method.int(key='NEED TO FIND COMMAND',min=1,max=100)

    # @ul_chan_freq.getter
    # def _(self):
    #     command = 'CONF:LTE:SIGN1:RFS:PCC:CHAN:UL? Hz'
    #     return self.query(command)

    # @ulrmc_num_rbs.getter
    # def _(self):
    #     msg = self.query('CONF:LTE:SIGN1:CONN:PCC:RMC:UL?')
    #     value = msg.split(',')[0]
    #     num_rbs = value.split('N')[1]
    #     return num_rbs

    # @ulrmc_modulation.getter
    # def _(self):
    #     msg = self.query('CONF:LTE:SIGN1:CONN:PCC:RMC:UL?')
    #     modulation = msg.split(',')[1]
    #     return modulation

    # @ulrmc_transblocksize.getter
    # def _(self):
    #     msg = self.query('CONF:LTE:SIGN1:CONN:PCC:RMC:UL?')
    #     value = msg.split(',')[2]
    #     if value == 'KEEP':
    #         return -1
    #     if value == 'ZERO':
    #         return 0
    #     value = value.split('T')[1]
    #     return value

    # @ulrmc_num_rbs.setter
    # def _(self, value):
    #     modulation = self.ulrmc_modulation
    #     transblocksize = self.ulrmc_transblocksize
    #     if transblocksize == -1:
    #         transblocksize = 'KEEP'
    #     if transblocksize == 0:
    #         transblocksize = 'ZERO'
    #     if isinstance(transblocksize, int):
    #         transblocksize = 'T' + str(transblocksize)
    #     arg = f'N{value},{modulation},{transblocksize}'
    #     lb.logger.debug(f'ULRMC arg is: {arg}')
    #     self.write(f'CONF:LTE:SIGN1:CONN:PCC:RMC:UL {arg}')

    # @ulrmc_modulation.setter
    # def _(self, value):
    #     num_rbs = self.ulrmc_num_rbs
    #     transblocksize = self.ulrmc_transblocksize
    #     if transblocksize == -1:
    #         transblocksize = 'KEEP'
    #     if transblocksize == 0:
    #         transblocksize = 'ZERO'
    #     if isinstance(transblocksize, int):
    #         transblocksize = 'T' + str(transblocksize)
    #     arg = f'N{num_rbs},{value},{transblocksize}'
    #     lb.logger.debug(f'ULRMC arg is: {arg}')
    #     self.write(f'CONF:LTE:SIGN1:CONN:PCC:RMC:UL {arg}')

    # @ulrmc_transblocksize.setter
    # def _(self, value):
    #     num_rbs = self.ulrmc_num_rbs
    #     modulation = self.ulrmc_modulation
    #     if value == -1:
    #         value = 'KEEP'
    #     if value == 0:
    #         value = 'ZERO'
    #     if isinstance(value, int):
    #         value = 'T' + str(value)
    #     arg = f'N{num_rbs},{modulation},{value}'
    #     lb.logger.debug(f'ULRMC arg is: {arg}')
    #     self.write(f'CONF:LTE:SIGN1:CONN:PCC:RMC:UL {arg}')

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
        if attached:
            return attached
        else:
            raise TimeoutError("UE attach timeout expired")

    def fetch_spectrogram(self):
        """a request to pull the spectrogram down from the cmw500, input
        values are fixed with a RBW of 30kHz and the frequency span x array
        calculated on that assumption.  Would be better to generalize this.
        May also want to add the ability to trigger the measurement
        SCPI = FETC:LTE:MEAS:MEV:TRAC:SEM:RBW:AVER?"""
        values = self.query_ascii_values('FETC:LTE:MEAS:MEV:TRAC:SEM:RBW30:AVER?')
        cent_freq = self.ul_chan_freq
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
        self.scheduling_type = 'UDTT'
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
        self._logger.debug('ul_udtti written, tti:{tti},start_rb:{start_rb},num_rb:{num_rb},mod:{mod}')
        return True


def test_cmw_idn(cmw_resource_string):
    """Use the IDN query to check that the manf and model # match the expected"""
    cmw500 = RohdeSchwarzCMW500(cmw_resource_string)
    cmw500.open()
    cmw_identity = cmw500.query('*IDN?').split(',')
    if cmw_identity[0] == 'Rohde&Schwarz' and cmw_identity[1] == 'CMW':
        cmw500.close()
        return True
    else:
        cmw500.close()
        return False


def test_cmw(cmw_resource_string):
    """Test to:
        1.  connect to the instrument
        2.  set the bandwidth
        3.  set UE target power
        4.  set RMC #RBs
        5.  stand the cell up
        6.  wait for the UE to attach
        7.  shut the cell down.
    This requires the UE to be in a state that in can connect with the instrument"""
    cmw500 = RohdeSchwarzCMW500(cmw_resource_string)
    # import pprint
    # pprint.pprint(dir(cmw500))

    cmw500.open()
    cmw500.reset_cmw()
    cmw500.operating_band = 66
    print(cmw500.operating_band)
    cmw500.duplex_mode = 'FDD'
    print(cmw500.duplex_mode)
    cmw500.cell_bw_mhz = 20
    print(cmw500.cell_bw_mhz)
    cmw500.rs_epre = -50
    print(cmw500.rs_epre)
    cmw500.scheduling_type = 'RMC'
    print(cmw500.scheduling_type)
    # DL stuff
    cmw500.dl_num_rbs =100
    print(cmw500.dl_num_rbs)
    cmw500.dl_start_rb = 0
    print(cmw500.dl_start_rb)
    cmw500.dl_modulation = 'Q256'
    print(cmw500.dl_modulation)
    # UL stuff
    cmw500.ul_num_rbs =100
    print(cmw500.ul_num_rbs)
    cmw500.ul_start_rb = 0
    print(cmw500.ul_start_rb)
    cmw500.ul_modulation = 'Q16'
    print(cmw500.ul_modulation)
    # other cell config
    cmw500.pbch_offset = 0
    print(cmw500.pbch_offset)
    cmw500.pcfich_offset = 0
    print(cmw500.pcfich_offset)
    cmw500.pdcch_offset = 0
    print(cmw500.pdcch_offset)
    cmw500.pss_offset = 0
    print(cmw500.pss_offset)
    cmw500.sss_offset = 0
    print(cmw500.sss_offset)


    # cmw500.pusch_cltp = -21
    # cmw500.ulrmc_num_rbs = 5
    cmw500.lte_signaling = True
    cmw500.wait_for_ue_to_attach(timeout=180)
    cmw500.lte_signaling = False
    cmw500.wait_for_cell_deactivate(timeout=180)
    return True


if __name__ == '__main__':
    default_cmw_address = 'TCPIP0::10.0.0.9::inst0::INSTR'
    # print('IDN test pass: ' + str(test_cmw_idn(default_cmw_address)))
    print('UE Attach test pass: ' + str(test_cmw(default_cmw_address)))
