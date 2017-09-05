# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 13:35:02 2017

@author: dkuester
"""

from .iperf import *
from .windows import *

# Clear out submodules from namespace
from inspect import ismodule as _ismodule
__l = locals()
[__l.pop(_k) for _k,_v in __l.items() if not _k.startswith('_') and _ismodule(_v)]
del __l,_k,_v,_ismodule