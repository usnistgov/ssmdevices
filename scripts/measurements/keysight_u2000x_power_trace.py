#!/usr/bin/env python3
# 
# Dependencies:
#     ssmdevices[scripts]

import labbench as lb
from ssmdevices.instruments import KeysightU2044XA
from matplotlib import pyplot as plt
import seaborn as sns

lb.show_messages('info')

#%% Acquisition

# pass in a specific a resource name if it cannot be autodetected
sensor = KeysightU2044XA()

with sensor:
    sensor.preset()
    sensor.frequency = 1e9
    sensor.measurement_rate = 'FAST'
    sensor.trigger_count = 200
    sensor.sweep_aperture = 20e-6
    sensor.trigger_source = 'IMM'
    sensor.initiate_continuous = True

    power = sensor.fetch()

#%% Display
sns.set(style='ticks')

fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(6,2))
power.plot(ax=ax1)
ax2.set_ylabel('Power level (dBm)')
power.hist(ax=ax2)
ax2.set_xlabel('Power level (dBm)')
ax2.set_ylabel('Count')