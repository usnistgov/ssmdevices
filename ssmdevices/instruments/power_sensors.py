# -*- coding: utf-8 -*-

__all__ = [
    "KeysightU2000XSeries",
    "RohdeSchwarzNRP8s",
    "RohdeSchwarzNRP18s",
    "RohdeSchwarzNRPSeries",
]

import labbench as lb


class KeysightU2000XSeries(lb.VISADevice):
    """Coaxial power sensors connected by USB"""

    TRIGGER_SOURCES = ("IMM", "INT", "EXT", "BUS", "INT1")

    initiate_continuous = lb.property.bool(key="INIT:CONT")
    output_trigger = lb.property.bool(key="OUTP:TRIG")
    trigger_source = lb.property.str(key="TRIG:SOUR", case=False, only=TRIGGER_SOURCES)
    trigger_count = lb.property.int(key="TRIG:COUN", min=1, max=200)
    measurement_rate = lb.property.str(
        key="SENS:MRAT", only=("NORM", "DOUB", "FAST"), case=False
    )
    sweep_aperture = lb.property.float(
        key="SWE:APER", min=20e-6, max=200e-3, help="time", label="s"
    )
    frequency = lb.property.float(
        key="SENS:FREQ",
        min=10e6,
        max=18e9,
        step=1e-3,
        help="input signal center frequency (in Hz)",
    )

    def preset(self):
        self.write("SYST:PRES")

    def fetch(self):
        """Return a single number or pandas Series containing the power readings"""
        import pandas as pd

        response = self.query("FETC?").split(",")
        if len(response) == 1:
            return float(response[0])
        else:
            return pd.to_numeric(pd.Series(response))


class RohdeSchwarzNRPSeries(lb.VISADevice):
    """Coaxial power sensors connected by USB.

    These require the installation of proprietary drivers from the vendor website. Resource strings for connections take the form
    'RSNRP::0x00e2::103892::INSTR'.
    """

    FUNCTIONS = ("POW:AVG", "POW:BURS:AVG", "POW:TSL:AVG", "XTIM:POW", "XTIM:POWer")
    TRIGGER_SOURCES = ("HOLD", "IMM", "INT", "EXT", "EXT1", "EXT2", "BUS", "INT1")

    # Instrument state traits (pass command arguments and/or implement setter/getter)
    frequency = lb.property.float(key="SENS:FREQ", min=10e6, step=1e-3, label="Hz")
    initiate_continuous = lb.property.bool(
        key="INIT:CONT", remap={False: "OFF", True: "ON"}
    )

    @lb.property.str(
        key="SENS:FUNC",
        case=False,
        only=FUNCTIONS,
    )
    def function(self, value):
        # Special case - this message requires quotes around the argument
        self.write(f'SENSe:FUNCtion "{value}"')

    @lb.property.str(
        key="TRIG:SOUR",
        case=False,
        only=TRIGGER_SOURCES,
    )
    def trigger_source(self):
        """'HOLD: No trigger; IMM: Software; INT: Internal level trigger; EXT2: External trigger, 10 kOhm"""
        # special case - the instrument returns '2' instead of 'EXT2'
        remap = {"2": "EXT2"}
        source = self.query("TRIG:SOUR?")
        return remap.get(source, default=source)

    trigger_delay = lb.property.float(key="TRIG:DELAY", min=-5, max=10)
    trigger_count = lb.property.int(key="TRIG:COUN", min=1, max=8192, help="help me")
    trigger_holdoff = lb.property.float(key="TRIG:HOLD", min=0, max=10)
    trigger_level = lb.property.float(key="TRIG:LEV", min=1e-7, max=200e-3)

    trace_points = lb.property.int(
        key="SENSe:TRACe:POINTs", min=1, max=8192, gets=False
    )
    trace_realtime = lb.property.bool(key="TRAC:REAL", remap={False: "OFF", True: "ON"})
    trace_time = lb.property.float(key="TRAC:TIME", min=10e-6, max=3)
    trace_offset_time = lb.property.float(key="TRAC:OFFS:TIME", min=-0.5, max=100)
    trace_average_count = lb.property.int(key="TRAC:AVER:COUN", min=1, max=65536)
    trace_average_mode = lb.property.str(
        key="TRAC:AVER:TCON", only=("MOV", "REP"), case=False
    )
    trace_average_enable = lb.property.bool(
        key="TRAC:AVER", remap={False: "OFF", True: "ON"}
    )

    average_count = lb.property.int(key="AVER:COUN", min=1, max=65536)
    average_auto = lb.property.bool(
        key="AVER:COUN:AUTO", remap={False: "OFF", True: "ON"}
    )
    average_enable = lb.property.bool(key="AVER", remap={False: "OFF", True: "ON"})
    smoothing_enable = lb.property.bool(
        key="SMO:STAT", remap={False: "OFF", True: "ON"}, gets=False
    )

    # Local settings traits (leave command unset, and do not implement setter/getter)
    read_termination = lb.property.str()

    def preset(self):
        self.write("*PRE")

    def trigger_single(self):
        self.write("INIT")

    def fetch(self):
        """Return a single number or pandas Series containing the power readings"""
        import pandas as pd

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
        import pandas as pd

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


class RohdeSchwarzNRP8s(RohdeSchwarzNRPSeries):
    frequency = lb.property.float(
        key="SENS:FREQ",
        min=10e6,
        max=8e9,
        step=1e-3,
        label="Hz",
        help="calibration frequency",
    )


class RohdeSchwarzNRP18s(RohdeSchwarzNRPSeries):
    frequency = lb.property.float(
        key="SENS:FREQ",
        min=10e6,
        max=18e9,
        step=1e-3,
        label="Hz",
        help="calibration frequency",
    )


if __name__ == "__main__":
    from pylab import *
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
    xlabel("Power level")
    ylabel("Count")
    title("Histogram of power sensor readings")
