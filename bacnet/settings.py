# pylint: disable=

"""
BACnet Settings Module
----------------------

This module contains general settings for the BACnet system.
"""

import os


# set data path
DATA_PATH = 'run/'

# set sandbox path
SANDBOX_PATH = 'bacnet/sandbox/'

# set sandbox temp path
SANDBOX_TMP = os.path.join(SANDBOX_PATH, 'tmp')

# set interface script
INTERFACE_SCRIPT = os.path.join(SANDBOX_PATH, 'interface.py')
