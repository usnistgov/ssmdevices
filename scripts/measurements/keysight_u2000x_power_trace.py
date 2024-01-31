#!/usr/bin/env python3
# 
# Dependencies:
#     ssmdevices[scripts]

import labbench as lb
from ssmdevices.instruments import KeysightU2000XSeries
from matplotlib import pyplot as plt
import seaborn as sns

lb.show_messages('info')

#%% Acquisition
# may need to supply a resource argument if it cannot be found
sensor = KeysightU2000XSeries()

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
ax2.ylabel('Power level (dBm)')
power.hist(ax=ax2)
ax2.xlabel('Power level (dBm)')
ax2.ylabel('Count')