# ssmdevices
`ssmdevices` is a module of drivers that support python lab automation for shared-spectrum metrology. The drivers are implemented with [labbench](https://gitlab.nist.gov/gitlab/ssm/labbench),
and provide data in [pandas](http://pandas.pydata.org/) data frames when possible to support rapid exploration of data.
It is separate from the `labbench` library to simplify future release of the `labbench` core without trade name complications and to restrict
access based on export control law.

## Getting started
### Installation
1. Install a 64-bit python 2.7 distribution (you can use your favorite, though this process has been tested mainly with Anaconda)
2. Make sure your distribution includes pandas 0.19.0 or newer.
3. In an administrator anaconda command prompt, type `pip install git+https://gitlab.nist.gov/gitlab/ssm/labbench`
4. In an administrator anaconda command prompt, type `pip install git+https://gitlab.nist.gov/gitlab/ssm/ssmdevices`
5. If you need support for VISA instruments, install an NI VISA runtime, for example [this one for windows](http://download.ni.com/support/softlib/visa/NI-VISA/16.0/Windows/NIVISA1600runtime.exe).
That's it.

### Data acquisition and instrument control examples
* [Coexistence tests of LTE-LAA and WLAN](examples/lte-laa-wlan.ipynb)
* [Receiver system noise tests of a WLAN client adapter](examples/wlan-noise-sweep.ipynb)
* [Receiver system noise tests of a GPS receiver](examples/gps-noise-sweep.ipynb)

## References
* [API reference](http://ssm.ipages.nist.gov/ssmdevices/)

## Supported laboratory devices
RF power sensors
* Keysight U2040 X series

RF signal analyzers
* Rohde Schwarz FSW series 

RF signal generators
* Rohde Schwarz SMW series
* Spirent GSS8000 GNSS Simulator

RF attenuators
* MiniCircuits RCDAT series

Virtual software "instruments"
* iperf version 2
* UDP sockets control interface for exchanging data with LabView
* Windows WLAN connection information
 
Misc. Test Electronics
* Acroname USBHub 2x4

GPS Receivers
* SwiftNav Piksi

