# -*- coding: utf-8 -*-

__all__ = [
    "KeysightU2000XSeries",
    "RohdeSchwarzNRP8s",
    "RohdeSchwarzNRP18s",
    "RohdeSchwarzNRPSeries",
]

import labbench as lb
from labbench import paramattr as attr
import pandas as pd
import numpy as np
import typing


@attr.adjust("make", "Keysight Technologies")
@attr.adjust("model", "U204")
class KeysightU2000XSeries(lb.VISADevice):
    """Coaxial power sensors connected by USB"""

    _TRIGGER_SOURCES = ("IMM", "INT", "EXT", "BUS", "INT1")

    initiate_continuous = attr.property.bool(key="INIT:CONT")
    output_trigger = attr.property.bool(key="OUTP:TRIG")
    trigger_source = attr.property.str(
        key="TRIG:SOUR", case=False, only=_TRIGGER_SOURCES
    )
    trigger_count = attr.property.int(key="TRIG:COUN", min=1, max=200)
    measurement_rate = attr.property.str(
        key="SENS:MRAT", only=("NORM", "DOUB", "FAST"), case=False
    )
    sweep_aperture = attr.property.float(
        key="SWE:APER", min=20e-6, max=200e-3, help="time", label="s"
    )
    frequency = attr.property.float(
        key="SENS:FREQ",
        min=10e6,
        max=18e9,
        step=1e-3,
        help="input signal center frequency (in Hz)",
    )
    auto_calibration = attr.property.bool(key="CAL:ZERO:AUTO")
    options = attr.property.str(
        key="*OPT", sets=False, cache=True, help="installed license options"
    )

    def preset(self, wait=True) -> None:
        """restore the instrument to its default state"""
        self.write("SYST:PRES")
        if wait:
            self.wait()

    def fetch(self) -> typing.Union[float, pd.Series]:
        """return power readings from the instrument.

        Returns:
            a single number if trigger_count == 1, otherwise or pandas.Series"""
        response = self.query("FETC?").split(",")
        if len(response) == 1:
            return float(response[0])
        else:
            df = pd.to_numeric(pd.Series(response))
            df.index = pd.Index(
                self.sweep_aperture * np.arange(len(df)), name="Time elapsed (s)"
            )
            df.columns.name = "Power (dBm)"
            return df

    def calibrate(self) -> None:
        if int(self.query("CAL?")) != 0:
            raise ValueError("calibration failed")


class RohdeSchwarzNRPSeries(lb.VISADevice):
    """Coaxial power sensors connected by USB.

    These require the installation of proprietary drivers from the vendor website.
    Resource strings for connections take the form 'RSNRP::0x00e2::103892::INSTR'.
    """

    _FUNCTIONS = ("POW:AVG", "POW:BURS:AVG", "POW:TSL:AVG", "XTIM:POW", "XTIM:POWer")
    _TRIGGER_SOURCES = ("HOLD", "IMM", "INT", "EXT", "EXT1", "EXT2", "BUS", "INT1")

    # Instrument state traits (pass command arguments and/or implement setter/getter)
    frequency = attr.property.float(
        key="SENS:FREQ", min=10e6, step=1e-3, label="Hz", help="calibration frequency"
    )
    initiate_continuous = attr.property.bool(key="INIT:CONT")
    options = attr.property.str(
        key="*OPT", sets=False, cache=True, help="installed license options"
    )

    @attr.property.str(key="SENS:FUNC", case=False, only=_FUNCTIONS).setter
    def function(self, value):
        # Special case - this message requires quotes around the argument
        self.write(f'SENSe:FUNCtion "{value}"')

    @attr.property.str(key="TRIG:SOUR", case=False, only=_TRIGGER_SOURCES)
    def trigger_source(self):
        """'HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm"""

        # special case - the instrument returns '2' instead of 'EXT2'
        remap = {"2": "EXT2"}
        source = self.query("TRIG:SOUR?")
        return remap.get(source, default=source)

    trigger_delay = attr.property.float(key="TRIG:DELAY", min=-5, max=10)
    trigger_count = attr.property.int(key="TRIG:COUN", min=1, max=8192, help="help me")
    trigger_holdoff = attr.property.float(key="TRIG:HOLD", min=0, max=10)
    trigger_level = attr.property.float(key="TRIG:LEV", min=1e-7, max=200e-3)

    trace_points = attr.property.int(
        key="SENSe:TRACe:POINTs", min=1, max=8192, gets=False
    )
    trace_realtime = attr.property.bool(key="TRAC:REAL")
    trace_time = attr.property.float(key="TRAC:TIME", min=10e-6, max=3)
    trace_offset_time = attr.property.float(key="TRAC:OFFS:TIME", min=-0.5, max=100)
    trace_average_count = attr.property.int(key="TRAC:AVER:COUN", min=1, max=65536)
    trace_average_mode = attr.property.str(
        key="TRAC:AVER:TCON", only=("MOV", "REP"), case=False
    )
    trace_average_enable = attr.property.bool(key="TRAC:AVER")

    average_count = attr.property.int(key="AVER:COUN", min=1, max=65536)
    average_auto = attr.property.bool(key="AVER:COUN:AUTO")
    average_enable = attr.property.bool(key="AVER")
    smoothing_enable = attr.property.bool(key="SMO:STAT", gets=False)

    # Local settings traits (leave command unset, and do not implement setter/getter)
    read_termination: str = attr.value.str("\n")

    def preset(self):
        self.write("*PRE")

    def trigger_single(self):
        self.write("INIT")

    def fetch(self):
        """Return a single number or pandas Series containing the power readings"""
        response = self.query("FETC?").split(",")
        if len(response) == 1:
            return float(response[0])
        else:
            index = np.arange(len(response)) * (
                self.trace_time / float(self.trace_points)
            )
            return pd.to_numeric(pd.Series(response, index=index))

    def fetch_buffer(self):
        """Return a single number or pandas Series containing the power readings"""
        response = self.query("FETC:ARR?").split(",")
        if len(response) == 1:
            return float(response[0])
        else:
            index = None  # np.arange(len(response))*(self.trace_time/float(self.trace_points))
            return pd.to_numeric(pd.Series(response, index=index))

    def setup_trace(
        self,
        frequency,
        trace_points,
        sample_period,
        trigger_level,
        trigger_delay,
        trigger_source,
    ):
        """

        :param frequency: in Hz
        :param trace_points: number of points in the trace (perhaps as high as 5000)
        :param sample_period: in s
        :param trigger_level: in dBm
        :param trigger_delay: in s
        :param trigger_source: 'HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm'
        :return: None
        """
        self.write("*RST")
        self.frequency = frequency
        self.function = "XTIM:POW"
        self.trace_points = trace_points
        self.trace_time = trace_points * sample_period
        self.trigger_level = 10 ** (trigger_level / 10.0)
        self.trigger_delay = trigger_delay  # self.Ts / 2
        self.trace_realtime = True
        self.trigger_source = trigger_source  # 'EXT2'  # Signal analyzer trigger output (10kOhm impedance)
        self.initiate_continuous = False
        self.wait()


@attr.adjust("frequency", max=8e9)
class RohdeSchwarzNRP8s(RohdeSchwarzNRPSeries):
    pass


@attr.adjust("frequency", max=18e9)
class RohdeSchwarzNRP18s(RohdeSchwarzNRPSeries):
    pass


if __name__ == "__main__":
    from matplotlib import pyplot as plt
    import seaborn as sns

    sns.set(style="ticks")

    # Enable labbench debug messages
    # log_to_screen()

    with KeysightU2000XSeries("USB0::0x2A8D::0x1E01::SG56360004::INSTR") as sensor:
        print("Connected to ", sensor.identity)

        # Configure
        sensor.preset()
        sensor.frequency = 1e9
        sensor.measurement_rate = "FAST"
        sensor.trigger_count = 200
        sensor.sweep_aperture = 20e-6
        sensor.trigger_source = "IMM"
        sensor.initiate_continuous = True

        power = sensor.fetch()

    power.hist(figsize=(6, 2))
    plt.xlabel("Power level")
    plt.ylabel("Count")
    plt.title("Histogram of power sensor readings")
