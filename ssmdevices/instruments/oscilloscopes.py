__all__ = ["RigolOscilloscope"]

import labbench as lb
from labbench import paramattr as attr

@attr.adjust('make', default='RIGOL TECHNOLOGIES')
@attr.adjust('model', default='MSO4014')
class RigolTechnologiesMSO4014(lb.VISADevice):
    time_offset = attr.property.float(key=":TIM:OFFS", label="s")
    time_scale = attr.property.float(key=":TIM:SCAL", label="s")
    options = attr.property.str(
        key="*OPT", sets=False, cache=True, help="installed license options"
    )

    def open(self, horizontal=False):
        self.write(":WAVeform:FORMat ASCii")

    def fetch(self):
        return self.backend.query_ascii_values(":WAV:DATA?")

    def fetch_rms(self):
        return float(self.backend.query(":MEAS:VRMS?").rstrip().lstrip())
