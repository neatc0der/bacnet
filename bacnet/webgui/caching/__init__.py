# pylint: disable=broad-except, import-error, global-variable-not-assigned, global-statement

"""
Caching Module
--------------

This module provides all necessary functions to access the cache in context of commands and objects.
"""

from __future__ import print_function

from bacnet_access import api_transmit, api_create

from .cache import get_object_ids, get_objects, set_object, has_objects, set_line, has_line


TRANSMISSIONS = {}


def cache_transmit(line):
    """
    This functions stores the supplied line in cache until it's being commited.

    :param line: command
    :return: None
    """

    # get global storage of lines
    global TRANSMISSIONS

    # check if line was cached already
    if not has_line(line):
        # cache line
        set_line(line, timeout=15)

        # split line
        split_line = line.split(' ')

        # check if length of split commands
        if len(split_line) > 2:
            # get addresses
            addresses = TRANSMISSIONS.get(split_line[0], {})

            # add command to requests for addresses
            values = addresses.get(split_line[1], ()) + (' '.join(split_line[2:]),)

            # store commands for address
            addresses[split_line[1]] = values

            # store updated commands in global variable
            TRANSMISSIONS[split_line[0]] = addresses

        else:
            # transmit immediately
            if api_transmit(line) is False:
                # print error if transmission failed
                print('!! FAILED to transmit: ' + line)


def cache_transmission_commit():
    """
    This function commits all cached lines.

    :return: None
    """

    # get global storage of lines
    global TRANSMISSIONS

    # loop through all commands
    for cmd, addresses in TRANSMISSIONS.iteritems():
        # loop through all addresses
        for address, values in addresses.iteritems():
            # set maximum count of units within one request
            units = 20

            # loop through all requests until all were handled
            while len(values) > 0:
                # restore line of command
                base_line = '%s %s %%s' % (cmd, address)

                # initialize properties
                properties = ''

                # loop through maximum amounts of units
                for i in xrange(units if len(values) > units else len(values)):
                    # get content of the line
                    value = values[i]

                    try:
                        # check if creating the request failed
                        if api_create(base_line % value) is None:
                            # add property index
                            value += ' 0'

                    except Exception:
                        # add property index
                        value += ' 0'

                    try:
                        # check if creating the request failed
                        if api_create(base_line % value) is None:
                            # continue
                            continue

                    except Exception as error:
                        # print error and continue
                        print(error)
                        continue

                    # add property
                    properties += ' %s' % value

                # remove handled lines from remaining values
                values = values[units:]

                # transmit newly created line
                if api_transmit(base_line % properties) is False:
                    # print error
                    print('!! FAILED to transmit: ' + (base_line % properties))

    # reset global storage
    TRANSMISSIONS = {}
