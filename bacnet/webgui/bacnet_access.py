"""
BACnet Access Module
--------------------

This module provides access to the inter-process communication of the system.
"""

import sys

from django.conf import settings

from bacnet.system.managing import client_manager, ADDRESS
from bacnet.api import BACnetAPI


if 'runserver' in sys.argv or 'webgui' in sys.argv:
    # check if ADDRESS was defined
    if not ADDRESS:
        # get manager by address and authkey
        MANAGER = client_manager(settings.ADDRESS, settings.AUTHKEY)

    else:
        # get manager
        MANAGER = client_manager()

    # get api access
    API = BACnetAPI(MANAGER.app(), MANAGER.webgui(), 4)

    # remove all security relevant objects
    del MANAGER, client_manager, BACnetAPI


def api_create(line):
    """
    This function wraps the API method create.

    :param line: command
    :return: APDU object
    """

    # return created object
    return API.create(line)


def api_transmit(line=None, request=None):
    """
    This function wraps the API methods create and send.

    :param line: command
    :param request: APDU object
    :return: sending successful
    """

    # check if line was supplied
    if line is not None:
        # return success of transmission
        return API.send(API.create(line))

    # return success of transmission
    return API.send(request)


def api_receive():
    """
    This function wraps the API methods receive and parse.

    :return: parsed APDU object
    """

    # returns parsed APDU object
    return API.parse(API.receive())
