# pylint: disable=broad-except

"""
BACnet API Module
-----------------

This module provides basic api functionality.
"""

from __future__ import absolute_import

from multiprocessing import Lock
from Queue import Empty
import time

from bacpypes.apdu import APDU

from bacnet.debugging import ModuleLogger, bacnet_debug

from bacnet.system.managing import client_manager

from bacnet.console.creator import request_creator
from bacnet.console.parser import response_parser


# enable logging
ModuleLogger()


# define minimum waiting times
# max 1.000 local attempts per second
LOCAL_WAIT = 0.001
# max 100 network attempts per second
NETWORK_WAIT = 0.05


@bacnet_debug
class BACnetAPI(object):
    """
    This class unifies all API accessible functions.
    """

    def __init__(self, *args):
        """
        This function initializes the object.

        :return:
        """

        # check if arguments were given
        if not len(args) in [0, 2, 3]:
            raise ValueError(
                'API takes either 2 queues and an optional local id or no arguments at all'
            )

        # get semaphore for waiting
        self.__wait_lock = Lock()

        # set variable
        self.__last_sent = None

        # set local id
        self.__local_id = 2

        if len(args) > 1:
            # set app queue
            self.__app = args[0]

            # set request queue
            self.__requests = args[1]

            # check if local id was defined
            if len(args) > 2:
                # set local id
                self.__local_id = args[2]

        else:
            # get manager
            manager = client_manager()

            # initialize app queue
            self.__app = manager.app()

            # initialize request queue
            self.__requests = manager.config()

    def create(self, line):
        """
        This function creates a request for the specified command.

        :param line: command line
        :return: request object
        """

        # strip line
        line = line.strip()

        # initialize request
        request = None

        try:
            # create request
            request = request_creator(line, local_id=self.__local_id)

        except Exception as error:
            self._exception(error)

        # return request
        return request

    def send(self, request, block=True, timeout=None):
        """
        This function transmits the request.

        :param request: outgoing request
        :param block: block
        :param timeout: timeout
        :return: request was queued
        """

        # ignore empty requests
        if request is None:
            return False

        # wait until request is allowed to be sent
        self.__wait(request)

        try:
            # queue request
            return self.__app.put(request, block, timeout)

        except Exception as error:
            self._exception(error)

            return False

    def __wait(self, request):
        """
        This function waits until next request is allowed to be sent.

        :return: None
        """

        # enter critical area
        self.__wait_lock.acquire()

        # check if last sent is set
        if self.__last_sent is not None:
            # check if request is local
            if request.pduDestination.addrIP == 0:
                # check if process has to wait
                if time.time() - self.__last_sent < LOCAL_WAIT:
                    # sleep
                    time.sleep(LOCAL_WAIT - time.time() + self.__last_sent)

            else:
                # check if process has to wait
                if time.time() - self.__last_sent < NETWORK_WAIT:
                    # sleep
                    time.sleep(NETWORK_WAIT - time.time() + self.__last_sent)

        # set current time
        self.__last_sent = time.time()

        # leave critical area
        self.__wait_lock.release()

    def receive(self, block=True, timeout=None):
        """
        This function checks for available incoming requests

        :param block: block
        :param timeout: timeout
        :return: incoming response or None
        """

        try:
            # return response
            return self.__requests.get(block, timeout)

        except (IOError, EOFError):
            # broken pipe
            return

        except Empty:
            # return
            return

    @staticmethod
    def parse(apdu):
        """
        This function returns a parsed dictionary from provided message.
        :param apdu: message
        :return: parsed dict
        """

        if not isinstance(apdu, APDU):
            raise ValueError('invalid apdu')

        # return parsed response
        return response_parser(apdu)
