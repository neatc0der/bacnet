# pylint: disable=

"""
File Access Parser Module
-------------------------

This module provides file access parsers.
"""

from __future__ import absolute_import

from bacpypes.apdu import AtomicWriteFileACK, AtomicReadFileACK


def __file_ack(apdu):
    """
    This function parses read/write file access acknowledgements.

    :param apdu: AtomicReadFileACK or AtomicWriteFileACK
    :return: parsed dictionary
    """

    result = {}

    # check if ack is atomic read file access
    if isinstance(apdu, AtomicReadFileACK):
        # get access method
        method = apdu.accessMethod

        # check if access method is stream access
        if hasattr(method, 'streamAccess'):
            # read data
            data = method.streamAccess.fileData

            # retrieve start position
            start = method.streamAccess.fileStartPosition

            # set access method
            method = 'streamAccess'

        else:
            # read data
            data = method.recordAccess.fileRecordData

            # set record count
            result['count'] = method.recordAccess.returnedRecordCount

            # retrieve start record
            start = method.recordAccess.fileStartRecord

            # set access method
            method = 'recordAccess'

        # set end of file
        result['eof'] = apdu.endOfFile

        # set data
        result['data'] = data

    # check if ack is atomic write file access
    elif isinstance(apdu, AtomicWriteFileACK):
        # check if access method is stream access
        if hasattr(apdu, 'fileStartPosition'):
            # retrieve start position
            start = apdu.fileStartPosition

            # set access method
            method = 'streamAccess'

        else:
            # retrieve start record
            start = apdu.fileStartRecord

            # set access method
            method = 'recordAccess'

        # set start position
        result['start'] = start

    # unsupported ack type
    else:
        # create error message
        raise RuntimeError('Unsupported ACK: %s' % apdu.__class__.__name__)

    # set start position
    result['start'] = start

    # set access method
    result['access'] = method

    # return result dictionary
    return result


def read_file_ack(apdu):
    """
    This function parses atomic read file acknowledgements.

    :param apdu: AtomicReadFileACK
    :returns: parsed data, output
    """

    # get parsed data
    result = __file_ack(apdu)

    # initialize output
    output = 'EOF = %s\n%s' % (result['eof'], result['data'])

    # return parsed data, output
    return result, output


def write_file_ack(apdu):
    """
    This function parses atomic write file acknowledgements.

    :param apdu: AtomicWriteFileACK
    :returns: parsed data, output
    """

    # get parsed data
    result = __file_ack(apdu)

    # initialize output
    output = 'ACK: start = %s' % result['start']

    # return parsed data, output
    return result, output
