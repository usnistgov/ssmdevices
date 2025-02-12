__all__ = ['RigolTechnologiesMSO4014', 'TektronixMSO64B', 'TektronixMSO64BSpectrogram']

import labbench as lb
from labbench import paramattr as attr

scope_channel_kwarg = attr.method_kwarg.int(
    'channel', min=1, max=4, help='hardware input port'
)


@scope_channel_kwarg
class RigolTechnologiesMSO4014(lb.VISADevice):
    # used for automatic connection
    make = attr.value.str('RIGOL TECHNOLOGIES', inherit=True)
    model = attr.value.str('MSO4014', inherit=True)

    time_offset = attr.property.float(
        key=':TIM:OFFS',
        label='s',
        help='acquisition time offset relative to the trigger',
    )
    time_scale = attr.property.float(
        key=':TIM:SCAL', label='s', help='acquisition time per division'
    )
    options = attr.property.str(
        key='*OPT', sets=False, cache=True, help='installed license options'
    )

    def open(self, horizontal=False):
        self.write(':WAVeform:FORMat ASCii')

    def fetch(self):
        return self.backend.query_ascii_values(':WAV:DATA?')

    def fetch_rms(self):
        return float(self.backend.query(':MEAS:VRMS?').rstrip().lstrip())


@attr.visa_keying(remap={True: '1', False: '0'})
@scope_channel_kwarg
class TektronixMSO64B(lb.VISADevice):
    # used for automatic connection
    make = attr.value.str('TEKTRONIX', inherit=True)
    model = attr.value.str('MSO64B', inherit=True)
    timeout: float = attr.value.float(3)

    # horizontal acquisition
    record_length = attr.property.int(
        key='HORIZONTAL:RECORDLENGTH', label='samples', help='acquisition record length'
    )
    sample_rate = attr.property.float(key='HOR:SAMPLER', label='S/s', get_on_set=True)
    _horizontal_mode = attr.property.str(
        key='HORizontal:MODe',
        case=False,
        only=('AUTOMATIC', 'MANUAL'),
        help='AUTO automatically adjusts the sample rate and record length',
    )

    # input port parameters
    # TODO: check lower bound
    bandwidth = attr.method.float(
        key='CH{channel}:BANDWIDTH',
        min=0,
        max=8e9,
        label='Hz',
        help='input port analog bandwidth',
    )
    channel_enabled = attr.method.bool(
        key='SELect:CH{channel}',
        help='enable channel acquisition',
    )
    coupling = attr.method.str(
        key='CH{channel}:COUPLING',
        case=False,
        only=('AC', 'DC', 'DCReject'),
        cache=True,
        help='input port coupling mode',
    )
    input_termination = attr.method.float(
        key='CH{channel}:TERMINATION',
        only=(50, 1e6),
        cache=True,
        help='input port termination impedance',
    )
    # Trigger settings
    trig_type = attr.property.str(
        key='TRIGger:A:TYPE',  # Trigger A is hard coded, trigger B only applies to TRANSISTION trigger,\
        # indicated by 'Sequence' on the display
        only=(
            'EDGE',
            'WIDTH',
            'TIMEOUT',
            'RUNT',
            'WINDOW',
            'LOGIC',
            'SETHOLD',
        ),
        help='Trigger mode for captures',
    )
    # Trig width only associated with width type trigger
    trig_width_high = attr.property.float(
        key='TRIGger:A:PULSEWidth:HIGHLimit', min=4e-9, max=5
    )
    trig_width_low = attr.property.float(
        key='TRIGger:A:PULSEWidth:LOWLimit', min=8e-9, max=5
    )


    trig_edge_slope = attr.property.str(
        key='TRIGger:A:EDGE:SLOpe',
        only=("RISE", "FALL", "EITHER")
    )
    trig_edge_source = attr.property.str(
        key='TRIGger:A:EDGE:SOUrce',
        only=('CH1', 'CH2', 'CH3', 'CH4', 'LINE', 'AUX'),
        help='source for edge type trigger'
    )

    trig_level= attr.method.float(
        key='TRIGger:A:LEVel:CH{channel}',
    )

    trig_mode = attr.property.str(
        key='TRIGger:A:MODe',
        only=("AUTO", "NORMAL")
    )

    trig_holdoff_by = attr.property.str(
        key="TRIGger:A:HOLDoff:BY",
        only=("TIME", "RANDOM")
        )

    trig_holdoff_time = attr.property.float(
        key="TRIGger:A:HOLDoff:TIMe",
        min=0,
        max=10
    )

    # Acquisition settings
    acq_type = attr.property.str(
        key="ACQuire:STOPAfter",
        only=("RUNSTOP", "SEQUENCE")
    )
    acq_mode = attr.property.str(
        key="ACQuire:MODe",
        only=("SAMPLE", "PEAKDETECT", "HIRES", "AVERAGE", "ENVELOPE")
    )
    acq_num_seq = attr.property.int(
        key="ACQuire:SEQuence:NUMSEQuence",
    )
    acq_time_source = attr.property.str(
        key="ROSc:SOUrce",
        only=("INTERNAL", "EXTERNAL", "TRACKING")
    )
    acq_fastframe = attr.property.str(
        key="HORizontal:FASTframe:STATE",
        only=("ON", "OFF")
    )

    # vertical scale
    vertical_scale = attr.method.float(
        key='CH{channel}:SCALE',
        label='V',
        help='vertical scale of the specified channel',
    )

    # Data storage, specifically for waveform retrieval over VISA (not implemented)
    data_source = attr.property.str(
        key='DATa:SOUrce',
        only=('CH1',
              'CH2',
              'CH3',
              'CH4'),
        help='data source for acquisition'
    )
    data_start = attr.property.int(
        key='DATa:START',
        help='data collection start point'
    )
    data_stop = attr.property.int(
        key='DATa:STOP',
        help='data collection stop point'
    )

    # File operations
    file_copy = attr.property.str(
        key='FILESystem:COPy', help='copy a file within filesystem'
    )
    file_cwd = attr.property.str(
        key='FILESystem:CWD',
        help='current working directory'
        )
    file_read = attr.property.str(
        key='FILESystem:READFile',
        help='read the file over interface',
    )

    # Store/load
    def load_setup(self, setup_file_name: str):
        self.write(f"RECAll:SETUp \"{setup_file_name}\"")

    def retrieve_waveform(self, channel, tekhsi_port=5000):
        """
        Retrieves the next waveform base on the scope's current acquisition settings.

        args:
        channel -- specifiy the channel number 1-4
        tekhsi_port -- typically 5000, unless it is changed manually on the scope

        returns:
        wfm -- AnalogWaveform type with data, further manipulation needed. See tekhsi docs.
        """
        try:
            from tekhsi import TekHSIConnect, AcqWaitOn
            from tm_data_types import AnalogWaveform
        except ImportError as e:
            raise e("When using the TektronixMSO64B class, ensure tekhsi library is installed.")

        ip_addr = self.resource.split("::")[1]
        self._logger.info(f"Waiting for data on {ip_addr}:{tekhsi_port}")
        with TekHSIConnect(f"{ip_addr}:{tekhsi_port}", [f"ch{channel}"]) as connect:
            with connect.access_data(AcqWaitOn.AnyAcq):
                wfm: AnalogWaveform = connect.get_data(f"ch{channel}")
        return wfm

    def open(self):
        self._horizontal_mode = 'MANUAL'
        self.write(':VERBose 0')
        self.write(':HEADer 0')


class TektronixMSO64BSpectrogram(TektronixMSO64B):
    resolution_bandwidth = attr.property.float(
        key='SV:RBW', label='Hz', help='resolution bandwidth of all channels'
    )
    span = attr.property.float(
        key='SV:SPAN', max=2e9, label='Hz', help='analysis bandwidth per channel'
    )

    # don't log instrument front-end display settings that don't impact the data (log=False)
    _power_scale_min = attr.property.float(
        key='SV:SPECtrogram:CSCale:MIN',
        min=-170,
        max=99,
        log=False,
        label='dBm',
        help='spectrogram display power scale minimum',
    )
    _power_scale_max = attr.property.float(
        key='SV:SPECtrogram:CSCale:MAX',
        min=-170,
        max=99,
        log=False,
        label='dBm',
        help='spectrogram display power scale maximum',
    )

    # assume that these are only set once, so relegate them to metadata (cache=True)
    _sync_center_frequencies = attr.property.bool(
        key='SV:LOCKCenter',
        cache=True,
        help='whether to lock all channels to the same center frequency',
    )
    _resolution_bandwidth_mode = attr.property.str(
        key='SV:RBWMode',
        case=False,
        only=('AUTOMATIC', 'MANUAL'),
        cache=True,
        help='whether to automatically set analysis parameters to achieve a specified RBW',
    )

    center_frequency = attr.method.float(
        key='CH{channel}:SV:CENTERFrequency',
        max=8e9,
        label='Hz',
        help='channel center frequency',
    )

    bandwidth = attr.method.float(
        # TODO: check min
        key='CH{channel}:BANDWIDTH',
        min=0,
        max=8e9,
        label='Hz',
        help='channel analysis bandwidth',
    )

    # log=False here since we intend usage of spectrogram_enabled
    _only_spectrogram_enabled = attr.method.bool(
        key='SV:CH{channel}:SEL:SPEC',
        log=False,
        help='enable channel spectrogram analysis',
    )

    _only_spectrumview_enabled = attr.method.bool(
        key='CH{channel}:SV:STATE',
        log=False,
        help='enable channel spectrum view mode',
    )

    @attr.method.bool(help='channel center frequency')
    @scope_channel_kwarg
    def spectrogram_enabled(self, enabled: bool = lb.Undefined, /, *, channel: int):
        return all(
            [
                self.channel_enabled(enabled, channel),
                self._only_spectrumview_enabled(enabled, channel),
                self._only_spectrogram_enabled(enabled, channel),
            ]
        )

    def open(self):
        self._resolution_bandwidth_mode = 'MANUAL'
        self._sync_center_frequencies = False


if __name__ == '__main__':
    with TektronixMSO64B() as scope:
        # Load some setup file onboard the scope
        scope.load_setup("default_setup.set")
        # Manually set some params
        scope.sample_rate = 200e6
        scope.record_length = 20e6
        scope.trig_type = "EDGE"
        scope.trig_edge_source = "CH1"
        scope.trig_mode = "AUTO"
        scope.trig_holdoff_by = "RANDOM"
        scope.acq_type = "RUNSTOP"

        # Collect data from scope after an acquisition
        data = scope.retrieve_waveform(1)
        print(data.normalized_vertical_values)

    with TektronixMSO64BSpectrogram() as scope:
        scope.spectrogram_enabled(channel=1)

        scope.resolution_bandwidth = 10e3
        scope.span = 2e9

        scope.coupling('AC', channel=1)
        scope.bandwidth(8e9, channel=1)
        scope.input_termination(50, channel=1)
        scope.center_frequency(3e9, channel=1)
        scope.vertical_scale(0.05, channel=1)
