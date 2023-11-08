__all__ = ["RigolOscilloscope"]

import labbench as lb
from labbench import paramattr as param


class RigolOscilloscope(lb.VISADevice):
    time_offset = param.property.float(key=":TIM:OFFS", label="s")
    time_scale = param.property.float(key=":TIM:SCAL", label="s")
    options = param.property.str(key="*OPT", sets=False, cache=True, help="installed license options")

    def open(self, horizontal=False):
        self.write(":WAVeform:FORMat ASCii")

    def fetch(self):
        return self.backend.query_ascii_values(":WAV:DATA?")

    def fetch_rms(self):
        return float(self.backend.query(":MEAS:VRMS?").rstrip().lstrip())
