*ssmdevices* is a set of python device drivers developed for data acquisition with wireless communication systems and test equipment.
The drivers are implemented with [labbench](https://gitlab.nist.gov/gitlab/ssm/labbench). Acquired data are packaged into [pandas](http://pandas.pydata.org/) data frames for fast data exploration.
It is separate from the `labbench` library to simplify future release of the `labbench` core without trade name complications and to restrict
access based on export control law.

## Installation
1. Install a 64-bit python 3.6 distribution (you can use your favorite, though this process has been tested mainly with Anaconda; support for python 2.7 is not being actively maintained)
2. If you installed python a while ago, make sure your distribution includes pandas 0.19.0 or newer.
3. In an administrator anaconda command prompt, type `pip install git+https://gitlab.nist.gov/gitlab/ssm/labbench`
4. In an administrator anaconda command prompt, type `pip install git+https://gitlab.nist.gov/gitlab/ssm/ssmdevices`
5. If you need support for VISA instruments, install an NI VISA runtime, for example [this one for windows](http://download.ni.com/support/softlib/visa/NI-VISA/16.0/Windows/NIVISA1600runtime.exe).
That's it.

## Documentation
* [ssmdevices API](http://ssm.ipages.nist.gov/ssmdevices/)
* [examples](examples)
* [labbench](https://gitlab.nist.gov/gitlab/ssm/labbench#how-to)

## Device Support
RF power sensors
* Keysight U2000 X series
* Rohde Schwarz NRP Series

RF signal analyzers
* Rohde Schwarz FSW series 

RF signal generators
* Rohde Schwarz SMW series
* Spirent GSS8000 GNSS Simulator

RF switches
* Minicircuits SPnT USB switches

RF attenuators
* Minicircuits RCDAT series

Virtual software "instruments"
* iperf version 2
* UDP sockets control interface for exchanging data with LabView
* Windows WLAN connection status and control
 
Misc. Test Electronics
* Acroname USBHub 2x4

GPS Receivers
* SwiftNav Piksi

### Contributors
| Name  |  Contact Info |
|---|---|
| Dan Kuester (maintainer)  |  <daniel.kuester@nist.gov> |
| Duncan McGillivray  | <duncan.a.mcgillivray@nist.gov>  |
| Ryan Jacobs | <ryan.jacobs@nist.gov> |
| John Ladbury | <john.ladbury@nist.gov> |
| Paul Blanchard | <paul.blanchard@nist.gov> |
| Yao Ma | <yao.ma@nist.gov> |
