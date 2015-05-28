# pylint: disable=unused-argument, too-many-branches

"""
Event Handler Module
--------------------

This module provides COV and event requests.
"""

from __future__ import absolute_import

from bacpypes.basetypes import PropertyReference

from bacpypes.pdu import Address
from bacpypes.apdu import SubscribeCOVRequest, SubscribeCOVPropertyRequest

from bacnet.object import get_object_class


def subscribe_request(args, console=None):
    """
    This function creates a write file stream request.

    Usage: subscribe <address> <lifetime> <confirmed> <type> <instance> [ <property> <increment> [ \
<index> ] ]

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if arguments were provided
    if len(args) < 5:
        raise ValueError('too few arguments')

    elif len(args) > 8:
        raise ValueError('too many arguments')

    i = 5

    # read address, life time, type and instance
    address, lifetime, confirmed, obj_type, obj_inst = args[:i]

    # check if life time is correct
    if not lifetime.isdigit():
        raise ValueError('life time must be an integer')

    # check if confirmed is correct
    if not confirmed.lower() in ('true', 'false', '0', '1'):
        raise ValueError('confirmed must be "true" ("1") or "false" ("0")')

    lifetime = int(lifetime)

    # check if object type is correct
    if obj_type.isdigit():
        obj_type = int(obj_type)

    elif not get_object_class(obj_type):
        raise ValueError('unknown object type')

    # check if object instance is correct
    if not obj_inst.isdigit():
        raise ValueError('object instance must be an integer')

    obj_inst = int(obj_inst)

    # check if property was provided
    if i < len(args):
        # read property identifier
        prop_id = args[i]

        i += 1

        if i >= len(args):
            raise ValueError('cov increment must be set')

        # read cov increment
        cov_inc = args[i]

        i += 1

        # check if cov increment is correct
        if not cov_inc.isdigit():
            raise ValueError('cov increment must be an integer')

        cov_inc = int(cov_inc)

        # initialize property array index
        prop_index = None

        # check if property array index was provided
        if i < len(args):
            # read property array index
            prop_index = args[i]

        # check if property array index was defined
        if prop_index is not None:
            # check if property array index is correct
            if not prop_index.isdigit():
                raise ValueError('object instance must be an integer')

            prop_index = int(prop_index)

        # create request
        request = SubscribeCOVPropertyRequest(
            monitoredPropertyIdentifier=PropertyReference(
                propertyIdentifier=prop_id,
                propertyArrayIndex=prop_index,
            ),
            covIncrement=cov_inc,
        )

    else:
        # create request
        request = SubscribeCOVRequest()

    # check if arguments are leftover
    if i < len(args):
        raise ValueError('too many arguments')

    # set variables for subscription
    request.lifetime = lifetime
    request.subscriberProcessIdentifier = 2
    request.monitoredObjectIdentifier = (obj_type, obj_inst)
    request.issueConfirmedNotifications = confirmed.lower() in ('true', '1')

    # set destination
    request.pduDestination = Address(address)

    # return request
    return request
