# pylint: disable=too-few-public-methods, invalid-name, import-error

"""
Config Parser Module
--------------------

This module provides an extended version of the BCApypes argument parser.
"""

from __future__ import absolute_import

from argparse import ArgumentParser
import sys

import os
from bacnet.debugging import bacnet_debug, ModuleLogger
from bacnet.system.config.helper import get_local_ip
from bacnet.system.version import get_version


if sys.version_info[0] < 3:
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser


# enabling logging
ModuleLogger(details=1, level='INFO')


@bacnet_debug(formatter='%(levelname)s:%(module)s: %(message)s')
class FullArgumentParser(ArgumentParser):
    """
    This class combines BACpypes builtin config and parameter parser with customized parameters.
    """

    arg_object = None

    def __init__(self, **kwargs):
        """
        This function constructs the application object.

        :return: FullArgumentParser instance
        """

        self._debug('%s.__init__', FullArgumentParser.__name__)

        # get commands
        commands = kwargs.get('commands', [])
        if 'commands' in kwargs:
            del kwargs['commands']

        # call predecessor constructor
        ArgumentParser.__init__(self, **kwargs)

        # set interface to retrieve ip
        # print version
        self.add_argument(
            '--version',
            action='version',
            version=get_version(),
        )

        self.add_argument(
            '--interface',
            '-i',
            help='define interface to retrieve IP address (ignores definition in config file)',
            dest='interface',
        )

        # set port
        self.add_argument(
            '--port',
            '-p',
            help='define port to provide bacnet functionality (ignores definition in config file)',
            dest='port',
        )

        # load examples
        self.add_argument(
            '--examples',
            '-e',
            help='add example objects on startup',
            action="store_true",
            dest='examples',
        )

        # deactivate hardware polling
        self.add_argument(
            '--nopoll',
            '-n',
            help='deactivate hardware polling',
            action="store_true",
            dest='deactivate_hardware_poll',
        )

        # set verbose mode
        self.add_argument(
            '--verbose',
            '-v',
            help='print output to command line',
            action='store_true',
            dest='verbose',
        )

        # set debug level
        self.add_argument(
            '--level',
            '-d',
            help='define debug level',
            dest='level',
            default=None,
        )

        # set debug logger
        self.add_argument(
            '--debug',
            nargs='*',
            help='add console log handler to each debugging logger',
            dest='debug',
        )

        # set debug colors
        self.add_argument(
            '--color',
            help='turn on color debugging',
            action='store_true',
            dest='color',
        )

        # set config file
        self.add_argument(
            '--ini',
            help="device object configuration file",
            default="BACnet.ini",
            dest='ini',
        )

        # set command
        self.add_argument(
            help='specify operation command',
            type=str,
            dest='command',
            choices=commands,
        )

    def parse_args(self, *args, **kwargs):
        """
        This function wraps the parse_args of ConfigArgumentParser to intercept version requests.

        :return: self
        """

        obj = ArgumentParser.parse_args(self, *args, **kwargs)

        section_data = {}

        if os.path.exists(obj.ini):
            # read in the configuration file
            config = ConfigParser()
            config.read(obj.ini)
            self._debug('   - config: %r', config)

            # check for BACpypes section
            if not config.has_section('BACnet'):
                self._debug('INI file with BACnet section required')

            else:
                section_data = dict(config.items('BACnet'))

        else:
            self._debug('INI file required')

        # convert the contents to an object
        ini_obj = type('ini', (object,), section_data)
        self._debug('   - ini_obj: %r', ini_obj)

        ini_obj.filename = obj.ini

        # add the object to the parsed arguments
        setattr(obj, 'ini', ini_obj)

        # store argument object
        self.arg_object = obj

        # return self
        return self

    def update(self):
        """
        This function updates the argument object.

        :return: parsed parameters
        """

        # read argument object
        obj = self.arg_object

        # checking for port parameter
        port = getattr(obj, 'port', None)

        # check if port was defined
        if port is not None:
            obj.ini.port = port

        # checking for interface parameter
        interface = getattr(obj, 'interface', None)

        # check if interface was defined
        if interface is not None:

            # retrieve ip_address from interface
            address = get_local_ip(interface)

            # check if address was retrieved
            if address is None:
                self._error(
                    'IP address could not be retrieved from %s! fallback to config file' %
                    interface
                )
            else:
                setattr(obj.ini, 'address', address)

                if port is not None:
                    self._info('IP and Port changed to %s:%s' % (address, port))

                else:
                    self._info('IP changed to %s' % address)

        elif port is not None:
            self._info('Port changed to %s' % port)

        # return argument object
        return obj
