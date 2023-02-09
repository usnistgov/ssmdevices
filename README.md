*ssmdevices* is a curated collection of python device drivers for lab equipment in wireless and radio frequency electromagnetic experiments. The scope of equipment targeted here includes consumer wireless communication hardware, instruments, diagnostic software, and other miscellaneous lab electronics.
The drivers are implemented with [labbench](https://github.com/usnistgov/labbench). In many cases the acquired data are packaged into [pandas](http://pandas.pydata.org/) data frames.
It is separate from the `labbench` library to simplify future release of the `labbench` core without trade name and export control complications.

## Installation
1. Install a 64-bit distribution of python 3.7 (or newer). This process has been tested only with anaconda
2. If you installed python a while ago, make sure your distribution includes pandas 0.21.0 or newer.
4. In an anaconda command prompt, type `pip install git+https://github.com/usnistgov/ssmdevices`
5. If you need support for VISA instruments, install an NI VISA runtime, for example [from here](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html#460225).

## Documentation
* [ssmdevices API](http://ssm.ipages.nist.gov/ssmdevices/)
* [examples](examples)
* [labbench](https://github.com/usnistgov/labbench/blob/master/examples/How%20to%20use%20a%20labbench%20driver%20by%20example.ipynb)

## Device Support
| *Class* | *Products* |
|-------------|---------|
|Attenuators|Minicircuits RUDAT series|
|           |Minicircuits RCDAT series|
|           |Minicircuits RCDAT4 series|
|Motors|ETS-Lindren Azi2005|
|Networking testers|Cobham TM500 load tester|
|Oscilloscopes|Rigol ...|
|Power sensors|Keysight U2000 X series|
|             |Rohde Schwarz NRP Series|
|Power supplies|Rigol DP800 series|
|Signal analyzers|Rohde Schwarz FSW series|
|Signal generators|Rohde Schwarz SMW series|
|                 |Spirent GSS8000 GNSS Simulator|
|Software virtual instruments|iperf 2.08 on host|
|                            |iperf on randroid over adb|
|                            |UDP sockets control interface for exchanging data with LabView|
|                            |Windows WLAN adapters|
|                            |Qualcomm QXDM|
|Switches|Minicircuits SPnT USB|
|Miscellaneous Lab Gear      |Acroname USBHub 2x4 (python 2.7 only)|
|Consumer Electronics        |SwiftNav Piksi GPS Receiver|
|                            |Android handsets|



### Contributors
| Name  |  Contact Info |
|---|---|
| Dan Kuester (maintainer)  |  <daniel.kuester@nist.gov> |
| Duncan McGillivray  | <duncan.a.mcgillivray@nist.gov>  |
| Andre Rosete        | <andre.rosete@nist.gov> |
| Paul Blanchard | <paul.blanchard@nist.gov> |
| Michael Voecks | <michael.voecks@nist.gov> |
| Ryan Jacobs | ryan.jacobs@nist.gov |
| Alex Curtin | alexandra.curtin@nist.gov |
| Audrey Puls | <audrey.puls@nist.gov> |
| John Ladbury | <john.ladbury@nist.gov> |
| Yao Ma | <yao.ma@nist.gov> |
