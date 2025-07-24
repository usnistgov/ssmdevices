"""Driver classes for signal generators.
:author: Ryan Jacobs <ryan.jacobs@nist.gov>, Aziz Kord <aziz.kord@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
Paul.Blanchard <paul.blanchard@nist.gov>
"""

import labbench as lb
from labbench import paramattr as attr

__all__ = ['RohdeSchwarzSMW200A']


@attr.visa_keying(remap={True: '1', False: '0'})
class RohdeSchwarzSMW200A(lb.VISADevice):
    make = attr.value.str('Rohde&Schwarz', inherit=True)
    model = attr.value.str('SMW200A', inherit=True)

    frequency_center = attr.property.float(
        key=':freq', min=2e3, max=26.5e9, step=1e3, label='Hz'
    )
    rf_output_power = attr.property.float(
        key=':pow', min=-145, max=20, step=1e-2, label='dBm'
    )
    rf_output_enable = attr.property.bool(key='OUTP')
    options = attr.property.str(
        key='*OPT', sets=False, cache=True, help='installed license options'
    )

    def save_state(self, FileName: str, num: int = 4):
        """Save current state of the device to the default directory.

        Arguments:
            FileName: path to a state file local to the instrument OS
            num: the index of the current state to save
        """
        if not FileName.lower().endswith('savrcltxt'):
            FileName = FileName + '.savrcltxt'
        self.write(f'MMEMory:STORe:STATe {num},"{FileName}"')

    def load_state(self, FileName: str, num: int = 4):
        """Loads a previously saved state file in the instrument

        Arguments:
            FileName: path to a state file local to the instrument OS
            num: the state number to fill with the loaded state
        """
        if not FileName.lower().endswith('savrcltxt'):
            FileName = FileName + '.savrcltxt'

        self.write(f"MMEM:LOAD:STAT {num},'{FileName}'; *RCL {num}")
        self.wait()


# Example code works nicely in this if statement, which only runs if we're
# running this file (not if it's being imported by another file :))
if __name__ == '__main__':
    with RohdeSchwarzSMW200A('USB::2733::146::102240::0::INSTR') as siggen:
        siggen.rf_output_enable = True
