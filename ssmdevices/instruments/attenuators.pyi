__all__ = ['MiniCircuitsRCDAT']
import time
import labbench as lb
from labbench import paramattr as attr
if __name__ == '__main__':
    from _minicircuits_usb import SwitchAttenuatorBase
else:
    from ._minicircuits_usb import SwitchAttenuatorBase


class MiniCircuitsRCDAT(SwitchAttenuatorBase):

    def __init__(
        self,
        resource: str='NoneType',
        usb_path: str='NoneType',
        timeout: str='int',
        frequency: str='NoneType',
        output_power_offset: str='NoneType',
        calibration_path: str='NoneType',
        channel: str='int'
    ):
        ...
    _PID = 35
    frequency: float = attr.value.float(
        default=None,
        allow_none=True,
        min=10000000.0,
        max=6000000000.0,
        help='frequency for calibration data (None for no calibration)',
        label='Hz'
    )
    output_power_offset: float = attr.value.float(
        default=None,
        allow_none=True,
        help='output power level at 0 dB attenuation',
        label='dBm'
    )
    calibration_path: float = attr.value.str(
        default=None,
        allow_none=True,
        cache=True,
        help='path to the calibration table csv file (containing frequency (row) and attenuation setting (column)), or None to search ssmdevices'
    )
    channel: int = attr.value.int(
        default=1,
        allow_none=True,
        min=1,
        max=4,
        cache=True,
        help='a port selector for 4 port attenuators None is a single attenuator'
    )

    @attr.property.float(min=0, max=115, step=0.25, label='dB', help='uncalibrated attenuation')
    def attenuation_setting(self):
        CMD_GET_ATTENUATION = 18
        if self.channel is None:
            d = self._cmd(CMD_GET_ATTENUATION)
            full_part = d[1]
            frac_part = float(d[2]) / 4.0
            return full_part + frac_part
        elif self.channel in range(1, 5):
            d = self._cmd(CMD_GET_ATTENUATION)
            offs = self.channel * 2 - 1
            full_part = d[offs]
            frac_part = float(d[(offs + 1)]) / 4.0
            return full_part + frac_part
        else:
            raise AttributeError

    @attenuation_setting
    def attenuation_setting(self, set_value):
        CMD_SET_ATTENUATION = 19
        if self.channel is None:
            value1 = int(set_value)
            value2 = int((set_value - value1) * 4.0)
            self._cmd(CMD_SET_ATTENUATION, value1, value2, 1)
        elif self.channel in range(1, 5):
            value1 = int(set_value)
            value2 = int((set_value - value1) * 4.0)
            self._cmd(CMD_SET_ATTENUATION, value1, value2, self.channel)
            time.sleep(0.001)
        else:
            raise AttributeError
    attenuation = attenuation_setting.calibrate_from_table(
        allow_none=True,
        path_attr=calibration_path,
        index_lookup_attr=frequency,
        table_index_column='Frequency(Hz)',
        help='calibrated attenuation'
    )
    output_power = attenuation.calibrate_from_expression(
        -attenuation + output_power_offset,
        help='calibrated output power level',
        label='dBm'
    )
if __name__ == '__main__':
    import numpy as np
    check_single_channel = True
    check_four_channel = False
    resource = '12104060052'
    lb.show_messages('info')
    if check_single_channel:
        for i in np.arange(0, 110.25, 5):
            atten = MiniCircuitsRCDAT(resource, frequency=5300000000.0)
            with atten:
                atten.attenuation_setting = i
                print(f'Attenuator set point {str(atten.attenuation_setting)}')
    if check_four_channel:
        for i in np.arange(0, 110.25, 5):
            atten1 = MiniCircuitsRCDAT(resource, frequency=5300000000.0, channel=1)
            atten2 = MiniCircuitsRCDAT(resource, frequency=5300000000.0, channel=2)
            atten3 = MiniCircuitsRCDAT(resource, frequency=5300000000.0, channel=3)
            atten4 = MiniCircuitsRCDAT(resource, frequency=5300000000.0, channel=4)
            with atten1, atten2, atten3, atten4:
                atten1.attenuation_setting = i
                atten2.attenuation_setting = i
                atten3.attenuation_setting = i
                atten4.attenuation_setting = i
                print(f'Attenuator 1 set point {str(atten1.attenuation_setting)}')
                print(f'Attenuator 2 set point {str(atten2.attenuation_setting)}')
                print(f'Attenuator 3 set point {str(atten3.attenuation_setting)}')
                print(f'Attenuator 4 set point {str(atten4.attenuation_setting)}')
