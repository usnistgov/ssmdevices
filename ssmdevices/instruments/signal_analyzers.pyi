import labbench as lb
from typing import Any, Optional


class RohdeSchwarzFSW26Base(lb.VISADevice):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str',
        default_window: str='str',
        default_trace: str='str'
    ):
        ...
    default_window: Any = ...
    default_trace: Any = ...
    frequency_center: Any = ...
    frequency_span: Any = ...
    frequency_start: Any = ...
    frequency_stop: Any = ...
    resolution_bandwidth: Any = ...
    sweep_time: Any = ...
    sweep_time_window2: Any = ...
    initiate_continuous: Any = ...
    reference_level: Any = ...
    reference_level_trace2: Any = ...
    reference_level_trace3: Any = ...
    reference_level_trace4: Any = ...
    reference_level_trace5: Any = ...
    reference_level_trace6: Any = ...
    amplitude_offset: Any = ...
    amplitude_offset_trace2: Any = ...
    amplitude_offset_trace3: Any = ...
    amplitude_offset_trace4: Any = ...
    amplitude_offset_trace5: Any = ...
    amplitude_offset_trace6: Any = ...
    output_trigger2_direction: Any = ...
    output_trigger3_direction: Any = ...
    output_trigger2_type: Any = ...
    output_trigger3_type: Any = ...
    input_preamplifier_enabled: Any = ...
    input_attenuation_auto: Any = ...
    input_attenuation: Any = ...
    channel_type: Any = ...
    format: Any = ...
    sweep_points: Any = ...
    display_update: Any = ...
    expected_channel_type: Any = ...
    cache_dir: str = ...

    def verify_channel_type(self) -> None:
        ...

    @classmethod
    def __imports__(cls) -> None:
        ...

    def open(self) -> None:
        ...

    def acquire_spectrogram(self, acquisition_time_sec: Any):
        ...

    def close(self) -> None:
        ...

    def clear_status(self) -> None:
        ...

    def status_preset(self) -> None:
        ...

    def save_state(self, name: Any, basedir: Optional[Any]=...) -> None:
        ...

    def load_state(self, name: Any, basedir: Optional[Any]=...) -> None:
        ...

    def load_cache(self):
        ...

    def save_cache(self) -> None:
        ...

    def mkdir(self, path: Any, recursive: bool=...):
        ...

    def file_info(self, path: Any):
        ...

    def remove_window(self, name: Any) -> None:
        ...

    def trigger_single(self, wait: bool=..., disable_continuous: bool=...) -> None:
        ...

    def autolevel(self) -> None:
        ...

    def abort(self) -> None:
        ...

    def set_channel_type(self, type_: Optional[Any]=...) -> None:
        ...

    def channel_preset(self) -> None:
        ...

    def query_ieee_array(self, msg: Any):
        ...

    def fetch_horizontal(self, window: Optional[Any]=..., trace: Optional[Any]=...):
        ...

    def fetch_trace(self, trace: Optional[Any]=..., horizontal: bool=..., window: Optional[Any]=...):
        ...

    def fetch_timestamps(self, window: Optional[Any]=..., all: bool=..., timeout: int=...):
        ...

    def fetch_spectrogram(
        self,
        window: Optional[Any]=...,
        freqs: str=...,
        timestamps: str=...,
        timeout: Optional[Any]=...
    ):
        ...

    def fetch_marker(self, marker: Any, axis: Any):
        ...

    def get_marker_enables(self):
        ...

    def get_marker_power(self, marker: Any):
        ...

    def get_marker_position(self, marker: Any):
        ...

    def set_marker_position(self, marker: Any, position: Any):
        ...

    def trigger_output_pulse(self, port: Any) -> None:
        ...


class RohdeSchwarzFSW26SpectrumAnalyzer(RohdeSchwarzFSW26Base):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str',
        default_window: str='str',
        default_trace: str='str'
    ):
        ...
    expected_channel_type: str = ...

    def get_marker_band_power(self, marker: Any):
        ...

    def get_marker_band_span(self, marker: Any):
        ...

    def get_marker_power_table(self):
        ...

    def fetch_marker_bpow(self, marker: Any):
        ...

    def fetch_marker_bpow_span(self, marker: Any):
        ...


class RohdeSchwarzFSW26LTEAnalyzer(RohdeSchwarzFSW26Base):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str',
        default_window: str='str',
        default_trace: str='str'
    ):
        ...
    format: Any = ...

    def uplink_sample_rate(self):
        ...

    def downlink_sample_rate(self):
        ...

    def open(self) -> None:
        ...

    def fetch_power_vs_symbol_x_carrier(self, window: Any, trace: Any):
        ...

    def get_ascii_window_trace(self, window: Any, trace: Any):
        ...

    def get_binary_window_trace(self, window: Any, trace: Any):
        ...

    def get_allocation_summary(self, window: Any):
        ...


class RohdeSchwarzFSW26IQAnalyzer(RohdeSchwarzFSW26Base):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str',
        default_window: str='str',
        default_trace: str='str'
    ):
        ...
    expected_channel_type: str = ...
    iq_simple_enabled: Any = ...
    iq_evaluation_enabled: Any = ...
    iq_mode: Any = ...
    iq_record_length: Any = ...
    iq_sample_rate: Any = ...
    iq_format: Any = ...
    iq_format_window2: Any = ...

    def fetch_trace(self, horizontal: bool=..., trace: Optional[Any]=...):
        ...

    def store_trace(self, path: Any) -> None:
        ...


class RohdeSchwarzFSW26RealTime(RohdeSchwarzFSW26Base):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str',
        default_window: str='str',
        default_trace: str='str'
    ):
        ...
    expected_channel_type: str = ...
    trigger_source: Any = ...
    trigger_post_time: Any = ...
    trigger_pre_time: Any = ...
    iq_fft_length: Any = ...
    iq_bandwidth: Any = ...
    iq_sample_rate: Any = ...
    iq_trigger_position: Any = ...
    sweep_dwell_auto: Any = ...
    sweep_dwell_time: Any = ...
    sweep_window_type: Any = ...

    def store_spectrogram(self, path: Any, window: int=...) -> None:
        ...

    def clear_spectrogram(self, window: int=...) -> None:
        ...

    def fetch_horizontal(self, window: int=..., trace: int=...):
        ...

    def set_detector_type(self, type_: Any, window: Optional[Any]=..., trace: Optional[Any]=...) -> None:
        ...

    def get_detector_type(self, window: Optional[Any]=..., trace: Optional[Any]=...):
        ...

    def set_spectrogram_depth(self, depth: Any, window: Optional[Any]=...) -> None:
        ...

    def get_spectrogram_depth(self, window: Optional[Any]=...):
        ...

    def trigger_mask_threshold(self):
        ...

    def set_frequency_mask(
        self,
        thresholds: Any,
        frequency_offsets: Optional[Any]=...,
        kind: str=...,
        window: Optional[Any]=...
    ) -> None:
        ...

    def get_frequency_mask(
        self,
        kind: str=...,
        window: Optional[Any]=...,
        first_threshold_only: bool=...
    ):
        ...
    default_window: int = ...
    default_trace: int = ...
    frequency_center: Any = ...
    initiate_continuous: bool = ...
    frequency_span: Any = ...
    reference_level: Any = ...
    input_attenuation: Any = ...
    input_preamplifier_enabled: bool = ...
    sweep_time_window2: Any = ...
    spectrogram_depth: int = ...
    output_trigger2_direction: str = ...
    output_trigger2_type: str = ...
    output_trigger3_direction: str = ...
    output_trigger3_type: str = ...

    def setup_spectrogram(
        self,
        center_frequency: Any,
        analysis_bandwidth: Any,
        reference_level: Any,
        time_resolution: Any,
        acquisition_time: Any,
        input_attenuation: Optional[Any]=...,
        trigger_threshold: Optional[Any]=...,
        detector: str=...,
        analysis_window: Optional[Any]=...,
        **kws: Any
    ) -> None:
        ...

    def acquire_spectrogram_sequence(
        self,
        loop_time: Optional[Any]=...,
        delay_time: float=...,
        timestamps: str=...
    ):
        ...

    def arm_spectrogram(self) -> None:
        ...

    def acquire_spectrogram(self):
        ...