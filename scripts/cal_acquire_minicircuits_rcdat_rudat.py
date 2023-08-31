""" Use a network analyzer to collect calibration data of a MiniCircuits
    attenuator.

    To generate calibration tables for ssmdevices, the results are on the network analyzer and need to be copied into a local folder
    (by USB stick?).
    
    By Audrey Puls, May 2018
    Updates by Dan K, Feb 2019
"""


from ssmdevices.instruments import MiniCircuitsRCDAT, RohdeSchwarzZMB
import labbench as lb
import numpy as np
import time

#############################SETUP CONNECTIONS#####################
atten = MiniCircuitsRCDAT(
    "11604210008", frequency=5.3e9
)  # Set the attenuator serial number here
na = RohdeSchwarzZMB("TCPIP0::132.163.202.153::inst0::INSTR")

lb.show_messages("debug")

with na, atten:
    na.clear()
    na.state.initiate_continuous = False

    ####################SWEEP THROUGH ATTENUATION AND COLLECT DATA#################
    # Since we want to collect cal data on (uncalibrated) attenuator settings,
    # we work with atten.state.attenuation_setting instead of
    # atten.state.attenuation (which tries to apply calibration data)
    for atten.state.attenuation_setting in np.linspace(0, 110, num=441):
        #    for atten.state.attenuation in np.arange(0,101,0.25):
        # The name of the run, based on the attenuation setting
        name = f"{atten.state.attenuation:0.2f}".replace(".", "pt")

        na.trigger()
        time.sleep(45)  # Pauses python to let the VNA finish a full sweep
        na.save_trace_to_csv(f"VA_{atten.settings.resource}_{name}.csv")

    # All done!
    print(
        r"""ATTENTION USER: This program has completed. Your data is stored
              on the VNA under: C:\Users\Public\Documents\Rhode-Schwarz\VNA
              This data can be transfered to another computer via USB.
           """
    )
