*ssmdevices* is a collection of python wrappers that have been used for automated experiments by the NIST Spectrum Technology and Research Division. They are released here for transparency, for re-use of the drivers ``as-is'' by the test community, and as a demonstration of lab automation based on [labbench](https://github.com/usnistgov/labbench).

The equipment includes consumer wireless communication hardware, test instruments, diagnostic software, and other miscellaneous lab electronics.
In many cases the acquired data are returned in tabular form as [pandas](http://pandas.pydata.org/) data frames.

# Contributors
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

# Getting started with `ssmdevices`
## Installation
1. Ensure python 3.8 or newer is installed
2. In a command prompt environment for this python interpreter, run `pip install git+https://github.com/usnistgov/ssmdevices`
3. If you need support for VISA instruments, install an NI VISA runtime, for example [from here](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html#460225).

_Note: Certain commercial equipment, instruments, and software are identified here in order to help specify experimental procedures.  Such identification is not intended to imply recommendation or endorsement of any product or service by NIST, nor is it intended to imply that the materials or equipment identified are necessarily the best available for the purpose._

## Documentation
* [API Reference](https://github.com/usnistgov/ssmdevices/blob/main/doc/ssmdevices-api.pdf)
* [Examples](https://github.com/usnistgov/ssmdevices/tree/main/examples)

## See also
* [labbench](https://github.com/usnistgov/labbench) the base library to develop these device wrappers

