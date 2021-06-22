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
        help="output power level calibrated at 0 dB attenuation",
        label="dBm",
    )

    calibration_path = lb.value.str(
        default=None,
        allow_none=True,
        help="path to the calibration table, which is a csv with frequency "
        "(columns) and attenuation setting (row), or None to search ssmdevices",
    )

    _PID = 0x23

    def open(self):
        import pandas as pd
        from pathlib import Path

        def read(path):
            # quick read
            self._cal = pd.read_csv(str(path), index_col="Frequency(Hz)", dtype=float)
            self._cal.columns = self._cal.columns.astype(float)
            if self._traits["frequency"].max in self._cal.index:
                self._cal.drop(self._traits["frequency"].max, axis=0, inplace=True)
            #    self._cal_offset.values[:] = self._cal_offset.values-self._cal_offset.columns.values[np.newaxis,:]

            self._logger.debug(f"calibration data read from {path}")

        if self.calibration_path is None:
            cal_path = Path(ssmdevices.lib.path("cal"))
            cal_filenames = (
                f"MiniCircuitsRCDAT_{self.resource}.csv.xz",
                f"MiniCircuitsRCDAT_default.csv.xz",
            )

            for f in cal_filenames:
                if (cal_path / f).exists():
                    read(str(cal_path / f))
                    self.calibration_path = str(cal_path / f)
                    break
            else:
                self._cal_data = None
                self._logger.debug(f"found no calibration data in {str(cal_path)}")
        else:
            read(self.calibration_path)

        lb.observe(self, self._update_frequency, name="frequency", type_="set")
        lb.observe(
            self, self._logger_debug, type_="set", name=("attenuation", "output_power")
        )

        # trigger cal update
        self.frequency = self.frequency

    # the requested attenuation is the only property that directly interacts
    # with the device
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
        self._logger.debug(f"uncalibrated attenuation set to {value:0.2f} dB")

    # the remaining traits are calibration corrections for attenuation_setting
    attenuation = attenuation_setting.calibrate(
        lookup=None,
        help="calibrated attenuation (set settings.calibration_path and settings.frequency to enable)",
    )

    _transmission = -attenuation

    output_power = _transmission.calibrate(
        offset_name="output_power_offset",
        help="calibrated power level at attenuator output",
        label="dBm",
    )

    def _update_frequency(self, msg):
        """match the calibration table to the frequency"""
        if self._cal is None:
            return

        frequency = msg["new"]
        if frequency is None:
            cal = None
            txt = f"set {msg['owner'].frequency} to enable calibration"
        else:
            # pull in the calibration table specific at this frequency
            i_freq = self._cal.index.get_loc(frequency, "nearest")
            cal = self._cal.iloc[i_freq]
            txt = f"calibrated at {frequency/1e6:0.3f} MHz"

        self._traits["attenuation"].set_table(cal, owner=self)
        self._logger.debug(txt)

    def _logger_debug(self, msg):
        """debug messages"""

        if msg["new"] == msg["old"]:
            # only log on changes
            return

        name = msg["name"]
        if name == "attenuation" and self.frequency is not None:
            cal = msg["new"]
            uncal = self._traits["attenuation"].find_uncal(cal, self)
            txt = f"calibrated attenuation set to {cal:0.2f} dB"
            self._logger.debug(txt)
        elif name == "output_power":
            uncal = msg["new"]
            label = self._traits["output_power"].label
            self._logger.debug(f"output_power set to {uncal:0.2f} {label}")


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
