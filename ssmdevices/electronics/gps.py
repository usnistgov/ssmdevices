'''
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
'''
__all__ = ['SwiftNavPiksi']
import labbench as lb

class SwiftNavPiksi(lb.SerialLoggingDevice):
    baud_rate = 1000000

if __name__ == '__main__':
    import labbench as lb
    import time
    
    lb.debug_to_screen(lb.DEBUG)
    with SwiftNavPiksi.from_hwid(r'USB VID:PID=0403:6014 SER=5') as piksi:
        piksi.start()
        time.sleep(5)
        piksi.stop()
        result = piksi.fetch()
        print result