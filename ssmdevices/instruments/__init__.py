# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from .attenuators import *
from .gps_simulator import *
from .network_testing import *
from .oscilloscopes import *
from .power_sensors import *
from .signal_analyzers import *
from .signal_generators import *
from .switches import *

# Clear out submodules from namespace
#from inspect import ismodule as _ismodule
#__l = locals()
#for _k,_v in __l.items():
#    if not _k.startswith('_'):
##        if _ismodule(_v):
##            __l.pop(_k)
#        if hasattr(_v, '__module__'):
#            _v.__module__ = '.'.join(_v.__module__.split('.')[:-1])
#del __l,_k,_v,_ismodule