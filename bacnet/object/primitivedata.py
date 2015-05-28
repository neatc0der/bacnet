# pylint: disable=invalid-name, too-few-public-methods, star-args

"""
Primitive Data Module
---------------------

This module contains improved bacpypes primitive data classes.
"""

from __future__ import absolute_import

from collections import OrderedDict
from datetime import datetime, timedelta
import dateutil.parser
import struct

from bacpypes import primitivedata, constructeddata, basetypes


class RingList(list):
    """
    This class is a ring buffer without overriding protection.
    """

    def __init__(self, size, seq=()):
        """
        This function initializes the ring buffer with size.

        :param size: number of entries
        :return: None
        """

        list.__init__(self, seq)

        self.extend(size * [None])
        self.__size = size
        self.__pos = 0

    @property
    def size(self):
        """
        This function returns the size of the ring buffer.

        :return: buffer size
        """

        return self.__size

    def append(self, data):
        """
        This function adds data to ring buffer.

        :param data: data to be added
        :return: None
        """

        self[self.__pos] = data
        self.__pos = (self.__pos + 1) % self.__size

    def first_value(self):
        """
        This function returns the value last appended.

        :return: last value
        """

        return self[(self.__pos + 1) % self.__size]

    def last_value(self):
        """
        This function returns the value last appended.

        :return: last value
        """

        return self[(self.__pos + self.__size - 1) % self.__size]


class RingDict(OrderedDict):
    """
    This class is a dictionary ring buffer without overriding protection.
    """

    def __init__(self, size, *args, **kwargs):
        """
        This function initializes the ring buffer with size.

        :param size: number of entries
        :return: None
        """

        self.__size = size
        self.__pos = 0

        OrderedDict.__init__(self, *args, **kwargs)

    @property
    def size(self):
        """
        This function returns the size of the ring buffer.

        :return: buffer size
        """

        return self.__size

    def __delitem__(self, key, **kwargs):
        """
        This function sets the specified item for key.

        :param key: key
        :param value: value
        """

        # check if key is in dictionary already
        if key in self:
            self.__pos -= 1

        return OrderedDict.__delitem__(self, key, **kwargs)

    def __setitem__(self, key, value, **kwargs):
        """
        This function sets the specified item for key.

        :param key: key
        :param value: value
        """

        # check if key is in dictionary already
        if not key in self:
            if self.__pos >= self.__size:
                # remove key from dictionary
                self.__delattr__(self.__root[0][-1])

            self.__pos += 1

        return OrderedDict.__setitem__(self, key, value, **kwargs)


class Unsigned(primitivedata.Unsigned, long):
    # pylint: disable=super-init-not-called
    """
    This class has an integer extension to support builtin functions like div float.
    """

    def __new__(cls, value, *args, **kwargs):
        """
        This function creates the object.

        :return: instance
        """

        # check if value is a Tag
        if isinstance(value, primitivedata.Tag):
            # make Tag to long-readable number
            value = primitivedata.Unsigned(value).value

        # check if value is an Array
        elif isinstance(value, constructeddata.Array):
            # get length of array
            value = len(value)

        # return created instance
        return long.__new__(cls, value, *args, **kwargs)

    def __init__(self, *args):
        """
        This function initializes the object.

        :return: None
        """

        # check if value was provided
        if len(args) > 0:
            # get value
            value = args[0]

            # check if value is an Array
            if isinstance(value, constructeddata.Array):
                # get length of array
                value = len(value)

            # call predecessor
            primitivedata.Unsigned.__init__(self, value, *args[1:])

        else:
            # call predecessor
            primitivedata.Unsigned.__init__(self, *args)


class Remaining(primitivedata.CharacterString):
    """
    This class is an extended version of Unsigned.
    """

    _app_tag = primitivedata.Tag.unsignedAppTag

    def __init__(self, time):
        """
        This function initializes the object

        :return: None
        """

        # check if time is Remaining
        if isinstance(time, Remaining):
            time = time.value

        # check if time is Tag
        elif isinstance(time, primitivedata.Tag):
            time = self.decode(time)

        # check if time is int
        if isinstance(time, (primitivedata.Unsigned, int, long)):
            time = datetime.utcnow() + timedelta(seconds=time)

        if isinstance(time, datetime):
            # convert time to iso format
            time = time.isoformat()

        # call predecessor
        primitivedata.CharacterString.__init__(self, time)

    @property
    def remaining_time(self):
        """
        This function calculates the remaining time till defined datetime

        :return: remaining time in seconds
        """

        # parse time
        time = dateutil.parser.parse(self.value)

        # get remaining time
        remaining = int((time - datetime.utcnow()).total_seconds())

        # check if remaining is smaller than zero
        if remaining < 0:
            remaining = 0

        # return remaining time
        return remaining

    def encode(self, tag):
        """
        This function encodes the value for network transmission.

        :param tag: Tag
        :return: None
        """

        # rip apart the number
        data = [ord(c) for c in struct.pack('>L', self.remaining_time)]

        # reduce the value to the smallest number of octets
        while len(data) > 1 and data[0] == 0:
            del data[0]

        # encode the tag
        tag.set_app_data(primitivedata.Tag.unsignedAppTag, ''.join(chr(c) for c in data))

    def decode(self, tag):
        """
        This function decodes the value from network transmission.

        :param tag: Tag
        :return: None
        """

        # check if tag is appropriate
        if tag.tagClass != primitivedata.Tag.applicationTagClass or \
            tag.tagNumber != primitivedata.Tag.unsignedAppTag:
            raise ValueError('unsigned application tag required')

        # get data
        result = 0L
        for c in tag.tagData:
            result = (result << 8) + ord(c)

        # return result
        return result


class ObjectPropertyReference(constructeddata.Sequence):
    """
    This class has an extension to support instances without property identifier.
    """
    sequenceElements = [
        constructeddata.Element('objectIdentifier', primitivedata.ObjectIdentifier, 0),
        constructeddata.Element('propertyIdentifier', basetypes.PropertyIdentifier, 1, True),
        constructeddata.Element('propertyArrayIndex', Unsigned, 2, True),
    ]


class COVSubscription(basetypes.COVSubscription):
    """
    This class has specific updates.
    """
    sequenceElements = [
        constructeddata.Element('recipient', basetypes.RecipientProcess, 0),
        constructeddata.Element('monitoredPropertyReference', ObjectPropertyReference, 1),
        constructeddata.Element('issueConfirmedNotifications', primitivedata.Boolean, 2),
        constructeddata.Element('timeRemaining', Remaining, 3),
        constructeddata.Element('covIncrement', primitivedata.Real, 4, True),
    ]

SequenceOfCOVSubscription = constructeddata.SequenceOf(COVSubscription)
