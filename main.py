#!/usr/bin/env python
# pylint: disable=invalid-name

"""
Main Module
-----------

This module handles loading of necessary objects to ensure BACnet conform communications by running
BACpypes core.

Note: This Module only works as described, if executed directly! (no import)
"""

from __future__ import absolute_import

from bacnet import BACnetSystem


if __name__ == '__main__':
    system = BACnetSystem()

