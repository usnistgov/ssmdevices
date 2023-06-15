import labbench as lb
from _typeshed import Incomplete

class KeysightU2000XSeries(lb.VISADevice):
    def __init__(
        self,
        resource: str = "str",
        read_termination: str = "str",
        write_termination: str = "str",
    ): ...
    TRIGGER_SOURCES: Incomplete
    initiate_continuous: Incomplete
    output_trigger: Incomplete
    trigger_source: Incomplete
    trigger_count: Incomplete
    measurement_rate: Incomplete
    sweep_aperture: Incomplete
    frequency: Incomplete

    def preset(self) -> None: ...
    def fetch(self): ...

class RohdeSchwarzNRPSeries(lb.VISADevice):
    def __init__(self, resource: str = "str", write_termination: str = "str"): ...
    FUNCTIONS: Incomplete
    TRIGGER_SOURCES: Incomplete
    frequency: Incomplete
    initiate_continuous: Incomplete

    def function(self, value) -> None: ...
    def trigger_source(self): ...
    trigger_delay: Incomplete
    trigger_count: Incomplete
    trigger_holdoff: Incomplete
    trigger_level: Incomplete
    trace_points: Incomplete
    trace_realtime: Incomplete
    trace_time: Incomplete
    trace_offset_time: Incomplete
    trace_average_count: Incomplete
    trace_average_mode: Incomplete
    trace_average_enable: Incomplete
    average_count: Incomplete
    average_auto: Incomplete
    average_enable: Incomplete
    smoothing_enable: Incomplete
    read_termination: Incomplete

    def preset(self) -> None: ...
    def trigger_single(self) -> None: ...
    def fetch(self): ...
    def fetch_buffer(self): ...
    def setup_trace(
        self,
        frequency,
        trace_points,
        sample_period,
        trigger_level,
        trigger_delay,
        trigger_source,
    ) -> None: ...

class RohdeSchwarzNRP8s(RohdeSchwarzNRPSeries):
    def __init__(self, resource: str = "str", write_termination: str = "str"): ...
    frequency: Incomplete

class RohdeSchwarzNRP18s(RohdeSchwarzNRPSeries):
    def __init__(self, resource: str = "str", write_termination: str = "str"): ...
    frequency: Incomplete
