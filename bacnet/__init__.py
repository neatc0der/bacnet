# pylint: disable=

"""
BACnet Framework
----------------

This module contains wrappers for BACpypes to ensure seamless integration of BACnet functionality to
user specific use cases.
"""

from __future__ import absolute_import

import os
import sys


# pypy support
PYPY_PATH = 'bacnet/sandbox/pypy'
if os.path.exists(PYPY_PATH):
    sys.path.insert(1, os.path.realpath(os.path.join(os.getcwd(), PYPY_PATH)))


from bacnet.debugging import ModuleLogger


# enabling logging
ModuleLogger()


from bacnet.system import BACnetSystem
