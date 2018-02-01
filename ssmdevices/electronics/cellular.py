'''
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
'''
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import super
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
import labbench as lb

__all__ = ['QxDM']

import logging
logger = logging.getLogger('labbench')

class QxDM(lb.Device):
    ''' Control an already running instance of "Qualcomm eXtensible Diagnostic Monitor" (QxDM).
    '''
    pass