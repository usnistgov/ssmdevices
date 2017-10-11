# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""

from .iperf import *
from .windows import *

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