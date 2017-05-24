'''
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
'''
import labbench as lb

class SwiftNavPiksi(lb.SerialLoggingDevice):
    baud_rate = 1000000