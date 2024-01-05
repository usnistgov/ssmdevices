[![PyPI Latest Release](https://img.shields.io/pypi/v/ssmdevices.svg)](https://pypi.org/project/ssmdevices/)
[![DOI](https://zenodo.org/badge/DOI/10.18434/M32122.svg)](https://doi.org/10.18434/M32122)
[![License](https://img.shields.io/badge/license-NIST-brightgreen)](https://github.com/usnistgov/ssmdevices/blob/master/LICENSE.md)
[![Downloads](https://static.pepy.tech/badge/ssmdevices)](https://pepy.tech/project/ssmdevices)
[![Last commit](https://img.shields.io/github/last-commit/usnistgov/ssmdevices)](https://pypi.org/project/ssmdevices/)

*ssmdevices* is a collection of python wrappers that have been used for complex automated experiments at NIST. They are released here for transparency, for re-use of the drivers ``as-is'' by collaborators and the broader test community, and as a demonstration of lab automation based on [labbench](https://github.com/usnistgov/labbench).

The equipment includes consumer wireless communication hardware, test instruments, diagnostic software, and other miscellaneous lab electronics.
In many cases the acquired data are returned in tabular form as [pandas](http://pandas.pydata.org/) data frames.

## Getting started with `ssmdevices`
### Installation
1. Ensure prerequisites are installed:
    * python (3.9 – 3.12)
    * [`pip`](https://pypi.org/project/pip/) for package management
2. Recommended module installation:
    * For python distributions based on anaconda:
      ```sh
      pip --upgrade-strategy only-if-needed install ssmdevices
      ```
    * For other python installations:
      ```sh
      pip install ssmdevices
      ```

<!-- _Note: Certain commercial equipment, instruments, and software are identified here in order to help specify experimental procedures.  Such identification is not intended to imply recommendation or endorsement of any product or service by NIST, nor is it intended to imply that the materials or equipment identified are necessarily the best available for the purpose._ -->

## Resources
* [Source code](http://github.com/usnistgov/ssmdevices)
* [Documentation](http://pages.nist.gov/ssmdevices)
* [PyPI](https://pypi.org/project/labbench/) module page
* [Examples](https://github.com/usnistgov/ssmdevices/tree/main/examples)
* [labbench](https://github.com/usnistgov/labbench), the underlying API library

## Contributors
| Name  |  Contact Info |
|---|---|
| Dan Kuester (maintainer)  |  <daniel.kuester@nist.gov> |
| Paul Blanchard | formerly with NIST |
| Alex Curtin | formerly with NIST |
| Keith Forsyth  | <keith.forsyth@nist.gov>  |
| Ryan Jacobs | formerly with NIST |
| John Ladbury | <john.ladbury@nist.gov> |
| Yao Ma | <yao.ma@nist.gov> |
| Duncan McGillivray  | <duncan.a.mcgillivray@nist.gov>  |
| Audrey Puls | formerly with NIST |
| Andre Rosete        | formerly with NIST |
| Michael Voecks | formerly with NIST |


## Some complex measurement efforts that used ssmdevices:
  * [NIST TN 1952: LTE Impacts on GPS](https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1952.pdf) and [data](https://data.nist.gov/od/id/mds2-2186)
  * [NIST TN 2069: Characterizing LTE User Equipment Emissions: Factor Screening](https://doi.org/10.6028/NIST.TN.2069)
  * [NIST TN 2140: AWS-3 LTE Impacts on Aeronautical Mobile Telemetry](https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.2140.pdf) and [data](https://data.nist.gov/od/id/mds2-2279)
  * [NIST TN 2147: Characterizing LTE User Equipment Emissions Under Closed-Loop Power Control](https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.2147.pdf)
  * [Blind Measurement of Receiver System Noise](https://www.nist.gov/publications/blind-measurement-receiver-system-noise) and [data](https://data.nist.gov/pdr/lps/ark:/88434/mds2-2121)

## Contributing
* [Pull requests](https://github.com/usnistgov/ssmdevices/pulls) are welcome!
* [Inline documentation style convention](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings)

## See also
* [labbench](https://github.com/usnistgov/labbench) the base library for these device wrappers

