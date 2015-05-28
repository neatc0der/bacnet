# pylint: disable=too-few-public-methods, too-many-ancestors, no-member

"""
Application Define Module
-------------------------

This module contains the user specific definition of a BACpypes Application and Console Commands.
"""

from __future__ import absolute_import

from .basic import BasicApplication


class Application(BasicApplication):
    """
    This class describes the user specific Application functionality including basic builtin
    functions like "whois" and "iam".
    """

    pass
