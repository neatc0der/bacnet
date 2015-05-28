# pylint: disable=unused-argument

"""
File Access Handler Module
--------------------------

This module provides file access requests.
"""

from __future__ import absolute_import

from bacpypes.pdu import Address
from bacpypes.apdu import AtomicReadFileRequest, AtomicReadFileRequestAccessMethodChoice, \
    AtomicReadFileRequestAccessMethodChoiceStreamAccess, AtomicWriteFileRequestAccessMethodChoice, \
    AtomicWriteFileRequestAccessMethodChoiceStreamAccess, AtomicWriteFileRequest, \
    AtomicWriteFileRequestAccessMethodChoiceRecordAccess, \
    AtomicReadFileRequestAccessMethodChoiceRecordAccess


def __readfile_request(args, stream=False):
    """
    This function creates a read file record/stream request.

    :param args: list of parameters
    :param stream: is stream access
    :return: request
    """

    # read address, instance, start record and record count
    address, obj_inst, start, count = args

    # set type
    obj_type = 'file'

    # check if object instance is correct
    if not obj_inst.isdigit():
        raise ValueError('object instance invalid')

    # make object instance to integer
    obj_inst = int(obj_inst)

    # check if start record is correct
    if not start.isdigit():
        raise ValueError('start record invalid')

    # make start record to integer
    start = int(start)

    # check if record count is correct
    if not count.isdigit():
        raise ValueError('record count invalid')

    # make record count to integer
    count = int(count)

    # create request
    if stream:
        request = AtomicReadFileRequest(
            fileIdentifier=(obj_type, obj_inst),
            accessMethod=AtomicReadFileRequestAccessMethodChoice(
                streamAccess=AtomicReadFileRequestAccessMethodChoiceStreamAccess(
                    fileStartPosition=start,
                    requestedOctetCount=count,
                )
            )
        )

    else:
        request = AtomicReadFileRequest(
            fileIdentifier=(obj_type, obj_inst),
            accessMethod=AtomicReadFileRequestAccessMethodChoice(
                recordAccess=AtomicReadFileRequestAccessMethodChoiceRecordAccess(
                    fileStartRecord=start,
                    requestedRecordCount=count,
                )
            )
        )

    # send to specified address
    request.pduDestination = Address(address)

    # return created request
    return request


def __writefile_request(args, stream=False):
    """
    This function creates a write file stream/record request.

    :param args: list of parameters
    :param stream: is stream access
    :return: request
    """

    # read address, instance and start record
    address, obj_inst, start = args[:3]

    count = 0

    # set type
    obj_type = 'file'

    # check if object instance is correct
    if not obj_inst.isdigit():
        raise ValueError('object instance invalid')

    # make object instance to integer
    obj_inst = int(obj_inst)

    # check if start record is correct
    if not start.isdigit():
        raise ValueError('start record invalid')

    # make start record to integer
    start = int(start)

    if stream:
        # read data
        data = args[3]

    else:
        # read record count
        count = args[3]

        # check if record count is correct
        if not count.isdigit():
            raise ValueError('record count invalid')

        # make record count to integer
        count = int(count)

        # read data
        data = list(args[4:]) if len(args) > 4 else []

    # create request
    if stream:
        request = AtomicWriteFileRequest(
            fileIdentifier=(obj_type, obj_inst),
            accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                streamAccess=AtomicWriteFileRequestAccessMethodChoiceStreamAccess(
                    fileStartPosition=start,
                    fileData=data,
                )
            )
        )

    else:
        request = AtomicWriteFileRequest(
            fileIdentifier=(obj_type, obj_inst),
            accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                recordAccess=AtomicWriteFileRequestAccessMethodChoiceRecordAccess(
                    fileStartRecord=start,
                    recordCount=count,
                    fileRecordData=data,
                )
            )
        )

    # send to specified address
    request.pduDestination = Address(address)

    # return created request
    return request


def rdstr_request(args, console=None):
    """
    This function creates a read file stream request.

    Usage: rdstr <address> <instance> <start> <count>

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if arguments were provided
    if len(args) < 4:
        raise ValueError('too few arguments')

    elif len(args) > 4:
        raise ValueError('too many arguments')

    return __readfile_request(args, stream=True)


def rdrec_request(args, console=None):
    """
    This function creates a read file record request.

    Usage: rdrec <address> <instance> <start> <count>

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if arguments were provided
    if len(args) < 4:
        raise ValueError('too few arguments')

    elif len(args) > 4:
        raise ValueError('too many arguments')

    return __readfile_request(args, stream=False)


def wrstr_request(args, console=None):
    """
    This function creates a write file stream request.

    Usage: wrstr <address> <instance> <start> <data>

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if arguments were provided
    if len(args) < 4:
        raise ValueError('too few arguments')

    elif len(args) > 4:
        raise ValueError('too many arguments')

    return __writefile_request(args, stream=True)


def wrrec_request(args, console=None):
    """
    This function creates a write file record request.

    Usage: wrrec <address> <instance> <start> <count> ( <data> )* ...

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if arguments were provided
    if len(args) < 4:
        raise ValueError('too few arguments')

    return __writefile_request(args, stream=False)
