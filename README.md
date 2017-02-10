# remotelets
The remotelets_drivers package contains implementations of lab instrument drivers for remotelets.
It is separate in order to simplify future release of the remotelets core without trade name complications.

## Summary
The basis of remotelets is [traitlets](https://github.com/ipython/traitlets), extended with hooks for remote fetch/put to a remote device.
Device control with remotelets relies on other libraries to act as backends, such as pyvisa, pyserial, pythonnet, etc.
The result is an instrument control library implemented according to the [descriptor](https://docs.python.org/3/howto/descriptor.html) (also known as [decorator](https://en.wikipedia.org/wiki/Decorator_pattern)) design pattern.
The use of traitlets also enables optional integration into [jupyter notebook](http://jupyter.org/) for interactive control.

## Installation
1. Install your favorite python distribution
2. In a command prompt `pip install git+https://git.ncnr.nist.gov/dkuester/remotelets`
3. In a command prompt `pip install git+https://git.ncnr.nist.gov/dkuester/remotelets_drivers`
4. Install an NI VISA runtime, for example [this one for windows](http://download.ni.com/support/softlib/visa/NI-VISA/16.0/Windows/NIVISA1600runtime.exe).
That's it.

## Supported instruments

RF power sensors
* Keysight U2040 X-Series