'''
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
'''
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
import labbench as lb

__all__ = ['SwiftNavPiksi']

class SwiftNavPiksi(lb.SerialLoggingDevice):
    baud_rate: lb.Int(1000000, min=1, )

if __name__ == '__main__':
    import labbench as lb
    import time
    
    lb.debug_to_screen(lb.DEBUG)
    with SwiftNavPiksi.from_hwid(r'USB VID:PID=0403:6014 SER=5') as piksi:
        piksi.start()
        lb.sleep(5)
        piksi.stop()
        result = piksi.fetch()
        print('Received:\n', result)