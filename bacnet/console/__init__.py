# pylint: disable=too-few-public-methods

"""
Console Module
--------------

This module contains just a single public function for creating an object for a set of console
commands to ensure BACnet conform communications by using BACpypes.

Function for creating console commands:
    create_console(application)

"""

from __future__ import absolute_import

from .define import Console

from bacnet.debugging import ModuleLogger


ModuleLogger()


def create_console(device, application, **kwargs):
    """
    This function creates a single BACpypes object to support a shell to control BACnet messages.

    :param device: device object
    :param application: application object
    :return: console object
    """
    # create specific console object
    console = Console(device, application, **kwargs)

    # return console object
    return console
