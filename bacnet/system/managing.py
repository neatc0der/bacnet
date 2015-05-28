# pylint: disable=global-statement, star-args, bare-except

"""
BACnet Managing Module
----------------------

This module provides managing tools for multiprocessing.
"""

from __future__ import absolute_import

import codecs
import os
from multiprocessing import Queue
from multiprocessing.managers import SyncManager as Manager

from bacnet.debugging import bacnet_debug, ModuleLogger


ModuleLogger()


AUTHKEY = None
ADDRESS = None

LOG_QUEUE = None
APP_QUEUE = None
CONFIG_QUEUE = None
CONSOLE_QUEUE = None
WEBGUI_QUEUE = None

IP_ADDRESS = None
PORT = None


def __get_manager():
    # pylint: disable=too-few-public-methods
    """
    This function creates specific managers for server and clients.

    :return:
    """

    class Supervisor(Manager):
        """
        This class provides specific attributes for inter-process communication
        """

    Supervisor.register('app', callable=lambda: APP_QUEUE)
    Supervisor.register('config', callable=lambda: CONFIG_QUEUE)
    Supervisor.register('console', callable=lambda: CONSOLE_QUEUE)
    Supervisor.register('webgui', callable=lambda: WEBGUI_QUEUE)
    Supervisor.register('log', callable=lambda: LOG_QUEUE)
    Supervisor.register('ip_address', callable=lambda: IP_ADDRESS)
    Supervisor.register('port', callable=lambda: PORT)

    return Supervisor


@bacnet_debug(formatter='%(levelname)s:server_manager: %(message)s')
def server_manager(log_queue, ip_address, port, console=False, webgui=False):
    """
    This function creates a server manager.

    :return: manager, server
    """

    self = server_manager

    global AUTHKEY, ADDRESS, LOG_QUEUE, APP_QUEUE, CONSOLE_QUEUE, WEBGUI_QUEUE, CONFIG_QUEUE
    global IP_ADDRESS, PORT

    LOG_QUEUE = log_queue
    APP_QUEUE = Queue()
    CONFIG_QUEUE = Queue()
    if console:
        CONSOLE_QUEUE = Queue()
    if webgui:
        WEBGUI_QUEUE = Queue()
    IP_ADDRESS = ip_address.split('/')[0]
    PORT = port

    # generate auth key
    AUTHKEY = codecs.encode(os.urandom(32), 'hex')

    # create manager
    manager = __get_manager()(authkey=AUTHKEY)
    manager.start()

    self._debug('created and started')

    # read address
    ADDRESS = manager._address

    # return manager and server
    return manager


@bacnet_debug(formatter='%(levelname)s:client_manager: %(message)s')
def client_manager(address=None, authkey=None):
    """
    This function creates a client manager

    :return: manager
    """

    # check if address was set
    if address is None:
        # set default address
        address = ADDRESS

    # check if authkey was set
    if authkey is None:
        # set default authkey
        authkey = AUTHKEY

    self = client_manager

    # create manager
    manager = __get_manager()(address=address, authkey=authkey)

    # connect
    manager.connect()

    self._debug('created and connected')

    # return manager
    return manager
