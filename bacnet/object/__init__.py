# pylint: disable=no-member, unused-argument, wildcard-import

"""
Objects Module
--------------

This module contains just a single function to collect all user specific bacpypes Objects.
"""

from __future__ import absolute_import

from .basic import *
from .define import get_initial_object_list
from .hardware import discover_hardware_objects


# enable logging
ModuleLogger()


def get_object_list():
    """
    This function collects all defined user specific and relevant builtin bacpypes Objects.

    :param examples: enable example objects
    :return: object_list
    """

    # collect all Objects
    object_list = get_initial_object_list()

    # return all Objects that are supposed to be used
    return object_list
