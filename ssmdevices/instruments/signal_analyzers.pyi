import labbench as lb
from _typeshed import Incomplete

class RohdeSchwarzFSWBase(lb.VISADevice):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    expected_channel_type: Incomplete
    default_window: Incomplete
    default_trace: Incomplete
    frequency_center: Incomplete
    frequency_span: Incomplete
    frequency_start: Incomplete
    frequency_stop: Incomplete
    resolution_bandwidth: Incomplete
    sweep_time: Incomplete
    sweep_time_window2: Incomplete
    initiate_continuous: Incomplete
    reference_level: Incomplete
    reference_level_trace2: Incomplete
    reference_level_trace3: Incomplete
    reference_level_trace4: Incomplete
    reference_level_trace5: Incomplete
    reference_level_trace6: Incomplete
    amplitude_offset: Incomplete
    amplitude_offset_trace2: Incomplete
    amplitude_offset_trace3: Incomplete
    amplitude_offset_trace4: Incomplete
    amplitude_offset_trace5: Incomplete
    amplitude_offset_trace6: Incomplete
    output_trigger2_direction: Incomplete
    output_trigger3_direction: Incomplete
    output_trigger2_type: Incomplete
    output_trigger3_type: Incomplete
    input_preamplifier_enabled: Incomplete
    input_attenuation_auto: Incomplete
    input_attenuation: Incomplete
    channel_type: Incomplete
    format: Incomplete
    sweep_points: Incomplete
    display_update: Incomplete

    def verify_channel_type(self) -> None: ...
    @classmethod
    def __imports__(cls) -> None: ...
    def open(self) -> None: ...
    def acquire_spectrogram(self, acquisition_time_sec): ...
    def close(self) -> None: ...
    def clear_status(self) -> None: ...
    def status_preset(self) -> None: ...
    def save_state(self, name, basedir: Incomplete | None = ...) -> None: ...
    def load_state(self, name, basedir: Incomplete | None = ...) -> None: ...
    def load_cache(self): ...
    def save_cache(self) -> None: ...
    def mkdir(self, path, recursive: bool = ...): ...
    def file_info(self, path): ...
    def remove_window(self, name) -> None: ...
    def trigger_single(
        self, wait: bool = ..., disable_continuous: bool = ...
    ) -> None: ...
    def autolevel(self) -> None: ...
    def abort(self) -> None: ...
    def apply_channel_type(self, type_: Incomplete | None = ...) -> None: ...
    def channel_preset(self) -> None: ...
    def query_ieee_array(self, msg): ...
    def fetch_horizontal(
        self, window: Incomplete | None = ..., trace: Incomplete | None = ...
    ): ...
    def fetch_trace(
        self,
        trace: Incomplete | None = ...,
        horizontal: bool = ...,
        window: Incomplete | None = ...,
    ): ...
    def fetch_timestamps(
        self, window: Incomplete | None = ..., all: bool = ..., timeout: int = ...
    ): ...
    def fetch_spectrogram(
        self,
        window: Incomplete | None = ...,
        freqs: str = ...,
        timestamps: str = ...,
        timeout: Incomplete | None = ...,
    ): ...
    def fetch_marker(self, marker, axis): ...
    def get_marker_enables(self): ...
    def get_marker_power(self, marker): ...
    def get_marker_position(self, marker: int) -> float: ...
    def set_marker_position(self, marker: int, position: float): ...
    def trigger_output_pulse(self, port) -> None: ...

class RohdeSchwarzSpectrumAnalyzerMixIn(RohdeSchwarzFSWBase):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    def get_marker_band_power(self, marker: int) -> float: ...
    def get_marker_band_span(self, marker: int) -> float: ...
    def get_marker_power_table(self): ...
    def fetch_marker_bpow(self, marker): ...
    def fetch_marker_bpow_span(self, marker): ...

class RohdeSchwarzLTEAnalyzerMixIn(RohdeSchwarzFSWBase):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    format: Incomplete

    def uplink_sample_rate(self): ...
    def downlink_sample_rate(self): ...
    def open(self) -> None: ...
    def fetch_power_vs_symbol_x_carrier(self, window, trace): ...
    def get_ascii_window_trace(self, window, trace): ...
    def get_binary_window_trace(self, window, trace): ...
    def get_allocation_summary(self, window): ...

class RohdeSchwarzIQAnalyzerMixIn(RohdeSchwarzFSWBase):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    iq_simple_enabled: Incomplete
    iq_evaluation_enabled: Incomplete
    iq_mode: Incomplete
    iq_record_length: Incomplete
    iq_sample_rate: Incomplete
    iq_format: Incomplete
    iq_format_window2: Incomplete

    def fetch_trace(self, horizontal: bool = ..., trace: Incomplete | None = ...): ...
    def store_trace(self, path) -> None: ...

class RohdeSchwarzRealTimeMixIn(RohdeSchwarzFSWBase):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    TRIGGER_SOURCES: Incomplete
    WINDOW_FUNCTIONS: Incomplete
    trigger_source: Incomplete
    trigger_post_time: Incomplete
    trigger_pre_time: Incomplete
    iq_fft_length: Incomplete
    iq_bandwidth: Incomplete
    iq_sample_rate: Incomplete
    iq_trigger_position: Incomplete
    sweep_dwell_auto: Incomplete
    sweep_dwell_time: Incomplete
    sweep_window_type: Incomplete

    def store_spectrogram(self, path, window: int = ...) -> None: ...
    def clear_spectrogram(self, window: int = ...) -> None: ...
    def fetch_horizontal(self, window: int = ..., trace: int = ...): ...
    def set_detector_type(
        self, type_, window: Incomplete | None = ..., trace: Incomplete | None = ...
    ) -> None: ...
    def get_detector_type(
        self, window: Incomplete | None = ..., trace: Incomplete | None = ...
    ): ...
    def set_spectrogram_depth(self, depth, window: Incomplete | None = ...) -> None: ...
    def get_spectrogram_depth(self, window: Incomplete | None = ...): ...
    def set_frequency_mask(
        self,
        thresholds,
        frequency_offsets: Incomplete | None = ...,
        kind: str = ...,
        window: Incomplete | None = ...,
    ) -> None: ...
    def get_frequency_mask(
        self,
        kind: str = ...,
        window: Incomplete | None = ...,
        first_threshold_only: bool = ...,
    ): ...
    default_window: int
    default_trace: int
    frequency_center: Incomplete
    initiate_continuous: bool
    frequency_span: Incomplete
    reference_level: Incomplete
    input_attenuation: Incomplete
    input_preamplifier_enabled: bool
    sweep_time_window2: Incomplete
    spectrogram_depth: int
    output_trigger2_direction: str
    output_trigger2_type: str
    output_trigger3_direction: str
    output_trigger3_type: str

    def setup_spectrogram(
        self,
        center_frequency,
        analysis_bandwidth,
        reference_level,
        time_resolution,
        acquisition_time,
        input_attenuation: Incomplete | None = ...,
        trigger_threshold: Incomplete | None = ...,
        detector: str = ...,
        analysis_window: Incomplete | None = ...,
    ) -> None: ...
    def acquire_spectrogram_sequence(
        self,
        loop_time: Incomplete | None = ...,
        delay_time: float = ...,
        timestamps: str = ...,
    ): ...
    def arm_spectrogram(self) -> None: ...
    def acquire_spectrogram(self): ...

class RohdeSchwarzFSW26Base(RohdeSchwarzFSWBase):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    frequency_center: Incomplete
    frequency_span: Incomplete
    frequency_start: Incomplete
    frequency_stop: Incomplete
    resolution_bandwidth: Incomplete

class RohdeSchwarzFSW26SpectrumAnalyzer(
    RohdeSchwarzFSW26Base, RohdeSchwarzSpectrumAnalyzerMixIn
):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...

class RohdeSchwarzFSW26LTEAnalyzer(RohdeSchwarzFSW26Base, RohdeSchwarzLTEAnalyzerMixIn):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...

class RohdeSchwarzFSW26IQAnalyzer(RohdeSchwarzFSW26Base, RohdeSchwarzIQAnalyzerMixIn):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...

class RohdeSchwarzFSW26RealTime(RohdeSchwarzFSW26Base, RohdeSchwarzRealTimeMixIn):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...

class RohdeSchwarzFSW43Base(RohdeSchwarzFSWBase):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    frequency_center: Incomplete
    frequency_span: Incomplete
    frequency_start: Incomplete
    frequency_stop: Incomplete
    resolution_bandwidth: Incomplete

class RohdeSchwarzFSW43SpectrumAnalyzer(
    RohdeSchwarzFSW43Base, RohdeSchwarzSpectrumAnalyzerMixIn
):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...

class RohdeSchwarzFSW43LTEAnalyzer(RohdeSchwarzFSW43Base, RohdeSchwarzLTEAnalyzerMixIn):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...

class RohdeSchwarzFSW43IQAnalyzer(RohdeSchwarzFSW43Base, RohdeSchwarzIQAnalyzerMixIn):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...

class RohdeSchwarzFSW43RealTime(RohdeSchwarzFSW43Base, RohdeSchwarzRealTimeMixIn):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
        default_window: str = "str",
        default_trace: str = "str",
    ): ...
    ...
