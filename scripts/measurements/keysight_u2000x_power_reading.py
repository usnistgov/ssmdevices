#!/usr/bin/env python3
# 
# Dependencies:
#     ssmdevices[scripts]

import labbench as lb
from ssmdevices.instruments import KeysightU2044XA

lb.show_messages('info')

#%% Acquisition

# pass in a specific a resource name if it cannot be autodetected
sensor = KeysightU2044XA()

with sensor:
    sensor.preset()
    sensor.frequency = 1e9
    sensor.measurement_rate = 'FAST'
    sensor.trigger_count = 1
    sensor.sweep_aperture = 1e-3
    sensor.trigger_source = 'IMM'
    sensor.initiate_continuous = True

    print('calibrating...')
    sensor.calibrate()

    # print('zeroing...')
    # sensor.zero()

    power = sensor.fetch()

    print(f'Power level: {power:0.2f} dBm')