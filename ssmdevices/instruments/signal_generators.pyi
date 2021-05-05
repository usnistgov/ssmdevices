import labbench as lb
from typing import Any


class RohdeSchwarzSMW200A(lb.VISADevice):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str'
    ):
        ...
    frequency_center: Any = ...
    rf_output_power: Any = ...
    rf_output_enable: Any = ...

    def save_state(self, FileName: Any, num: str=...) -> None:
        ...

    def load_state(self, FileName: Any, opc: bool=..., num: str=...) -> None:
        ...
