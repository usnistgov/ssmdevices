# labbench
The labbench package contains implementations of lab instrument drivers for [remotelets](https://git.ncnr.nist.gov/dkuester/remotelets).
It is separate in order to simplify future release of the remotelets core without trade name complications.

## Installation
1. Install your favorite python distribution
2. In a command prompt `pip install git+https://git.ncnr.nist.gov/dkuester/remotelets`
3. In a command prompt `pip install git+https://git.ncnr.nist.gov/dkuester/labbench`
4. Install an NI VISA runtime, for example [this one for windows](http://download.ni.com/support/softlib/visa/NI-VISA/16.0/Windows/NIVISA1600runtime.exe).
That's it.

## Supported instruments
RF power sensors
* Keysight U2040 X-Series

RF signal analyzers
* Rohde Schwarz FSW Series 