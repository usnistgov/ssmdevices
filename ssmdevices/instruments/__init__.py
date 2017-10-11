# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""

from .attenuators import *
from .gps_simulator import *
from .oscilloscopes import *
from .power_sensors import *
from .signal_analyzers import *
from .signal_generators import *

# Clear out submodules from namespace
from inspect import ismodule as _ismodule
__l = locals()
for _k,_v in __l.items():
    if not _k.startswith('_'):
        if _ismodule(_v):
            __l.pop(_k)
        __l.__module__ = '.'.join(__l.__module__.split('.')[:-1])
    
del __l,_k,_v,_ismodule