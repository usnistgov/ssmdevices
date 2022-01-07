# -*- coding: utf-8 -*-

__all__ = ["MiniCircuitsRCDAT", "MiniCircuitsRC4DAT"]

import ssmdevices.lib
import labbench as lb
import time, random

if __name__ == "__main__":
    from _minicircuits_usb import SwitchAttenuatorBase
else:
    from ._minicircuits_usb import SwitchAttenuatorBase


class MiniCircuitsRCDAT(SwitchAttenuatorBase):
    # SwitchAttenuatorBase uses product ID to connect to USB devices
    _PID = 0x23

    frequency = lb.value.float(
        default=None,
        allow_none=True,
        min=10e6,
        max=6e9,
        help="frequency for calibration data (None for no calibration)",
        label="Hz",
    )

    output_power_offset = lb.value.float(
        default=None,
        allow_none=True,
        help="output power level at 0 dB attenuation",
        label="dBm",
    )

    calibration_path = lb.value.str(
        default=None,
        allow_none=True,
        help="path to the calibration table csv file (containing frequency "
        "(row) and attenuation setting (column)), or None to search ssmdevices",
    )

    # the only property that directly sets attenuation in the device
    @lb.property.float(
        min=0, max=115, step=0.25, label="dB", help="uncalibrated attenuation"
    )
    def attenuation_setting(self):
        # getter
        CMD_GET_ATTENUATION = 18

        d = self._cmd(CMD_GET_ATTENUATION)
        full_part = d[1]
        frac_part = float(d[2]) / 4.0
        return full_part + frac_part

    @attenuation_setting
    def attenuation_setting(self, value):
        # setter
        CMD_SET_ATTENUATION = 19

        value1 = int(value)
        value2 = int((value - value1) * 4.0)
        self._cmd(CMD_SET_ATTENUATION, value1, value2, 1)

    # the remaining traits are calibration corrections for attenuation_setting
    attenuation = attenuation_setting.calibrate_from_table(
        path_trait=calibration_path,
        index_lookup_trait=frequency,
        table_index_column='Frequency(Hz)',
        help="calibrated attenuation",
    )

    output_power = attenuation.calibrate_from_expression(
        -attenuation + output_power_offset,
        help="calibrated output power level",
        label="dBm",
    )

class MiniCircuitsRC4DAT(SwitchAttenuatorBase):
    _PID = 0x23

    CMD_GET_ATTENUATION = 18
    CMD_SET_ATTENUATION = 19

    attenuation1 = lb.property.float(min=0, max=115, step=0.25, key=1)
    attenuation2 = lb.property.float(min=0, max=115, step=0.25, key=2)
    attenuation3 = lb.property.float(min=0, max=115, step=0.25, key=3)
    attenuation4 = lb.property.float(min=0, max=115, step=0.25, key=4)

    def get_key(self, key, trait_name=None):
        d = self._cmd(self.CMD_GET_ATTENUATION)
        offs = key * 2 - 1
        full_part = d[offs]
        frac_part = float(d[offs + 1]) / 4.0
        return full_part + frac_part

    def set_key(self, key, value, trait_name=None):
        value1 = int(value)
        value2 = int((value - value1) * 4.0)
        self._cmd(self.CMD_SET_ATTENUATION, value1, value2, key)


if __name__ == "__main__":
    import numpy as np

    lb.show_messages("info")

    for i in np.arange(0, 110.25, 5):
        atten = MiniCircuitsRCDAT("11604210014", frequency=5.3e9)
        atten2 = MiniCircuitsRCDAT("11604210008", frequency=5.3e9)
        with atten, atten2:
            atten.attenuation = i
            # print(atten.output_power)
            lb.logger.info(str(atten.attenuation))
