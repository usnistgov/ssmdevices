# ssmdevices
The ssmdevices module is a library of python device drivers. The drivers are implemented with [labbench](https://git.ncnr.nist.gov/ssm/labbench),
and provide data in [pandas](http://pandas.pydata.org/) data frames when possible to support rapid exploration of data.
It is separate from the `labbench` library to simplify future release of the `labbench` core without trade name complications and to restrict
access based on export control law.

## Installation
1. Install your favorite python distribution
2. In a command prompt `pip install git+https://git.ncnr.nist.gov/ssm/labbench`
3. In a command prompt `pip install git+https://git.ncnr.nist.gov/ssm/ssmdevices`
4. Install an NI VISA runtime, for example [this one for windows](http://download.ni.com/support/softlib/visa/NI-VISA/16.0/Windows/NIVISA1600runtime.exe).
That's it.

## Supported instruments
RF power sensors
* Keysight U2040 X-Series

RF signal analyzers
* Rohde Schwarz FSW Series 

RF signal generators
* Spirent GSS8000 GNSS Simulator

RF attenuators
* MiniCircuits RCDAT series

Virtual software "instruments"
* IPerfClient - iperf