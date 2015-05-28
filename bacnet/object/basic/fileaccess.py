# pylint: disable=invalid-name, unused-variable, no-name-in-module

"""
File Access Object Module
-------------------------

This module contains File Access Objects.
"""

from __future__ import absolute_import

from multiprocessing import Lock

import os

from .general import register_object_type, FileObject

from bacnet.debugging import bacnet_debug, ModuleLogger

from bacnet.settings import DATA_PATH


# enable logging
ModuleLogger()


@bacnet_debug
@register_object_type
class RecordAccessFileObject(FileObject):
    """
    This class provides read/write access to file records.
    """

    def __init__(self, **kwargs):
        """
        This function initializes the instance.

        :return: None
        """

        self._debug('__init__ %r', kwargs)

        # call predecessor
        FileObject.__init__(self, fileAccessMethod='recordAccess', **kwargs)

        # fill record with example data
        self._record_data = []

    def __len__(self):
        """
        This function provides builtin length request.

        :return: length of record
        """

        self._debug('__len__')

        # return length
        return len(self._record_data)

    def ReadFile(self, start, count):
        """
        This function provides read access.

        :param start: start record
        :param count: record count
        :return: record data
        """

        self._debug('ReadFile %r %r', start, count)

        # check for end of file
        eof = start + count > len(self._record_data)

        # return end of file and record data
        return eof, self._record_data[start:start + count]

    def WriteFile(self, start, count, data):
        """
        This function provides write access.

        :param start: start record
        :param count: record count
        :param data: record data
        :return: start record
        """

        self._debug('WriteFile %r %r %r', start, count, data)

        # check if start record describes appending
        if start < 0:
            # set start to end of current record data
            start = len(self._record_data)

            # append new record data
            self._record_data.extend(data)

        # check if start describes additional extending
        elif start > len(self._record_data):
            # extend record data with empty data
            self._record_data.extend(['' for i in range(start - len(self._record_data))])

            # set start to end of extended record data
            start = len(self._record_data)

            # append new record data
            self._record_data.extend(data)

        # start describes slicing of current record data
        else:
            # check if new data overlaps
            if start + count > len(self._record_data):
                self._record_data.extend(
                    ['' for i in range(start + count - len(self._record_data))]
                )

            # write new record data into current record data
            self._record_data[start:start+count] = data

        # return new start record
        return start


@bacnet_debug
@register_object_type
class StreamAccessFileObject(FileObject):
    """
    This class provides read/write access to file streams.
    """

    def __init__(self, **kwargs):
        """
        This function initializes the instance.

        :return: None
        """

        self._debug('__init__ %r', kwargs)

        # call predecessor
        FileObject.__init__(self, fileAccessMethod='streamAccess', **kwargs)

        file_name = self.ReadProperty('objectName')
        file_name = getattr(file_name, 'value', str(file_name))

        file_type = self.ReadProperty('fileType')
        file_type = getattr(file_type, 'value', str(file_type))

        if file_type.lower() == 'text/x-python':
            file_name += '.py'

        # set file name
        self._file_name = os.path.join(DATA_PATH, file_name)

        # check if file exists
        if not os.path.exists(self._file_name):
            # touch file
            open(self._file_name, 'w').close()

        # unlock file
        self._file_lock = Lock()

    def get_filename(self):
        """
        This function returns the absolute path and file name.

        :return: file name
        """

        # return file name
        return self._file_name

    def lock_file(self):
        """
        This function locks the file.

        :return: None
        """

        # lock file
        self._file_lock.acquire()

    def unlock_file(self):
        """
        This function unlocks the file.

        :return: None
        """

        # unlock file
        self._file_lock.release()

    def __len__(self):
        """
        This function provides builtin length request.

        :return: length of stream
        """

        self._debug('__len__')

        # return length
        return os.path.getsize(self._file_name)

    def ReadFile(self, start, count):
        """
        This function provides read access.

        :param start: start position
        :param count: letter count
        :return: record data
        """

        self._debug('ReadFile %r %r', start, count)

        # check for end of file
        eof = start + count > len(self)

        # lock file
        self.lock_file()

        # open file
        file_pointer = open(self._file_name, 'r')

        # set start position
        file_pointer.seek(start)

        # check count
        if count == 0:
            eof = True
            # read characters
            result = file_pointer.read()

        elif count < 0:
            if start + count > 0:
                # read characters
                result = file_pointer.read(len(self) + count)

            else:
                # unable to read characters
                result = ''

        else:
            # read characters
            result = file_pointer.read(count)

        # close file
        file_pointer.close()

        # unlock file
        self.unlock_file()

        # return end of file and stream data
        return eof, result

    def WriteFile(self, start, data):
        # pylint: disable=bad-open-mode
        """
        This function provides write access.

        :param start: start position
        :param data: data
        :return: start position
        """

        self._debug('WriteFile %r %r', start, data)

        # lock file
        self.lock_file()

        # check if start position describes appending
        if start < 0:
            # set start to end of current stream data
            start = len(self)

            # lock file
            self.lock_file()

            # open file
            file_pointer = open(self._file_name, 'a')

            # write data
            file_pointer.write(data)

            # close file
            file_pointer.close()

        # check if start describes additional extending
        elif start > len(self):
            # open file
            file_pointer = open(self._file_name, 'a')

            # write empty data
            file_pointer.write('\0' * (start - len(self)))

            # write data
            file_pointer.write(data)

            # close file
            file_pointer.close()

        # start describes overriding of current stream data
        elif start == 0:
            # open file
            file_pointer = open(self._file_name, 'w')

            # write data
            file_pointer.write(data)

            # close file
            file_pointer.close()

        # start describes slicing of current stream data
        else:
            # open file
            file_pointer = open(self._file_name, 'r+w')

            # set start position
            file_pointer.seek(start)

            # read last chunk
            chunk = file_pointer.read()

            # set start position again
            file_pointer.seek(start)

            # write data
            file_pointer.write(data)

            # write last chunk
            file_pointer.write(chunk)

            # close file
            file_pointer.close()

        # unlock file
        self.unlock_file()

        # return new start record
        return start
