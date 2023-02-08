from _typeshed import Incomplete


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
    frequency: Incomplete
    output_power_offset: Incomplete
    calibration_path: Incomplete
    attenuation: Incomplete
    output_power: Incomplete


class MiniCircuitsRC4DAT(SwitchAttenuatorBase):

    def __init__(self, resource: str='NoneType', usb_path: str='NoneType', timeout: str='int'):
        ...
    CMD_GET_ATTENUATION: int
    CMD_SET_ATTENUATION: int
    attenuation1: Incomplete
    attenuation2: Incomplete
    attenuation3: Incomplete
    attenuation4: Incomplete

    def get_key(self, key, trait_name: Incomplete | None=...):
        ...

    def set_key(self, key, value, trait_name: Incomplete | None=...) -> None:
        ...
