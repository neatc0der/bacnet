# pylint: disable=too-many-instance-attributes, broad-except, import-error

"""
BACnet Config Module
--------------------

This module provides configuration functionality.
"""

import os
import sys

from bacpypes.pdu import Address

from bacnet.debugging import bacnet_debug, ModuleLogger

from bacnet.system.config.helper import get_local_ip

if sys.version_info[0] < 3:
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser


ModuleLogger()


@bacnet_debug(formatter='%(levelname)s:config: %(message)s')
class ConfigManager(object):
    """
    This class handles the configuration requests by the user.
    """

    filename = 'BACnet.ini'
    data = {}

    def __init__(self, **kwargs):
        """
        This function initializes the object.

        :return: None
        """

        # set default stdin
        self.stdin = sys.stdin

        # set default stdout
        self.stdout = sys.stdout

        # set default data
        self.defaults = {
            'objectname': 'node',
            'objectidentifier': '123456',
            'address': 'eth0',
            'port': '47808',
            'maxapdulengthaccepted': '1024',
            'segmentationsupported': 'segmentedBoth',
            'webport': '8080',
        }

        # set preset data
        self.data = {
            'vendoridentifier': '0',
            'foreignport': '0',
            'foreignbbmd': '10.20.30.40/24',
            'foreignttl': '30',
        }

        # set title names
        self.titles = {
            'objectname': 'node name',
            'objectidentifier': 'node id',
            'address': 'ip address/netmask or interface',
            'maxapdulengthaccepted': 'maximum apdu length',
            'foreignbbmd': 'foreign broadcast node address',
            'foreignport': 'foreign node port',
            'foreignttl': 'foreign node ttl',
            'segmentationsupported': 'segmention supported',
            'webport': 'django runserver port',
        }

        # set order of user input
        self.order = (
            'objectname',
            'objectidentifier',
            'address',
            'port',
            'maxapdulengthaccepted',
            'segmentationsupported',
            'webport',
            # 'foreignBBMD',
        )

        # reset filename if defined
        if 'filename' in kwargs:
            self.filename = kwargs['filename']
            del kwargs['filename']

        # check if config already exists
        if os.path.exists(self.filename):
            # create parser
            config = ConfigParser()

            # read file
            config.read(self.filename)

            # check if section exists
            if config.has_section('BACnet'):
                # update defaults
                self.defaults.update(dict(config.items('BACnet')))

        self.allowed_none = ()

        # set initial values if existing
        for name, value in kwargs.items():
            if hasattr(self, name):
                if isinstance(value, dict):
                    getattr(self, name).update(value)
                else:
                    setattr(self, name, value)

            else:
                raise AttributeError('attribute "%s" not found' % name)

        # start
        self.start()

    def store(self):
        """
        This function stores the retrieved data.

        :return: None
        """

        config = ConfigParser()
        config.add_section('BACnet')
        for key in self.order:
            config.set('BACnet', key, self.data[key])

        for key in set(self.data.keys()) - set(self.order):
            config.set('BACnet', key, self.data[key])

        with open(self.filename, 'w') as file_pointer:
            config.write(file_pointer)

    def start(self):
        """
        This function initiates the user interface.

        :return: None
        """

        try:
            for key in self.order:
                self.get(key)

        except ValueError as error:
            self._error('aborting config: %s' % error.message)

        except Exception as error:
            self._exception(error)

    def get_input(self, key, prompt):
        """
        This function handles user input.

        :param key: default key
        :param prompt: prompt text
        :return: user response
        """

        # get default value
        default_value = self.defaults.get(key, None)

        # get message
        message = prompt
        if default_value is not None:
            message += ' (default: %s)' % default_value
        message += ': '

        # print prompt
        self.stdout.write(message)
        self.stdout.flush()

        # wait for response
        response = self.stdin.readline()

        # strip unnecessary signs
        response = response.rstrip('\r\n').strip()

        if response == '':
            response = default_value

        # return response
        return response

    def verify_address(self, key='address', response='', interface=True):
        """
        This function retrieves an ip address provided by the user.

        :param response: user input
        :return: verified response
        """

        try:
            Address(response)
            address = response

        except (TypeError, ValueError):
            if interface:
                address = get_local_ip(response)
                if address is not None:
                    self.stdout.write('  -> retrieved: %s\n' % address)
                    self.stdout.flush()
                    response = address
            else:
                address = None

        if interface:
            i_text = ' or interface'
        else:
            i_text = ''

        if not self.valid(key, address):
            self.stdout.write('invalid address%s "%s"\n' % (i_text, response))
            self.stdout.flush()
            response = None

        # return response
        return response

    def verify_bbmd(self, response):
        """
        This function verifies an ip address provided by the user.

        :param response: user input
        :return: verified response
        """

        return self.verify_address('bbmd', response, interface=False)

    def valid(self, key, response):
        """
        This function checks, if response is valid

        :param key: value to retrieve
        :param response: retrieved value
        :return:
        """

        # return if response is valid
        return bool(response) or key in self.allowed_none

    def get(self, key):
        """
        This function retrieves specified value provided by the user.

        :param key: value to retrieve
        :return: None
        """

        if hasattr(self, 'verify_%s' % key):
            verify = getattr(self, 'verify_%s' % key)
        else:
            verify = lambda response: response

        response = None
        i = 0

        # try 3 times to get address
        while i == 0 or (i < 3 and not self.valid(key, response)):
            # get user input
            response = verify(response=self.get_input(key, 'define %s' % self.titles.get(key, key)))

            # count response
            i += 1

        if not self.valid(key, response):
            raise ValueError('%s not set properly' % key)

        # store key
        self.data[key] = response
