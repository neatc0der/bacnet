# pylint: disable=invalid-name

"""
File Access Handler Module
--------------------------

This module provides file access handlers.
"""

from __future__ import absolute_import

from bacpypes.errors import ExecutionError

from bacpypes.apdu import AtomicReadFileACK, AtomicWriteFileACK, \
    AtomicReadFileACKAccessMethodChoice, AtomicReadFileACKAccessMethodRecordAccess, \
    AtomicReadFileACKAccessMethodStreamAccess

from bacnet.debugging import ModuleLogger


# enable logging
ModuleLogger()


def __do_AtomicRecordAccess(self, apdu, obj, write=False):
    """
    This function reads data from record access and returns parsed data.

    :param apdu: incoming message
    :param obj: object
    :param write: specify if a read or write request is handed over
    :return: parsed data
    """
    result_dict = {}

    self._debug('__do_AtomicRecordAccess %r', apdu)

    # check if file access method is correct
    if obj.fileAccessMethod != 'recordAccess':
        raise ExecutionError(
            errorClass='services',
            errorCode='invalidFileAccessMethod',
        )

    # check if start record is correct
    elif not write and (apdu.accessMethod.recordAccess.fileStartRecord < 0 or
                        not hasattr(obj, '__len__') or
                        apdu.accessMethod.recordAccess.fileStartRecord >= len(obj)):
        raise ExecutionError(
            errorClass='services',
            errorCode='invalidFileStartPosition',
        )

    else:
        if write:
            # write file
            start_record = obj.WriteFile(
                apdu.accessMethod.recordAccess.fileStartRecord,
                apdu.accessMethod.recordAccess.recordCount,
                apdu.accessMethod.recordAccess.fileRecordData,
            )

            result_dict['start_pos'] = start_record
            result_dict['record_data'] = apdu.accessMethod.recordAccess.fileRecordData

            self._debug('   - start_record: %r', start_record)

            # create acknowledgement
            result_dict['resp'] = AtomicWriteFileACK(
                context=apdu,
                fileStartRecord=start_record,
            )

        else:
            # read file
            end_of_file, record_data = obj.ReadFile(
                apdu.accessMethod.recordAccess.fileStartRecord,
                apdu.accessMethod.recordAccess.requestedRecordCount,
            )

            result_dict['start_pos'] = apdu.accessMethod.recordAccess.fileStartRecord
            result_dict['record_data'] = record_data

            self._debug('   - record_data: %r', record_data)

            # create acknowledgement
            result_dict['resp'] = AtomicReadFileACK(
                context=apdu,
                endOfFile=end_of_file,
                accessMethod=AtomicReadFileACKAccessMethodChoice(
                    recordAccess=AtomicReadFileACKAccessMethodRecordAccess(
                        fileStartRecord=apdu.accessMethod.recordAccess.fileStartRecord,
                        returnedRecordCount=len(record_data),
                        fileRecordData=record_data,
                    ),
                ),
            )

    # return result dict
    return result_dict


def __do_AtomicStreamAccess(self, apdu, obj, write=False):
    """
    This function reads data from stream access and returns parsed data.

    :param apdu: incoming message
    :param obj: object
    :param write: specify if a read or write request is handed over
    :return: parsed data
    """
    result_dict = {}

    self._debug('__do_AtomicStreamAccess %r', apdu)

    # check if file access method is correct
    if obj.fileAccessMethod != 'streamAccess':
        raise ExecutionError(
            errorClass='services',
            errorCode='invalidFileAccessMethod',
        )

    # check if start record is correct
    elif not write and (apdu.accessMethod.streamAccess.fileStartPosition < 0 or
                        not hasattr(obj, '__len__') or
                        apdu.accessMethod.streamAccess.fileStartPosition >= len(obj)):
        raise ExecutionError(
            errorClass='services',
            errorCode='invalidFileStartPosition',
        )

    else:
        # read/write file
        if write:
            start_position = obj.WriteFile(
                apdu.accessMethod.streamAccess.fileStartPosition,
                apdu.accessMethod.streamAccess.fileData,
            )

            result_dict['start_pos'] = start_position
            result_dict['record_data'] = apdu.accessMethod.streamAccess.fileData

            self._debug('   - start_position: %r', start_position)

            # create acknowledgement
            result_dict['resp'] = AtomicWriteFileACK(
                context=apdu,
                fileStartPosition=start_position,
            )

        else:
            end_of_file, record_data = obj.ReadFile(
                apdu.accessMethod.streamAccess.fileStartPosition,
                apdu.accessMethod.streamAccess.requestedOctetCount,
            )

            result_dict['start_pos'] = apdu.accessMethod.streamAccess.fileStartPosition
            result_dict['record_data'] = record_data

            self._debug('   - record_data: %r', record_data)

            # create acknowledgement
            result_dict['resp'] = AtomicReadFileACK(
                context=apdu,
                endOfFile=end_of_file,
                accessMethod=AtomicReadFileACKAccessMethodChoice(
                    streamAccess=AtomicReadFileACKAccessMethodStreamAccess(
                        fileStartPosition=apdu.accessMethod.streamAccess.fileStartPosition,
                        fileData=record_data,
                    ),
                ),
            )

    # return result dict
    return result_dict


def __do_AtomicFileRequest(self, apdu, obj, write=False):
    """
    This function reads data from request and returns parsed data.

    :param apdu: incoming message
    :param obj: object
    :param write: specify if a read or write request is handed over
    :return: parsed data
    """
    result_dict = {}

    self._debug('__do_AtomicFileRequest %r', apdu)

    # check if object exists
    if obj is None:
        raise ExecutionError(errorClass='object', errorCode='unknownObject')

    # check if method is record access
    elif apdu.accessMethod.recordAccess:
        # initiate atomic record access
        result_dict.update(__do_AtomicRecordAccess(self, apdu, obj, write))

    # check if method is stream access
    elif apdu.accessMethod.streamAccess:
        # initiate atomic stream access
        result_dict.update(__do_AtomicStreamAccess(self, apdu, obj, write))

    # return result dict
    return result_dict


def do_AtomicReadFileRequest(self, apdu):
    """
    This function reads data from read file request.

    :param apdu: incoming message
    :return: response
    """
    self._debug('do_AtomicReadFileRequest %r', apdu)

    # check if file id is correct
    if apdu.fileIdentifier[0] != 'file':
        raise ExecutionError(errorClass='services', errorCode='inconsistentObjectType')

    # get object
    obj = self.get_object_by_id(apdu.fileIdentifier)

    self._debug('   - object: %r', obj)

    # initiate reading process
    result_dict = __do_AtomicFileRequest(self, apdu, obj, write=False)

    resp = result_dict['resp']

    # return response
    return resp


def do_AtomicWriteFileRequest(self, apdu):
    """
    This function reads data from write file request.

    :param apdu: incoming message
    :return: response
    """
    self._debug('do_AtomicWriteFileRequest %r', apdu)

    # check if file id is correct
    if apdu.fileIdentifier[0] != 'file':
        raise ExecutionError(errorClass='services', errorCode='inconsistentObjectType')

    # get object
    obj = self.get_object_by_id(apdu.fileIdentifier)

    self._debug('   - object: %r', obj)

    # initiate writing process
    result_dict = __do_AtomicFileRequest(self, apdu, obj, write=True)

    # set new size
    obj.WriteProperty('fileSize', len(obj), direct=True)

    resp = result_dict['resp']

    # return response
    return resp
