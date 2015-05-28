# pylint: disable=too-few-public-methods

"""
Console Handler Module
--------------

This module provides requests and parser.
"""

from __future__ import absolute_import

import shlex

from bacpypes.pdu import Address

from .simple import whois_request, iam_request, read_request, write_request, whohas_request, \
    ihave_request, cast_value
from .fileaccess import rdrec_request, rdstr_request, wrrec_request, wrstr_request
from .objects import create_request, delete_request
from .events import subscribe_request
from .local import print_values


# collect all commands
COMMAND_DICT = {}

# loop through all global objects
for name, reference in globals().items():
    # check if object is a request
    if name.endswith('_request') and not name.startswith('_'):
        # format command name
        key = name.rpartition('_')[0]

        # store command reference
        COMMAND_DICT[key] = reference


def request_creator(line, console=None, local_id=1):
    """
    This function parses arguments and calls specific command.

    :param line: string of command line
    :param console: console object
    :return: request object
    """

    # split arguments
    args = list(arg.decode('unicode_escape').encode('utf8') for arg in shlex.split(line))

    if len(args) < 1:
        raise RuntimeError('not enough arguments provided')

    # get command
    cmd = args[0]

    # slice arguments
    args = args[1:]

    # initialize request
    request = None

    # check if command handler was defined
    if cmd in COMMAND_DICT:
        # check if console was provided
        if console is not None and hasattr(console, '_debug'):
            console._debug('do_write %r', args)

        # create request
        request = COMMAND_DICT[cmd](args, console=console)

        # check if destination is local
        if str(request.pduDestination).isdigit():
            # set local source and destination address
            request.pduDestination = Address(('', str(request.pduDestination)))
            request.pduSource = Address(('', local_id))

        else:
            # check if console was provided
            if console is not None and hasattr(console, 'node_address'):
                # set network source address
                request.pduSource = Address(console.node_address)

    # check if console was provided
    elif console is not None and hasattr(console, 'default'):
        # call default line
        return console.default(line)

    # return request
    return request
