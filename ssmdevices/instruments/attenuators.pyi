from typing import Any, Optional


class MiniCircuitsRCDAT(SwitchAttenuatorBase):

    def __init__(
        self,
        resource: str='NoneType',
        usb_path: str='NoneType',
        timeout: str='int',
        frequency: str='NoneType',
        output_power_offset: str='NoneType',
        calibration_path: str='NoneType'
    ):
        ...
    frequency: Any = ...
    output_power_offset: Any = ...
    calibration_path: Any = ...

    def open(self) -> None:
        ...
    attenuation_setting: Any = ...

    def attenuation_setting(self, value: Any) -> None:
        ...
    attenuation: Any = ...
    output_power: Any = ...


class MiniCircuitsRC4DAT(SwitchAttenuatorBase):

    def __init__(self, resource: str='NoneType', usb_path: str='NoneType', timeout: str='int'):
        ...
    CMD_GET_ATTENUATION: int = ...
    CMD_SET_ATTENUATION: int = ...
    attenuation1: Any = ...
    attenuation2: Any = ...
    attenuation3: Any = ...
    attenuation4: Any = ...

    def get_key(self, key: Any, trait_name: Optional[Any]=...):
        ...

    def set_key(self, key: Any, value: Any, trait_name: Optional[Any]=...) -> None:
        ...