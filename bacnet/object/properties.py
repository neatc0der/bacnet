# pylint: disable=invalid-name, too-many-branches, too-many-arguments, too-few-public-methods

"""
Object Properties Module
------------------------

This module contains specific properties for the usage within objects.
Especially it provides updated property COV functionality for bacpypes objects.
"""

from __future__ import absolute_import

from collections import Iterable
from datetime import datetime
from threading import Lock
import types

from bacpypes.errors import ConfigurationError, ExecutionError

from bacpypes.primitivedata import Atomic, CharacterString, Real, Unsigned, Time, Date
from bacpypes.basetypes import BinaryPV
from bacpypes.constructeddata import Array

from bacpypes.object import PropertyIdentifier

from bacnet.object.primitivedata import RingList, SequenceOfCOVSubscription

from bacnet.debugging import bacnet_debug, ModuleLogger


# enable logging
ModuleLogger(level='INFO')


@bacnet_debug
class HardwareAccessObject(object):
    """
    This class is a wrapper for terra hardware objects.
    """

    hardware = None
    writable = False

    def __init__(self, hw_object, write=False, hysteresis=False, buffer_size=0):
        """
        This function is a constructor for the wrapper of a hardware objects.

        :param hw_object: hardware object
        :return:
        """

        # set hardware object
        self.hardware = hw_object

        # set writable property
        self.writable = write

        if buffer_size:
            # set buffer
            self.buffer = RingList(buffer_size)

        if hysteresis:
            # set hysteresis usage
            self.hysteresis_func = hysteresis

    def __repr__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return u'<%s.%s of %r>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.hardware,
        )

    def __str__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()

    def __unicode__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()

    def hysteresis(self, value):
        """
        This function applies a user specific hysteresis to the value.

        :param value: hardware value
        :return: updated value
        """

        # call user specific function
        return getattr(self, 'hysteresis_func', lambda s, v: v)(self, value)

    def get(self, index=None):
        """
        This function is a wrapper for getting the actual hardware value

        :param index: array index
        :return: value
        """

        # get hardware
        hardware = self.hardware

        # get hardware by index
        if index is not None and isinstance(hardware, Iterable):
            hardware = hardware[index]

        # initialize value
        value = None

        # check if hardware has get-function
        if hasattr(hardware, 'get'):
            # read hardware value
            value = hardware.get()

            # apply hysteresis
            value = self.hysteresis(value)

        # return value
        return value

    def set(self, value, data_type, index=None):
        # pylint: disable=too-many-function-args
        """
        This function converts the

        :param value: value
        :param data_type: data type
        :param index: array index
        :return: value
        """

        # check if hardware is writable
        if not self.writable:
            # exit
            return value

        return_values = []

        # get hardware
        hardware = self.hardware

        # get hardware by index
        if index is not None and isinstance(hardware, Iterable):
            hardware = hardware[index]

        #check if hardware is an iterable
        if isinstance(hardware, (Array, Iterable)):

            # loop through hardware objects
            for i in range(len(hardware)):

                # check if value is an array
                if isinstance(value, Array):
                    # call function for each object
                    return_values.append(self.set(value[i], data_type.subtype, i))

                else:
                    # call function for each object
                    return_values.append(self.set(value, data_type.subtype, i))

            # return value list
            return return_values

        # check if data type is binary
        elif issubclass(data_type, BinaryPV):

            # check if hardware should be turned on or off
            if getattr(value, 'value', value) == 'active':
                hardware.on()

            else:
                hardware.off()

        # check if data type is string
        elif issubclass(data_type, CharacterString):

            # check if hardware has write function
            if hasattr(hardware, 'write'):
                value = hardware.write(getattr(value, 'value', value))
            else:
                self._error('unable to write to hardware %r' % hardware)

        # check if data type is real
        # elif isinstance(value, Real):
        #     pass

        # check if value is array size
        elif isinstance(value, int):
            pass

        else:
            self._error(
                'unable to set value "%s" (%s) on hardware %r' %
                (value, type(value), hardware)
            )

            # exit
            return value

        # return value
        return value


@bacnet_debug
class Property(object):
    """
    This class is an extension of the bacpypes Property class to support COV notifications.
    """

    def __init__(self, identifier, datatype, **kwargs):
        """
        This function initializes the property.

        :return: None
        """

        self._debug('__init__ %s, %s, %s', identifier, datatype, kwargs)

        # read identifier and data type
        self.identifier = identifier
        self.datatype = datatype

        # read default, optional and mutable
        self.default = kwargs.get('default', None)
        self.optional = kwargs.get('optional', False)
        self.mutable = kwargs.get('mutable', False)

        # get cov support
        self.cov_support = kwargs.get('cov_support', False)

        # get hardware
        self.hardware = kwargs.get('hardware', False)

    def __repr__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return u'<%s.%s %r>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.identifier,
        )

    def __str__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()

    def __unicode__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        """
        This function handles writing.

        :param obj: property
        :param value: property value
        :param arrayIndex: index
        :param priority: priority
        :param direct: direct
        :return: property value
        """

        self._debug(
            'WriteProperty(%s) %s %r arrayIndex=%r priority=%r direct=%r',
            self.identifier,
            obj,
            value,
            arrayIndex,
            priority,
            direct,
        )

        if not direct:
            # check if property must be provided
            if not self.optional and value is None:
                raise ValueError('%s value required' % self.identifier)

            # check if writing is allowed
            if not self.mutable:
                raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')

        # initialize value
        if value is None:
            if issubclass(self.datatype, CharacterString):
                value = ''
            if issubclass(self.datatype, (Real, Unsigned)):
                value = 0

        # check if data type is correct
        if issubclass(self.datatype, Atomic):
            # inform hardware
            if self.identifier == 'presentValue' and obj._hardware is not None:
                value = obj._hardware.set(value, self.datatype)

            # cast to correct data type if needed
            if not isinstance(value, self.datatype) and value is not None:
                value = self.datatype(value)

            self._debug('   - property is atomic, assumed correct type')

        elif isinstance(value, self.datatype):
            # inform hardware
            if self.identifier == 'presentValue' and obj._hardware is not None:
                value = obj._hardware.set(value, self.datatype)

            self._debug('   - correct type')

        # check if property index is set
        elif arrayIndex is not None:
            # check if data type is array
            if not issubclass(self.datatype, Array):
                raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')

            # read values
            values = obj.get_value(self.identifier)

            # check if values exist
            if values is None:
                raise RuntimeError('%s uninitialized array' % self.identifier)

            # check if array index is valid
            if not 0 <= arrayIndex <= len(value):
                raise ExecutionError(errorClass='property', errorCode='invalidArrayIndex')

            self._debug('   - forwarding to array')

            # inform hardware
            if arrayIndex > 0 and self.identifier == 'presentValue' and obj._hardware is not None:
                value = obj._hardware.set(value, self.datatype)

            # set value
            values[arrayIndex] = value

            # return value
            return value

        # check if value is set
        elif value is not None:

            # cast value
            value = self.datatype(value)

            # inform hardware
            if obj._hardware is not None:
                value = obj._hardware.set(value, self.datatype)

            self._debug('   - coerced the value: %r', value)

        # set value
        obj.set_value(self.identifier, value)

        # return value
        return value

    def ReadProperty(self, obj, arrayIndex=None):
        """
        This function handles reading.

        :param obj: property
        :param arrayIndex: index
        :return: property value
        """

        self._debug(
            'ReadProperty(%s) %s arrayIndex=%r',
            self.identifier,
            obj,
            arrayIndex,
        )

        # read value
        value = obj.get_value(self.identifier)

        # check if property index is set
        if arrayIndex is not None:
            # check if data type is array
            if not issubclass(self.datatype, Array):
                raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')

            if value is None:
                obj.set_value(self.identifier, self.datatype())
                value = obj.get_value(self.identifier)

            # check if array index is valid
            if not 0 <= arrayIndex <= len(value):
                raise ExecutionError(errorClass='property', errorCode='invalidArrayIndex')

            # check if value is valid
            if value:
                # set value
                value = value[arrayIndex]

        # return value
        return value


class StandardProperty(Property):
    """
    This class is an extension of the bacpypes StandardProperty class to support COV notifications.
    """

    def __init__(self, *args, **kwargs):
        """
        This function initializes the property.

        :return: None
        """

        # check if subclass is valid
        if not isinstance(self, (OptionalProperty, ReadableProperty, WritableProperty)):
            raise ConfigurationError(
                '%s must derive from OptionalProperty, ReadableProperty, or WritableProperty' %
                self.__class__.__name__
            )

        # read identifier
        identifier = args[0]

        # check if identifier is valid
        if identifier not in PropertyIdentifier.enumerations:
            raise ConfigurationError('unknown standard property identifier: %s' % identifier)

        # call predecessor
        Property.__init__(self, *args, **kwargs)


class OptionalProperty(StandardProperty):
    """
    This class is an extension of the bacpypes OptionalProperty class to support COV notifications.
    """

    def __init__(self, identifier, datatype,
                 default=None, optional=True, mutable=False, cov_support=False):
        """
        This function initializes the property.

        :return: None
        """

        # call predecessor
        StandardProperty.__init__(
            self,
            identifier,
            datatype,
            default=default,
            optional=optional,
            mutable=mutable,
            cov_support=cov_support,
        )


class ReadableProperty(StandardProperty):
    """
    This class is an extension of the bacpypes ReadableProperty class to support COV notifications.
    """

    def __init__(self, identifier, datatype,
                 default=None, optional=False, mutable=False, cov_support=False):
        """
        This function initializes the property.

        :return: None
        """

        # call predecessor
        StandardProperty.__init__(
            self,
            identifier,
            datatype,
            default=default,
            optional=optional,
            mutable=mutable,
            cov_support=cov_support,
        )


@bacnet_debug
class WritableProperty(StandardProperty):
    """
    This class is an extension of the bacpypes WritableProperty class to support COV notifications.
    """

    def __init__(self, identifier, datatype,
                 default=None, optional=False, mutable=True, cov_support=False):
        """
        This function initializes the property.

        :return: None
        """

        # call predecessor
        StandardProperty.__init__(
            self,
            identifier,
            datatype,
            default=default,
            optional=optional,
            mutable=mutable,
            cov_support=cov_support,
        )


@bacnet_debug
class ObjectIdentifierProperty(ReadableProperty):
    """
    This class is an extension of the ReadableProperty class for object identifiers.
    """

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        """
        This function handles writing.

        :param obj: property
        :param value: property value
        :param arrayIndex: index
        :param priority: priority
        :param direct: direct
        :return: property value
        """

        self._debug(
            'WriteProperty %r %r arrayIndex=%r priority=%r',
            obj,
            value,
            arrayIndex,
            priority
        )

        # check if value was provided
        if value is None:
            pass

        # check if value is valid
        elif isinstance(value, (types.IntType, types.LongType)):
            value = (obj.objectType, value)

        # check if object type within value is correct
        elif isinstance(value, types.TupleType) and len(value) == 2:
            if value[0] != obj.objectType:
                raise ValueError('%s required' % obj.objectType)

        else:
            raise TypeError('object identifier invalid')

        # perform actual write procedure
        return ReadableProperty.WriteProperty(self, obj, value, arrayIndex, priority, direct)


class CurrentDateProperty(OptionalProperty):
    """
    This class is an extension of the OptionalProperty class for current date.
    """

    def __init__(self, identifier):
        """
        This function initializes the property.

        :return: None
        """

        OptionalProperty.__init__(self, identifier, Date)

    def ReadProperty(self, obj, arrayIndex=None):
        """
        This function handles reading.

        :param obj: property
        :param arrayIndex: index
        :return: property value
        """

        # access an array
        if arrayIndex is not None:
            raise TypeError('%s is not an array' % self.identifier)

        # get utc now
        utcnow = datetime.utcnow()

        # get current date
        now = Date(
            year=utcnow.year - 1900,
            month=utcnow.month,
            day=utcnow.day,
            dayOfWeek=utcnow.weekday() + 1
        )

        # return value
        return now.value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        """
        This function handles writing.

        :param obj: property
        :param value: property value
        :param arrayIndex: index
        :param priority: priority
        :param direct: direct
        :return: property value
        """

        raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')


class CurrentTimeProperty(OptionalProperty):
    """
    This class is an extension of the OptionalProperty class for current time.
    """

    def __init__(self, identifier):
        """
        This function initializes the property.

        :return: None
        """

        OptionalProperty.__init__(self, identifier, Time)

    def ReadProperty(self, obj, arrayIndex=None):
        """
        This function handles reading.

        :param obj: property
        :param arrayIndex: index
        :return: property value
        """

        # check if array index was provided
        if arrayIndex is not None:
            raise TypeError('%s is not an array' % self.identifier)

        # get utc now
        utcnow = datetime.utcnow()

        # get current time
        now = Time(
            hour=utcnow.hour,
            minute=utcnow.minute,
            second=utcnow.second,
            hundredth=utcnow.microsecond /  10000
        )

        # return value
        return now.value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        """
        This function handles writing.

        :param obj: property
        :param value: property value
        :param arrayIndex: index
        :param priority: priority
        :param direct: direct
        :return: property value
        """

        raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')


@bacnet_debug
class ActiveCovSubscriptionsProperty(ReadableProperty):
    # pylint: disable=arguments-differ
    """
    This class is an extension of the ReadableProperty class for active cov subscriptions.
    """

    def __init__(self, *args, **kwargs):
        """
        This function initializes the property.

        :return: None
        """

        # add lock to property
        self.lock = Lock()

        # call predecessor
        ReadableProperty.__init__(self, *args, **kwargs)

    def ReadProperty(self, obj, arrayIndex=None, dictionary=False):
        """
        This function handles reading.

        :param obj: property
        :param arrayIndex: index
        :return: property value
        """

        # get result
        result = ReadableProperty.ReadProperty(self, obj, arrayIndex)

        # check if return value should be a dictionary
        if not dictionary:

            removables = []

            # get new instance
            new_result = SequenceOfCOVSubscription()

            # loop through all subscriptions
            for subscriptions in result.itervalues():
                for subscription in subscriptions:
                    # check if remaining life time is 0
                    if subscription.timeRemaining.remaining_time == 0:
                        # add subscription to remove list
                        removables.append(subscription)
                    else:
                        # add subscription to read result
                        new_result.append(subscription)

            # check if removables were found
            if any(removables):
                # remove results
                obj._application.delete_cov_subscriptions(removables)

            result = new_result

        # return result
        return result

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        """
        This function handles writing.

        :param obj: property
        :param value: property value
        :param arrayIndex: index
        :param priority: priority
        :param direct: direct
        :return: property value
        """

        self._debug(
            'WriteProperty(%s) %s %r arrayIndex=%r priority=%r direct=%r',
            self.identifier,
            obj,
            value,
            arrayIndex,
            priority,
            direct,
        )

        # initialize value
        if value is None:
            if issubclass(self.datatype, CharacterString):
                value = ''
            if issubclass(self.datatype, (Real, Unsigned)):
                value = 0

        if not direct:
            # check if property must be provided
            if not self.optional and value is None:
                raise ValueError('%s value required' % self.identifier)

            # check if writing is allowed
            if not self.mutable:
                raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')

        # check if property was locked before writing
        if self.lock.acquire(False):
            # release lock
            self.lock.release()

            if value:
                self._warning('not locked before writing directly')

        # check if value is dictionary
        if not isinstance(value, dict):
            self._warning('value is not a dictionary')

        # set value
        obj.set_value(self.identifier, value)

        # return value
        return value
