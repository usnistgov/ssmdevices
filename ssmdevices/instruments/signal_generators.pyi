""" Driver classes for signal generators.
:author: Ryan Jacobs <ryan.jacobs@nist.gov>, Aziz Kord <aziz.kord@nist.gov>, Daniel Kuester <daniel.kuester@nist.gov>
Paul.Blanchard <paul.blanchard@nist.gov>
"""
import labbench as lb
from labbench import paramattr as attr
__all__ = ['RohdeSchwarzSMW200A']


@attr.visa_keying(remap={True: '0', False: '1'})
class RohdeSchwarzSMW200A(lb.VISADevice):

    def __init__(
        self,
        resource: str='NoneType',
        read_termination: str='str',
        write_termination: str='str',
        open_timeout: str='NoneType',
        timeout: str='NoneType',
        make: str='NoneType',
        model: str='NoneType'
    ):
        ...
    frequency_center = attr.property.float(
        key=':freq',
        min=2000.0,
        max=26500000000.0,
        step=1000.0,
        label='Hz'
    )
    rf_output_power = attr.property.float(key=':pow', min=-145, max=20, step=0.01, label='dBm')
    rf_output_enable = attr.property.bool(key='OUTP')
    options = attr.property.str(key='*OPT', sets=False, cache=True, help='installed license options')

    def save_state(self, FileName, num='4'):
        """Save current state of the device to the default directory.
        :param FileName: state file location on the instrument
        :type FileName: string

        :param num: state number in the saved filename
        :type num: int

        """
        self.write('MMEMory:STORe:STATe {},"{}.savrcltxt"'.format(num, FileName))

    def load_state(self, FileName, opc=False, num='4'):
        """Loads a previously saved state file in the instrument

        :param FileName: state file location on the instrument
        :type FileName: string

        :param opc: set the VISA op complete flag?
        :type opc: bool

        :param num: state number in the saved filename
        :type num: int
        """
        cmd = 'MMEM:LOAD:STAT {},\'{}.savrcltxt\';*RCL {}'.format(num, FileName, num)
        self.write(cmd, opc=opc)
if __name__ == '__main__':
    with RohdeSchwarzSMW200A('USB::2733::146::102240::0::INSTR') as siggen:
        siggen.rf_output_enable = True
