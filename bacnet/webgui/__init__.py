# pylint: disable=anomalous-backslash-in-string, broad-except, unused-argument

"""
BACnet WebGUI Module
--------------------

This module contains a django project for BACnet interaction.
"""

from json import dumps
from multiprocessing import Process
import os
import re
import signal
import subprocess
import sys
from threading import Thread, Event
import urllib2
from time import time

from bacnet.debugging import ModuleLogger, bacnet_debug

from .bacnet_access import api_receive, api_transmit


# enable debugging
ModuleLogger(level='INFO')


AUTHKEY_REGEX = re.compile("AUTHKEY\s*=\s*'(.*)'", re.IGNORECASE)
ADDRESS_REGEX = re.compile("ADDRESS\s*=\s*'(.*)'", re.IGNORECASE)
IP_ADDRESS_REGEX = re.compile("IP_ADDRESS\s*=\s*'(.*)'", re.IGNORECASE)

@bacnet_debug
class DjangoProcess(Process):
    """
    This class handles the django process.
    """

    def __init__(self, address, port):
        """
        This function initializes the process.
        """

        # call predecessor
        Process.__init__(self)

        # reserve variables
        self.django_process = None
        self.comm_thread = None

        # set process to daemon
        self.daemon = True

        # set address and port
        self.address = address
        self.port = port

        # set receiving event
        self.start_receiving = Event()

        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self.shutdown)

        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.shutdown)

        # start process
        self.start()

    def receiver(self):
        """
        This function provides the environment for the receiver thread.

        :return: None
        """
        from .control.urls import OBJECT_UPDATE_URL

        # wait until django is started
        self.start_receiving.wait(5)

        self._debug('running: receiver thread')

        # set update url
        update_url = 'http://%s:%s/%s' % (self.address, self.port, OBJECT_UPDATE_URL)

        # initialize last iam
        last_iam = 0

        try:
            # loop forever
            while True:
                try:
                    # receive parsed data
                    parsed_data = api_receive()

                except (IOError, EOFError):
                    # broken pipe
                    break

                # check if parsed data is a dictionary
                if not isinstance(parsed_data, dict):
                    continue

                # check if django sub process is still running
                if hasattr(self, 'django_process') and self.django_process is None and \
                    self.django_process.poll() is not None:
                    break

                # create request
                req = urllib2.Request(
                    update_url,
                    dumps(parsed_data),
                    {'Content-Type': 'application/json'},
                )

                # send update information
                urllib2.urlopen(req)

                if time() - last_iam > 1800:
                    last_iam = time()
                    api_transmit('whois 1')

        except Exception as error:
            self._exception(error)

        finally:
            self._debug('finished: receiver thread')

    def shutdown(self, *args):
        """
        This function shuts down the process.

        :return: None
        """

        self._debug('shutdown')

        if hasattr(self, 'django_process') and self.django_process is not None \
            and self.django_process.poll() is not None:
            self.django_process.kill()

    def run(self):
        """
        This function is executed as a separate process.
        """

        self._debug('running')

        # get current directory
        start_dir = os.getcwd()

        # change directory
        os.chdir(os.path.dirname(__file__))

        # set sys path
        sys.path.insert(0, os.path.dirname(__file__))

        # start thread
        self.comm_thread = Thread(target=self.receiver)
        self.comm_thread.setDaemon(True)
        self.comm_thread.start()

        # import AUTHKEY and ADDRESS for manager
        from bacnet.system.managing import ADDRESS, AUTHKEY

        # set private file
        private_file = 'webgui/settings/private.py'

        # load private settings
        with open(private_file, 'r') as private_fd:
            private_settings = private_fd.read()

        # replace authkey within private settings
        match = AUTHKEY_REGEX.search(private_settings)
        if match:
            private_settings = private_settings[0:match.start(1)] + AUTHKEY + \
                               private_settings[match.end(1):]

        # replace address within private settings
        match = ADDRESS_REGEX.search(private_settings)
        if match:
            private_settings = private_settings[0:match.start(1)] + ADDRESS + \
                               private_settings[match.end(1):]

        # replace ip address within private settings
        match = IP_ADDRESS_REGEX.search(private_settings)
        if match:
            private_settings = private_settings[0:match.start(1)] + self.address + \
                               private_settings[match.end(1):]

        # store private settings
        with open(private_file, 'w') as private_fd:
            private_fd.write(private_settings)

        try:
            # set execution arguments
            argv = [
                './manage.py',
                'runserver',
                '%s:%s' % (self.address, self.port),
                # '--noreload',
            ]

            # initialize django sub process
            self.django_process = subprocess.Popen(argv)

            # wait until sub process terminates
            self.django_process.wait()

        except OSError:
            # interrupt system call
            pass

        except Exception as error:
            self._exception('an error has occurred: %s', error)

        finally:
            # load private settings
            with open(private_file, 'r') as private_fd:
                private_settings = private_fd.read()

            # remove authkey within private settings
            match = AUTHKEY_REGEX.search(private_settings)
            if match:
                private_settings = private_settings[0:match.start(1)] + \
                                   private_settings[match.end(1):]

            # remove address within private settings
            match = ADDRESS_REGEX.search(private_settings)
            if match:
                private_settings = private_settings[0:match.start(1)] + \
                                   private_settings[match.end(1):]

            # remove ip address within private settings
            match = IP_ADDRESS_REGEX.search(private_settings)
            if match:
                private_settings = private_settings[0:match.start(1)] + \
                                   private_settings[match.end(1):]

            # store private settings
            with open(private_file, 'w') as private_fd:
                private_fd.write(private_settings)

            # change directory
            os.chdir(start_dir)

            self._debug('finished')


def create_webgui(address, port):
    """
    This function creates a django subprocess.

    :return: webgui process
    """

    # create webgui process
    process = DjangoProcess(address=address, port=port)

    # return webgui process
    return process
