# pylint: disable=

"""
BACnet System Module
--------------------

This module contains the bacnet system class.
"""

import inspect
import os
import signal
import subprocess
import sys
from threading import Lock
import time

from bacnet.debugging import ModuleLogger, set_debug, bacnet_debug, get_loggers, iso_now

from bacnet.console import create_console
from bacnet.console.creator import print_values

from bacnet.app import create_app

from bacnet.object.hardware import discover_hardware_objects

from .config import ConfigManager
from .config.parser import FullArgumentParser
from .managing import server_manager
from .version import __program__, __version__


ModuleLogger(level='INFO')


@bacnet_debug(formatter='%(levelname)s:system: %(message)s')
class BACnetSystem(object):
    # pylint: disable=unused-argument, no-self-use, broad-except, too-many-instance-attributes
    """
    This class handles the BACnet system.
    """

    application = None
    console = None
    manager = None

    stdin = None
    stdout = None
    stderr = None

    def __init__(self, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
        """
        This function initializes the bacnet system.

        :param stdin: define stdin
        :param stdout: define stdout
        :param stderr: define stderr
        :return: None
        """

        self._debug('__init__ %r, %r, %r', stdin, stdout, stderr)

        self.exit_code = 0
        self.exiting = Lock()

        self.pid = os.getpid()

        self.application = None
        self.console = None
        self.webgui = None
        self.device = None
        self.pid = os.getpid()

        # set stdin
        self.stdin = stdin

        # set stdout
        self.stdout = stdout

        # set stderr
        self.stderr = stderr

        # collect allowed commands
        self.commands = tuple(
            attribute[3:] for attribute in dir(self) if attribute.startswith('do_')
        )

        # initialize logger
        ModuleLogger(inspect.stack()[1][0].f_globals)

        # assign interrupt methods
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.shutdown)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self.console_interrupt)

        # print info message
        self._info('starting at %s' % iso_now())

        # parse parameters and config file
        config_args = FullArgumentParser(
            commands=self.commands,
            description=__program__,
        ).parse_args()

        # set initial logger config
        self.log_queue = set_debug(
            args=config_args.arg_object,
            stream=self.stderr,
        )

        # update parsed parameters
        config_args = config_args.update()

        # read execution command
        cmd = config_args.command

        self._debug('initialization')
        self._debug('   - args: %r', config_args)

        try:

            # execute command
            getattr(self, 'do_%s' % cmd)(config_args)

        except Exception as error:
            self._exception('an error has occurred: %s', error)

        finally:
            self._debug('done')

        self.exit()

    def console_interrupt(self, *args):
        """
        This function is the catch for interrupts.

        :return: None
        """

        self._debug('console_interrupt %r', args)

        if os.getpid() == self.pid:
            self._debug('This is me: %i' % self.pid)
            if (self.console is None or not self.console.is_alive()) and \
                (self.webgui is None or not self.webgui.is_alive()):
                if self.application is None or not self.application.is_alive():
                    self.exit(1)

    def shutdown(self, *args):
        """
        This function shuts down the process.

        :return: None
        """

        # exit
        self.exit(1)

    def exit(self, code=0):
        """
        This function exits the system.

        :param code: exit code
        :return: None
        """

        self._debug('initializing exit procedure')

        locked = self.exiting.acquire(False)

        # check if already exiting
        if not locked or self.pid != os.getpid():
            # reset exit code
            if self.exit_code == 0 and code != 0:
                self.exit_code = code

            # exit
            return

        # set exiting
        self.exit_code = code

        # shutdown subprocesses
        for process in ('application', 'console', 'webgui'):
            # get process
            obj = getattr(self, process, None)

            try:
                # check if process exists and is alive
                if obj is not None and obj.is_alive():
                    self._debug('stopping process: "%s"' % process)
                    obj.terminate()
                    obj.join(5)

            except Exception as error:
                self._exception(error)

        # print info message
        self._info('shutting down at %s' % iso_now())

        self.log_queue.join(1)

        sys.exit(self.exit_code)

    def do_start(self, config_args, console=False, webgui=False):
        # pylint: disable=unused-variable
        """
        This function initiates the BACnet system start up as reactive application.

        :param config_args: configuration arguments
        :return: None
        """

        self._debug('running as %r', os.getpid())

        try:
            # check if console and webgui were set
            if console and webgui:
                raise RuntimeError('console and webgui are not allowed to run simultaneously')

            # specify device initials
            device_init = {
                'applicationSoftwareVersion': __version__,
                'modelName': __program__,
                'description': 'Masterarbeit Grosch',
            }

            # get manager and server
            self.manager = server_manager(
                self.log_queue,
                config_args.ini.address,
                config_args.ini.port,
                console=console,
                webgui=webgui,
            )

            # create project specific application
            device, self.application = create_app(
                config_args,
                device_init=device_init,
                stdout=self.stdout,
                single=not console and not webgui,
                deactivate_hardware_poll=config_args.deactivate_hardware_poll,
            )

            # check if shell is requested
            if console:
                # create project specific console
                self.console = create_console(
                    device,
                    self.application,
                    stdin=os.dup(self.stdin.fileno()),
                    stdout=self.stdout,
                )

            # check if webgui is requested
            if webgui:
                # import webgui process
                from bacnet.webgui import create_webgui

                # create webgui process
                self.webgui = create_webgui(
                    address=config_args.ini.address.split('/')[0].split(':')[0],
                    port=config_args.ini.webport,
                )

            self._debug('running')

            if console:
                self.console.join()
                self.application.terminate()

            elif webgui:
                self.webgui.join()
                self.application.terminate()

            self.application.join()

        except Exception as error:
            self._exception('an error has occurred: %s', error)

            # exit program
            self.exit(1)

    def do_shell(self, config_args):
        """
        This function initiates the BACnet system start up as shell.

        :param config_args: configuration arguments
        :return: None
        """

        # call start up function
        self.do_start(config_args, console=True)

    def do_webgui(self, config_args):
        """
        This function initiates the BACnet system start up as web gui.

        :param config_args: configuration arguments
        :return: None
        """

        # call start up function
        self.do_start(config_args, webgui=True)

    def do_buggers(self, config_args):
        """
        This function lists all buggers.

        :param config_args: configuration arguments
        :return: None
        """

        # get all buggers
        loggers = get_loggers()

        values = [
            (
                'Name',
                'Description',
            ),
        ]

        # get debuggers
        debuggers = config_args.debug

        for logger in loggers:
            # check if logger has correct prefix
            if debuggers is not None and not \
                any(logger.startswith(debugger) for debugger in debuggers):
                # go to next logger
                continue

            module_name = logger.rpartition('.')[0]
            obj_name = logger.rpartition('.')[-1]
            description = None

            # get description
            if logger in sys.modules:
                description = sys.modules[logger].__doc__

            elif module_name in sys.modules and hasattr(sys.modules[module_name], obj_name):
                description = getattr(getattr(sys.modules[module_name], obj_name), '__doc__', None)

            elif logger == __name__:
                description = __doc__

            elif module_name == __name__:
                description = getattr(globals().get(obj_name), '__doc__', None)

            if description is None:
                description = '-'

            else:
                if '---\n' in description:
                    description = description.rpartition('---\n')[-1]

                if '\n' in description:
                    description = tuple(
                        line.lstrip() for line in description.split('\n') if line != ''
                    )[0]

            # create value line
            value_line = (logger, description)

            # add value line
            values.append(value_line)

        # print list
        print_values(values)

    def do_hardware(self, config_args):
        """
        This function lists all creatable hardware objects.

        :param config_args: configuration arguments
        :return: None
        """

        values = []

        # get hardware dictionary
        hardware_dict = discover_hardware_objects()

        # list all hardware objects
        for obj_id, hw_dict in hardware_dict.iteritems():
            # read object type
            obj_type = obj_id[0]

            # get name
            name = hw_dict.get('name', '?')

            # read description
            description = hw_dict.get('initials', {}).get('description', '-')

            # add info to list
            values.append((name, description, obj_type))

        # sort values by description
        values.sort()

        # add headline
        values.insert(
            0,
            (
                'Name',
                'Description',
                'Object Type',
            )
        )

        # print list
        print_values(values)

    def do_config(self, config_args):
        """
        This function sets configuration parameters.

        :param config_args: configuration arguments
        :return: None
        """

        self._info('Configuration Mode')

        # predefine defaults
        defaults = {}

        # check if address was set
        if hasattr(config_args.ini, 'address'):
            defaults['address'] = config_args.ini.address

        # check if port was set
        if hasattr(config_args.ini, 'port'):
            defaults['port'] = config_args.ini.port

        time.sleep(0.1)

        try:

            # start config manager
            config_manager = ConfigManager(
                stdin=self.stdin,
                stdout=self.stdout,
                defaults=defaults,
                filename=config_args.ini.filename,
            )

            # store new config
            config_manager.store()

        except KeyboardInterrupt:
            # append new line
            self.stdout.write('\n')
            self.stdout.flush()

            # exit program
            self.exit(2)

    def do_set_tag(self, config_args):
        """
        This function initiates the BACnet system start up as shell.

        :param config_args: configuration arguments
        :return: None
        """

        # get all version tags
        versions = [x for x in subprocess.check_output(['git', 'tag']).split('\n') if x]

        # read current version tag
        version_tag = '.'.join(__version__.split('.')[:2])

        # check if version tag was set already
        if not version_tag in versions:
            self._info(subprocess.check_output(['git', 'tag', version_tag]))

        else:
            self._info('tag "%s" already set\n' % version_tag)
