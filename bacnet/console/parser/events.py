# pylint: disable=invalid-name

"""
Event Parser Module
-------------------------

This module provides event parsers.
"""

from bacpypes.apdu import ConfirmedCOVNotificationRequest

from bacpypes.primitivedata import ObjectIdentifier

from bacnet.object import get_datatype
from bacnet.object.primitivedata import Unsigned, Remaining


def __subscribe_cov(apdu):
    """
    This function parses subscribe cov request.

    :param apdu: SubscribeCOVRequest or SubscribeCOVPropertyRequest
    :returns: parsed data, output
    """

    # initialize result
    result = {
        'object': apdu.monitoredObjectIdentifier,
        'process_id': apdu.subscriberProcessIdentifier,
        'remaining': Remaining(apdu.lifetime),
        'confirmed': bool(apdu.issueConfirmedNotifications),
        'cov_increment': None,
        'property': None,
        'index': None,
    }

    confirmed = 'confirmed' if result['confirmed'] else 'unconfirmed'

    # check if cov increment was defined
    if hasattr(apdu, 'covIncrement'):
        # read cov increment
        result['cov_increment'] = apdu.covIncrement

    # initialize property
    prop = ''

    # create renew request
    result['renew'] = '%i %s %s %s' % (
        apdu.lifetime if apdu.lifetime > 0 else 1800,
        str(result['confirmed']).lower(),
        result['object'][0],
        result['object'][1],
    )

    # check if property identifier was provided
    if hasattr(apdu, 'monitoredPropertyIdentifier'):
        # read property
        result['property'] = prop = apdu.monitoredPropertyIdentifier.propertyIdentifier
        result['renew'] += ' ' + result['property'] + ' '
        result['renew'] += str(result['cov_increment']) if result['cov_increment'] is not None \
                           else '0'

        # check if property array index was defined
        if apdu.monitoredPropertyIdentifier.propertyArrayIndex:
            # read property array index
            result['index'] = apdu.monitoredPropertyIdentifier.propertyArrayIndex
            prop += ', ' + result['index']
            result['renew'] += ' ' + result['index']

        prop = ' (%s)' % prop

    if apdu.lifetime > 0:
        # initialize output
        output = 'add/renew %s subscription for object "%s %i"%s for %i seconds' % (
            confirmed,
            apdu.monitoredObjectIdentifier[0],
            apdu.monitoredObjectIdentifier[1],
            prop,
            apdu.lifetime,
        )

    else:
        # initialize output
        output = 'remove subscription for object "%s %i"%s' % (
            apdu.monitoredObjectIdentifier[0],
            apdu.monitoredObjectIdentifier[1],
            prop,
        )

    # return parsed data, output
    return result, output


def subscribe_cov_request(apdu):
    """
    This function parses subscribe cov request.

    :param apdu: SubscribeCOVRequest
    :returns: parsed data, output
    """

    # get parsed data
    result = __subscribe_cov(apdu)

    # return parsed data, output
    return result


def subscribe_cov_property_request(apdu):
    """
    This function parses subscribe cov property request.

    :param apdu: SubscribeCOVPropertyRequest
    :returns: parsed data, output
    """

    # get parsed data
    result = __subscribe_cov(apdu)

    # return parsed data, output
    return result


def __cov_notification(apdu):
    """
    This function parses cov notification request.

    :param apdu: ConfirmedCOVNotificationRequest
    :returns: parsed data, output
    """

    # initialize result
    result = {
        'confirmed': isinstance(apdu, ConfirmedCOVNotificationRequest),
        'object': ObjectIdentifier(apdu.monitoredObjectIdentifier).value,
    }

    # get device id
    device_id = apdu.initiatingDeviceIdentifier

    # initialize output
    output = 'COV for object "%s %i" on %s' %  (result['object'] + (device_id,))

    prop_values = {}

    # loop through properties
    for prop_value in apdu.listOfValues:
        # get print result
        prop = prop_value.propertyIdentifier

        # check if property has array index
        if prop_value.propertyArrayIndex:
            prop += ' [%s]' + prop_value.propertyArrayIndex

        if prop_value.propertyArrayIndex == 0:
            # cast to unsigned integer
            value = prop_value.value.cast_out(Unsigned)

        else:
            # cast to proper data type
            value = prop_value.value.cast_out(
                get_datatype(
                    result['object'][0],
                    prop_value.propertyIdentifier,
                ),
            )

        # store value
        value_dict = prop_values.get(prop_value.propertyIdentifier, {})
        value_dict[prop_value.propertyArrayIndex] = value
        prop_values[prop_value.propertyIdentifier] = value_dict

        prop += ' = %s' % value

        # add values to output
        output += '\n    %s' % prop

    # create object entry
    result[result['object'][0]] = {
        result['object'][1]: prop_values,
    }

    # return parsed data, output
    return result, output


def confirmed_cov_notification_request(apdu):
    """
    This function parses confirmed cov notification request.

    :param apdu: ConfirmedCOVNotificationRequest
    :returns: parsed data, output
    """

    # get parsed data
    result = __cov_notification(apdu)

    # return parsed data, output
    return result


def unconfirmed_cov_notification_request(apdu):
    """
    This function parses unconfirmed cov notification request.

    :param apdu: UnconfirmedCOVNotificationRequest
    :returns: parsed data, output
    """

    # get parsed data
    result = __cov_notification(apdu)

    # return parsed data, output
    return result
