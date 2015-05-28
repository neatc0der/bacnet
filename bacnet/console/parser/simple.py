# pylint: disable=too-many-branches, too-many-locals, broad-except

"""
Simple Parser Module
--------------------

This module contains rudimentary parser functions.
"""

from __future__ import absolute_import

from bacpypes.primitivedata import Date, Time, Boolean, CharacterString
from bacpypes.constructeddata import Array
from bacpypes.basetypes import ErrorType, PropertyIdentifier, DateTime, TimeStamp, AddressBinding

from bacpypes.apdu import ReadPropertyMultipleACK, ReadPropertyACK

from bacnet.debugging import bacnet_debug, ModuleLogger

from bacnet.object import get_datatype, ObjectIdentifier
from bacnet.object.primitivedata import Unsigned


# enable logging
ModuleLogger()


def __date_to_str(val):
    """
    convert Date to str

    :param val: tuple
    :return: date string
    """

    weekday = ('Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag')

    return '%s, %02i.%02i.%4i' % (weekday[val[3] - 1], val[2], val[1], val[0] + 1900)


def __time_to_str(val):
    """
    convert Time to str

    :param val: tuple
    :return: time string
    """

    return '%02i:%02i:%02.2f Uhr' % (val[0], val[1], val[2] + float(val[3]) / 100)


def __datetime_to_str(val):
    """
    convert DateTime to str

    :param val: tuple
    :return: (date string, time string)
    """

    return (__date_to_str(val.date.value), __time_to_str(val.time.value))


@bacnet_debug
def __convert_value(value, obj_type=None, prop_id=None, datatype=None):
    """
    This function converts value into a human readable value.

    :param value: value
    :return: human readable value
    """

    self = __convert_value

    # check if data type was defined
    if datatype is not None:
        data_type = datatype

    else:
        # get data type
        data_type = get_datatype(obj_type, prop_id)

    if issubclass(data_type, Array):
        data_type = getattr(data_type, 'subtype', data_type)

    # check if value is error
    if isinstance(value, ErrorType):
        value = '(error) %s: %s' % (value.errorClass, value.errorCode)

    # check if value is character string
    elif isinstance(value, CharacterString):
        value = value.strValue

    # check if value is object identifier
    elif isinstance(value, ObjectIdentifier):
        value = value.value

    # check if value is date time
    elif issubclass(data_type, DateTime):
        if isinstance(value, data_type):
            value = __datetime_to_str(value)

    # check if value is date
    elif issubclass(data_type, Date):
        if isinstance(value, data_type):
            value = value.value
        if not isinstance(value, basestring):
            value = __date_to_str(value)

    # check if value is time
    elif issubclass(data_type, Time):
        if isinstance(value, data_type):
            value = value.value
        if not isinstance(value, basestring):
            value = __time_to_str(value)

    # check if value is time stamp
    elif issubclass(data_type, TimeStamp):
        if isinstance(value, TimeStamp):
            value = (
                __time_to_str(value.time.value),
                int(value.sequenceNumber),
                __datetime_to_str(value.dateTime)
            )

    # check if value is boolean
    elif issubclass(data_type, Boolean):
        value = bool(value)

    # check if value is address binding
    elif issubclass(data_type, AddressBinding):
        if isinstance(value, data_type):
            value = (
                value.deviceObjectIdentifier.value,
                (
                    value.deviceAddress.networkNumber.value,
                    value.deviceAddress.macAddress.value,
                ),
            )

    # check if value is sequence of another class
    elif data_type.__name__.startswith('SequenceOf'):
        value = tuple(__convert_value(val, datatype=data_type.subtype) for val in value)

    # check if value is instance of its own data type
    elif not isinstance(value, data_type) and not data_type in (ObjectIdentifier,
                                                                PropertyIdentifier):
        # cast value
        try:
            value = data_type(value)

        except Exception as error:
            self._error(value)
            self._error(data_type)
            self._error(error)

    # return converted value
    return value


def __read_ack(apdu):
    """
    This function parses read property (multiple) acknowledgements.

    :param apdu: ReadPropertyMultipleACK or ReadPropertyACK
    :returns: parsed data, output
    """

    result = {}

    # check if ack is read property
    if isinstance(apdu, ReadPropertyACK):
        # get object identifier
        obj_id = getattr(apdu.objectIdentifier, 'value', apdu.objectIdentifier)

        # check if array length was defined
        if apdu.propertyArrayIndex == 0:
            # cast to unsigned integer
            value = apdu.propertyValue.cast_out(Unsigned)

        else:
            # cast to proper data type
            value = apdu.propertyValue.cast_out(
                get_datatype(
                    obj_id[0],
                    apdu.propertyIdentifier,
                ),
            )

        value = getattr(value, 'value', value)

        # set result dictionary for object and priority identifier
        result[obj_id[0]] = {
            obj_id[1]: {
                apdu.propertyIdentifier: {
                    apdu.propertyArrayIndex: value,
                }
            },
        }

    # check if ack is read property multiple
    elif isinstance(apdu, ReadPropertyMultipleACK):
        # loop through objects
        for obj_access in apdu.listOfReadAccessResults:
            # initialize type and object dictionary
            type_dict = result.get(obj_access.objectIdentifier[0], {})
            obj_dict = type_dict.get(obj_access.objectIdentifier[1], {})

            # loop through properties
            for prop_access in obj_access.listOfResults:
                # initialize property dictionary
                property_dict = obj_dict.get(prop_access.propertyIdentifier, {})

                # check if property had access error
                if prop_access.readResult.propertyAccessError is not None:
                    value = prop_access.readResult.propertyAccessError

                # check if array length was defined
                elif prop_access.propertyArrayIndex == 0:
                    # cast to unsigned integer
                    value = prop_access.readResult.propertyValue.cast_out(Unsigned)

                else:
                    # get data type
                    data_type = get_datatype(
                        obj_access.objectIdentifier[0],
                        prop_access.propertyIdentifier,
                    )

                    # check if data_type is array
                    if issubclass(data_type, Array):
                        data_type = data_type.subtype

                    # cast to proper data type
                    try:
                        value = prop_access.readResult.propertyValue.cast_out(
                            data_type,
                        )

                        if issubclass(data_type, Date):
                            value = __date_to_str(value)

                        elif issubclass(data_type, Time):
                            value = __time_to_str(value)

                    except Exception:
                        value = None

                # update property dictionary for property array index
                property_dict[prop_access.propertyArrayIndex] = value

                # update object dictionary for property identifier
                obj_dict[prop_access.propertyIdentifier] = property_dict

            # update type dictionary for object identifier
            type_dict[obj_access.objectIdentifier[1]] = obj_dict

            # update result dictionary for type identifier
            result[obj_access.objectIdentifier[0]] = type_dict

    # unsupported ack type
    else:
        # create error message
        raise RuntimeError('Unsupported ACK: %s' % apdu.__class__.__name__)


    # initialize output
    output = 'read response:'

    # loop through object types
    for obj_type in result.iterkeys():
        # loop through object instances
        for obj_inst in result[obj_type].iterkeys():
            # loop through property identifiers
            for prop_id, value in result[obj_type][obj_inst].iteritems():
                # create prefix
                prefix = '(%s, %s): %s' % (obj_type, obj_inst, prop_id)

                # check if property is array
                if None in value:
                    # check if value must be converted
                    index_value = __convert_value(value[None], obj_type, prop_id)

                    # add values to output
                    output += '\n    %s = %s' % (prefix, index_value)

                else:

                    # loop through property array index
                    for prop_index, index_value in value.iteritems():
                        # check if value must be converted
                        index_value = __convert_value(index_value, obj_type, prop_id)

                        # add values to output
                        output += '\n    %s [%s] = %s' % (prefix, prop_index, index_value)

    # return parsed data, output
    return result, output


def read_property_ack(apdu):
    """
    This function parses read property acknowledgements.

    :param apdu: ReadPropertyACK
    :returns: parsed data, output
    """

    # get parsed data
    result = __read_ack(apdu)

    # return parsed data, output
    return result


def read_property_multiple_ack(apdu):
    """
    This function parses read property multiple acknowledgements.

    :param apdu: ReadPropertyMultipleACK
    :returns: parsed data, output
    """

    # get parsed data
    result = __read_ack(apdu)

    # return parsed data, output
    return result


def whois_request(apdu):
    """
    This function parses who is requests.

    :param apdu: WhoIsRequest
    :returns: parsed data, output
    """

    # initialize result
    result = {
        'limits': (),
    }

    # check if limits were defined
    if hasattr(apdu, 'deviceInstanceRangeLowLimit') and \
            apdu.deviceInstanceRangeLowLimit is not None and \
            apdu.deviceInstanceRangeHighLimit is not None:
        # set limits
        result['limits'] = (apdu.deviceInstanceRangeLowLimit, apdu.deviceInstanceRangeHighLimit)

    # initialize output
    output = 'who is around?'

    # check if limits were defined
    if any(result['limits']):
        # add values to output
        output += ' (range: %i - %i)' % result['limits']

    # return parsed data, output
    return result, output


def iam_request(apdu):
    """
    This function parses i am requests.

    :param apdu: IAmRequest
    :returns: parsed data, output
    """

    # read device identifier
    result = {
        'id': apdu.iAmDeviceIdentifier,
    }

    # initialize output
    output = 'i am "%s %i"!' % result['id']

    # return parsed data, output
    return result, output


def whohas_request(apdu):
    """
    This function parses who has requests.

    :param apdu: WhoHasRequest
    :returns: parsed data, output
    """

    # initialize result
    result = {
        'limits': (),
        'has': None,
    }

    # check if limits were defined
    if hasattr(apdu, 'deviceInstanceRangeLowLimit') and \
            apdu.deviceInstanceRangeLowLimit is not None and \
            apdu.deviceInstanceRangeHighLimit is not None:
        # set limits
        result['limits'] = (apdu.deviceInstanceRangeLowLimit, apdu.deviceInstanceRangeHighLimit)

    # check if object identifier was supplied
    if apdu.object.objectIdentifier is not None:
        # set has object properties
        result['has'] = 'identifier'
        result['identifier'] = apdu.object.objectIdentifier

    # check if object name was supplied
    elif apdu.object.objectName is not None:
        # set has object properties
        result['has'] = 'name'
        result['name'] = apdu.object.objectName


    # check if who has requested property was defined
    if result['has'] is None:
        # initialize output
        output = 'who has ... malformed'

    else:
        # initialize output
        output = 'who has object %s "%s"?' % (result['has'], result[result['has']])

        # check if limits were defined
        if any(result['limits']):
            # add values to output
            output += ' (range: %i - %i)' % result['limits']

    # return parsed data, output
    return result, output


def ihave_request(apdu):
    """
    This function parses i have requests.

    :param apdu: IHaveRequest
    :returns: parsed data, output
    """

    # read object identifier and name
    result = {
        'device': getattr(apdu.deviceIdentifier, 'value', apdu.deviceIdentifier),
        'id': getattr(apdu.objectIdentifier, 'value', apdu.deviceIdentifier),
        'name': getattr(apdu.objectName, 'value', apdu.objectName),
    }

    # initialize output
    output = 'i have "%s" as %s!' % (result['name'], result['id'])

    # return parsed data, output
    return result, output
