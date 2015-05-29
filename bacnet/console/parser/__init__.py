# pylint: disable=too-many-branches

"""
Acknowledgement Parser Module
------------------------------

This module provides acknowledgement parsing handlers.
"""

from __future__ import absolute_import

from bacpypes.apdu import Error, IAmRequest, SimpleAckPDU, ComplexAckPDU, APDU

from bacnet.debugging import ModuleLogger, bacnet_debug

from .simple import read_property_ack, read_property_multiple_ack, whohas_request, whois_request, \
    iam_request, ihave_request
from .events import subscribe_cov_property_request, subscribe_cov_request, \
    confirmed_cov_notification_request, unconfirmed_cov_notification_request
from .fileaccess import read_file_ack, write_file_ack


# enable debugging
ModuleLogger()


# collect all commands
REQUEST_DICT = {}

# loop through all global objects
for name, reference in globals().items():
    # check if object is a request
    if (name.endswith('_ack') or name.endswith('_request')) and not name.startswith('_') and \
        hasattr(reference, '__doc__'):
        # get help text
        help_text = reference.__doc__

        # set param
        param = ':param apdu:'

        # check if usage is defined
        if param in help_text:

            # get key
            key = help_text[help_text.find(param)+len(param):].split('\n')[0].strip()

            # store acknowledgement reference
            REQUEST_DICT[key] = reference


@bacnet_debug
def response_parser(apdu, console=None):
    """
    This function parses request messages and returns parsed data.

    :param apdu: request message
    :param console: console object
    :return: parsed data
    """

    response_parser._debug('parsing %s' % apdu)

    # check if apdu was defined
    if not isinstance(apdu, APDU):
        raise RuntimeError('message is not a apdu')

    # get request name
    request_name = apdu.__class__.__name__

    # initialize result
    result = {
        'class': request_name,
        'ack': isinstance(apdu, (SimpleAckPDU, ComplexAckPDU)),
        'source': '1' if apdu.pduSource is None else str(apdu.pduSource),
        'destination': str(apdu.pduDestination),
        'local': False,
        'content': {},
    }

    # interpret hex if existing
    if result['source'].startswith('0x'):
        result['source'] = str(int(result['source'], 16))

    if result['destination'].startswith('0x'):
        result['destination'] = str(int(result['destination'], 16))

    # check if source is local
    if result['source'].isdigit():
        src = u'local({0})'.format(result['source'])

    else:
        if not ':' in result['source']:
            result['source'] += ':47808'
        src = result['source']

    # check if source is local
    if result['destination'].isdigit():
        dst = u'local({0})'.format(result['destination'])

        # check if source is local
        if src.startswith('local'):
            result['local'] = True

    elif result['destination'] == 'None' and hasattr(console, 'node_address'):
        dst = '%s:%s' % (console.node_address, console.node_port)

    else:
        if not ':' in result['destination']:
            if hasattr(console, 'node_port'):
                result['destination'] += ':47808'
        dst = result['destination']

        # check if source is local
        if src.startswith('local') and hasattr(console, 'node_address'):
            src = '%s:%s' % (console.node_address, console.node_port)

    # initialize output
    output = u'(%s > %s) ' % (src, dst)
    # check if console object was provided

    # check if command handler was defined
    if request_name in REQUEST_DICT:
        # get parsed result
        result['content'], output_append = REQUEST_DICT[request_name](apdu)

        # append new output
        output += output_append

    else:
        if isinstance(apdu, IAmRequest):
            output += '%s: %s' % (
                console.node_address if apdu.pduSource is None else apdu.pduSource,
                apdu.iAmDeviceIdentifier,
            )

        elif isinstance(apdu, SimpleAckPDU):
            output += 'ACK'

        elif isinstance(apdu, Error):
            output += 'Error: %s, %s' % (apdu.errorClass, apdu.errorCode)

        else:
            output += 'unparsed packet: %r' % apdu

    output += '\n'

    if console is not None and hasattr(console, 'stdout'):
        # check if message is outgoing
        outgoing = not dst.startswith('local') and dst != console.node_address

        # get message type
        msg_type = apdu.__class__.__name__.lower()

        # check if printing should be supported
        printing = console.info_dict.get(msg_type, True) and \
                   ((result['local'] and console.info_dict['local']) or
                    (not result['local'] and ((outgoing and console.info_dict['outgoing']) or
                                              (not outgoing and console.info_dict['incoming']))))

        if printing:
            # print output
            console.stdout.write(output)
            console.stdout.flush()

        else:
            console._debug(u'suppressed message: (%s > %s) %s' % (src, dst, request_name))

    response_parser._debug('parsed result: %s' % result)

    # return parsed data
    return result
