import labbench as lb
from _typeshed import Incomplete


class RohdeSchwarzSMW200A(lb.VISADevice):

    def __init__(
        self,
        resource: str='str',
        read_termination: str='str',
        write_termination: str='str'
    ):
        ...
    frequency_center: Incomplete
    rf_output_power: Incomplete
    rf_output_enable: Incomplete

    def save_state(self, FileName, num: str=...) -> None:
        ...

    def load_state(self, FileName, opc: bool=..., num: str=...) -> None:
        ...
