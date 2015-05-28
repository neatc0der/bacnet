# coding=utf-8
# pylint: disable=too-few-public-methods, invalid-name, broad-except, too-many-public-methods

"""
Console Basic Module
--------------------

This module provides a basic BACpypes console commands object.
"""

from __future__ import absolute_import

from cmd import Cmd
from collections import OrderedDict
import gc
from multiprocessing import Process
import os
import readline
import shlex
import signal
import sys
from threading import Thread
import types

from bacpypes import apdu as bacpypes_apdu

from bacnet.debugging import bacnet_debug, ModuleLogger, get_loggers, set_handler

from bacnet.system.version import get_version
from bacnet.system.managing import client_manager

from bacnet.api import BACnetAPI

from .creator import print_values, request_creator, COMMAND_DICT
from .parser import response_parser


# enabling logging
ModuleLogger(level='INFO')


@bacnet_debug(formatter='%(levelname)s:console: %(message)s')
class BasicConsole(Cmd, Process):
    # pylint: disable=unused-argument, too-many-instance-attributes, arguments-differ
    """
    This class describes a basic BACpypes shell including simple commands.
    """

    device = None
    application = None

    def __init__(self, device, application, *args, **kwargs):
        """
        This function constructs the console commands object and links it to the application.

        :param application: application
        :return: BasicConsole instance
        """

        self._debug('__init__ %r, %r, %r, %r', device, application, args, kwargs)

        if 'prompt' in kwargs:
            self.prompt = kwargs['prompt']
            del kwargs['prompt']

        else:
            self.prompt = '> '

        # remove keys for additional processing
        # for key in ('processes', 'out_queues', 'in_queues'):
        #     if key in kwargs:
        #         del kwargs[key]

        Cmd.__init__(self, *args, **kwargs)
        Process.__init__(self, name='console')

        # gc counters
        self.type2count = {}
        self.type2all = {}

        # execution space for the user
        self._locals = {}
        self._globals = {}

        # bacpype objects
        self.device = device
        self.application = application

        # activate rawinput and thereby line completion
        self.use_rawinput = sys.version_info[0] != 3

        # activate shell
        self.allow_shell = True

        # deactivate python exec
        self.allow_exec = False

        # set ignore command due to interrupt
        self.ignore_command = False

        # set callback output
        self.info_dict = OrderedDict({
            'local': True,
            'incoming': True,
            'outgoing': True,
        })

        # populate callback output
        for request_type in dir(bacpypes_apdu):
            # check if name is request type
            if request_type.endswith('Request') or request_type.endswith('ACK'):
                # lowercase request type
                request_type = request_type.lower()

                # check if request type was already declared
                if not request_type in self.info_dict:
                    # set request type
                    self.info_dict[request_type] = True

        self.info_dict['iamrequest'] = False
        self.info_dict['whoisrequest'] = False

        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.shutdown)

        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self.console_interrupt)

        # get manager
        manager = client_manager()

        # get log queue
        self.log = manager.log()

        # get node address
        self.node_address = manager.ip_address().encode('ascii')

        # get node address
        self.node_port = manager.port().encode('ascii')

        # get api access
        self.api = BACnetAPI(manager.app(), manager.console(), 3)

        # predefine thread
        self.comm_thread = None

        # start process
        self.start()

    def console_interrupt(self, *args):
        """
        This function is the catch for interrupts.

        :return: None
        """

        # check if this the forked process
        if self._popen is not None:

            self._debug('console_interrupt %r', args)

            # print info
            self.stdout.write('Keyboard interrupt trapped - press enter to continue\n')

        else:
            # set ignore current command
            self.ignore_command = True

            # send new line to stdin
            self.stdin.flush()

    def check_queue(self):
        """
        This function checks for queued outgoing requests.

        :return: None
        """

        self._debug('running: comm thread')

        # handle request queue
        while True:
            try:
                # wait for request
                apdu = self.api.receive()

                # initiate callback
                self.callback(apdu)

            except Exception as error:
                self._exception(error)
                break

        self._debug('finished: comm thread')

    def run(self):
        """
        This function initiates processing.

        :return: None
        """

        self._debug('running as %r', self.pid)

        try:
            # open file descriptor if needed
            if isinstance(self.stdin, int):
                # override sys.stdin
                sys.stdin = self.stdin = os.fdopen(self.stdin, 'w')

            # start thread
            self.comm_thread = Thread(target=self.check_queue)
            self.comm_thread.setDaemon(True)
            self.comm_thread.start()

            # enter loop
            self.cmdloop()

            self.stdin.close()

        except Exception as error:
            self._exception('exception: %r', error)

        finally:
            self._debug('finished')

    def terminate(self):
        """
        This function terminates processing.

        :return: None
        """

        self._debug('terminated')

        # terminate process
        self._popen.terminate()

    def shutdown(self, *args):
        """
        This function shuts down the process.

        :return: None
        """

        self._debug('shutdown')

        # TODO: terminate raw_input

    def preloop(self):
        """
        This function prepares loop by loading readline history file.

        :return: None
        """

        # call predecessor function
        Cmd.preloop(self)

        try:
            # load history
            readline.read_history_file(sys.argv[0] + '.history')

        except Exception as error:
            self._error("history error: %s\n" % error)

    def postloop(self):
        """
        This function wraps up readline history after loop has finished.

        :return: None
        """

        try:
            # store history
            readline.write_history_file(sys.argv[0] + '.history')

        except Exception as error:
            self._error("history error: %s\n" % error)

        # call predecessor function
        Cmd.postloop(self)

    @staticmethod
    def _split(args):
        """
        This function splits line and removes escapes.

        :param args: line of command
        :return: split and unescaped line of command
        """

        # return
        return [arg.decode('unicode-escape').encode('ascii') for arg in shlex.split(args)]

    def onecmd(self, line, queue=True):
        """
        This function interprets the command line.

        :param line: user command line
        :return: command result
        """

        self._debug('onecmd %r', line)

        # check if command should be ignored
        if self.ignore_command is True:
            # unset ignore command
            self.ignore_command = False

            # exit
            return None

        # let the real command run, trapping errors
        try:
            # parse line
            cmd, arg, line = self.parseline(line)

            # check if line is empty
            if not line:
                return self.emptyline()

            # check if command was supplied
            if cmd is None:
                return self.default(line)

            # set last line to current
            self.lastcmd = line

            # check if line was set to EOF
            if line == 'EOF':
                self.lastcmd = ''

            # check if command was supplied
            if cmd == '':
                return self.default(line)

            else:
                try:
                    # check if specific function was defined
                    if hasattr(self, 'do_' + cmd) or cmd == 'shell':
                        request = getattr(self, 'do_' + cmd)(arg)

                    # use default handler
                    else:
                        request = request_creator(line, console=self, local_id=3)

                    # check if request was defined
                    if isinstance(request, bacpypes_apdu.APDU):
                        self._debug('   - request: %r', request)

                        # check if request should be queued
                        if queue:
                            # queue request
                            self.api.send(request)

                            # reset result to None
                            request = None

                    # return result
                    return request

                except Exception as error:
                    # self._exception('exception: %r', error)
                    self._error(error)

        except Exception as e:
            self._exception("exception: %r", e)

    def __pretty_stdout(self, obj, prefix='', offset=0, inline=False):
        """
        This function prints pretty objects to stdout.

        :return: None
        """

        class IndentedOutput(object):
            """
            This class simulates stdout.
            """

            offset = 0
            obj = None

            def __init__(self, output_obj, intend):
                """
                This function initializes an instance.
                """

                if not isinstance(intend, int) or intend < 0:
                    raise ValueError('offset must be integer greater or equal 0')

                self.offset = intend

                self.obj = output_obj

            def write(self, text):
                """
                This function writes to stdout.
                """

                self.obj.stdout.write(' ' * self.offset + text)

            def flush(self):
                """
                This function flushes stdout
                """

                self.obj.stdout.flush()

        self.stdout.write(prefix)

        start = ''
        end = ''
        loop = False

        if isinstance(obj, list):
            start = '['
            end = ']'
            loop = obj
        elif isinstance(obj, tuple):
            start = '('
            end = ')'
            loop = obj
        elif isinstance(obj, dict):
            start = '{'
            end = '}'
            loop = obj.items()

        cols = len(prefix) + offset
        offset_cols = cols + 4

        self.stdout.write(start)

        if loop is not False:
            for argument in loop:
                if isinstance(argument, tuple):
                    self.stdout.write('\n' + offset_cols * ' ' + '%r: ' % argument[0])
                    self.__pretty_stdout(argument[1], offset=offset_cols, inline=True)
                    self.stdout.write(',')

                else:
                    self.stdout.write('\n' + offset_cols * ' ')
                    self.__pretty_stdout(argument, offset=offset_cols, inline=True)
                    self.stdout.write(',')

            if obj:
                self.stdout.write('\n' + cols * ' ')

        else:
            self.stdout.write(str(obj) if not isinstance(obj, basestring) else '%r' % obj)

        self.stdout.write(end)

        if not inline:
            self.stdout.write('\n')

            if hasattr(obj, 'debug_contents'):
                obj.debug_contents(file=IndentedOutput(self, cols))

    def callback(self, apdu):
        """
        This function provides a callback for command executions.

        :param apdu: message
        :return: None
        """

        self._debug('callback')

        # check if message came from the network
        transmit = str(apdu.pduSource) in (None, self.node_address) or str(apdu.pduSource).isdigit()

        # set format
        formatter = '%s (Service: {apduService}' % apdu.__class__.__name__
        if apdu.apduInvokeID is not None:
            formatter += ', ID: {apduInvokeID}'
        formatter += ')'

        if transmit:
            formatter = '>>>> {pduDestination} ' + formatter + ' >>>>'

        else:
            formatter = '<<<< {pduSource} ' + formatter + ' <<<<'

        self._debug(formatter.format(**apdu.__dict__))

        # acknowledge handler
        response_parser(apdu, console=self)

    def emptyline(self):
        """
        This function ignores empty lines.

        :return: None
        """

        pass

    def default(self, line):
        # pylint: disable=exec-used
        """
        This function handles the command line if no command was found.

        :param line: command line
        :return: None
        """

        if not self.allow_exec:
            return Cmd.default(self, line)

        try:
            exec(line) in self._locals, self._globals

        except Exception as e:
            self.stdout.write('%s : %s\n' % (e.__class__.__name__, e))

    def get_names(self):
        """
        This function collects all attributes.

        :return: list of attributes
        """

        # get all attributes of class
        attributes = dir(self.__class__)

        # add request functions
        attributes.extend(list('do_%s' % name for name in COMMAND_DICT.keys()))

        # return all attributes
        return attributes

    def do_version(self, args):
        """
        This function prints current software version.

        Usage: version

        :param args: string of parameters
        :return: None
        """

        # print version
        self.stdout.write('%s\n' % get_version())


    def do_gc(self, args):
        """
        This function prints current garbage collection information.

        Usage: gc

        :param args: string of parameters
        :return: None
        """

        # snapshot of counts
        type2count = {}
        type2all = {}
        for obj in gc.get_objects():
            if isinstance(obj, types.InstanceType):
                type2count[obj.__class__] = type2count.get(obj.__class__, 0) + 1
                type2all[obj.__class__] = type2all.get(obj.__class__, 0) + sys.getrefcount(obj)

        # count the things that have changed
        ct = [
            (
                t.__module__,
                t.__name__,
                type2count[t],
                type2count[t] - self.type2count.get(t, 0),
                type2all[t] - self.type2all.get(t, 0),
            )
            for t in type2count.iterkeys()
        ]

        # ready for the next time
        self.type2count = type2count
        self.type2all = type2all

        fmt = '%-30s %-30s %6s %6s %6s\n'
        self.stdout.write(fmt % ('Module', 'Type', 'Count', 'dCount', 'dRef'))

        # sorted by count
        ct.sort(lambda x, y: cmp(y[2], x[2]))
        for i in range(min(10, len(ct))):
            m, n, c, delta1, delta2 = ct[i]
            self.stdout.write(fmt % (m, n, c, delta1, delta2))
        self.stdout.write('\n')

        self.stdout.write(fmt % ('Module', 'Type', 'Count', 'dCount', 'dRef'))

        # sorted by module and class
        ct.sort()
        for m, n, c, delta1, delta2 in ct:
            if delta1 or delta2:
                self.stdout.write(fmt % (m, n, c, delta1, delta2))
        self.stdout.write('\n')

    def do_info(self, args):
        """
        This function adjusts package output.

        Usage: info [ ( on | off ) ( <msg_type> )* ]

        :param args: string of parameters
        :return: None
        """

        # parse arguments
        args = args.split()

        # check if arguments were provided
        if len(args) > 0:

            # check if first argument is correct
            if not args[0] in ('on', 'off'):
                raise ValueError('first argument must be "on" or "off"')

            # set switch
            switch = args[0] == 'on'

            # read type list
            type_list = args[1:] if len(args) > 1 else self.info_dict.keys()

            # loop through all provided
            for msg_type in type_list:
                # check if message type exists
                if not msg_type in self.info_dict:
                    ValueError('"%s" is not a message type' % msg_type)

                self.info_dict[msg_type] = switch

        else:
            # print info
            print_values(
                (('Name', 'Print'),) + tuple(msg_type for msg_type in self.info_dict.items())
            )

    def do_exit(self, args):
        """
        This function provides an exit.

        Usage: exit

        :param args: string of parameters
        :return: None
        """

        self._debug('do_exit %r', args)

        return -1

    def do_EOF(self, args):
        """
        This function provides an exit.

        Usage: EOF

        :param args: string of parameters
        :return: None
        """

        self._debug('do_EOF %r', args)

        return self.do_exit(args)

    def do_buggers(self, args):
        """
        This function lists all buggers.

        Usage: buggers [ <prefix> ]

        :param args: string of parameters
        :return: None
        """

        self._debug('do_buggers %r', args)

        # parse arguments
        args = args.split()

        if len(args) > 1:
            raise ValueError('too many arguments')

        # get all loggers
        loggers = get_loggers()

        # print all loggers
        for logger in loggers:
            if len(args) == 0 or logger.startswith(args[0]):
                self.stdout.write('  %s\n' % logger)

        self.stdout.write('\n')

    def do_bugin(self, args):
        """
        This function activates debugging for mentioned buggers.

        Usage: bugin ( <bugger> )+

        :param args: string of parameters
        :return: None
        """

        self._debug('do_bugin %r', args)

        # parse arguments
        args = args.split()

        if len(args) < 1:
            raise ValueError('too few arguments')

        # set level to debug for all buggers
        for logger in args:
            if not logger.startswith('bacnet.console'):
                self.stdout.write('logger out of scope: subprocess\n')
            else:
                set_handler(logger, level='DEBUG', details=1)

    def do_bugout(self, args):
        """
        This function deactivates debugging for mentioned buggers.

        Usage: bugout ( <bugger> )+

        :param args: string of parameters
        :return: None
        """

        self._debug('do_bugout %r', args)

        # parse arguments
        args = args.split()

        if len(args) < 1:
            raise ValueError('too few arguments')

        # set level to error for all buggers
        for logger in args:
            if not logger.startswith('bacnet.console'):
                self.stdout.write('logger out of scope: subprocess\n')
            else:
                set_handler(logger, level='ERROR', details=1)

    def do_shell(self, args):
        """
        This function provides an access to shell execution.

        Usage: ! <command>

        :param args: string of parameters
        :return: None
        """

        self._debug('do_shell %r', args)

        # check if shell execution is allowed
        if self.allow_shell:
            os.system(args)

        else:
            self._error('shell not allowed')

    # helper function
    def print_text(self, text):
        """
        This function prints help text.

        :param text: help text
        :return: None
        """

        # print help text
        self.stdout.write('%s\n' % text)
        self.stdout.flush()


# add appropriate help text to BasicConsole
for name, reference in COMMAND_DICT.items():
    # read help text
    help_text = reference.__doc__

    # check if usage is defined
    if 'Usage:' in help_text:

        # shorten help text
        help_text = help_text[help_text.lower().find('usage:'):].split('\n')[0]

        # set help text
        setattr(
            BasicConsole,
            'help_%s' % name,
            lambda self, text=help_text: self.print_text(text)
        )

    else:
        BasicConsole._warning('missing help text for %s', name)
