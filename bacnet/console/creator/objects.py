# pylint: disable=unused-argument

"""
Objects Handler Module
----------------------

This module provides object requests.
"""

from __future__ import absolute_import

from bacpypes.constructeddata import Any

from bacpypes.apdu import CreateObjectRequest, DeleteObjectRequest, PropertyValue, \
    CreateObjectRequestObjectSpecifier
from bacpypes.pdu import Address

from bacnet.object import get_object_class, get_datatype

from .simple import cast_value


def create_request(args, console=None):
    """
    This function creates a create object request.

    Usage: create <address> <type> [ <vendor> ] ( <property> <value> [ <index> [ priority ] ] )* ...

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if arguments were provided
    if len(args) < 3:
        raise ValueError('too few arguments')

    i = 3

    # read address, type and instance
    address, obj_type, obj_inst = args[:i]

    # check if object type is correct
    if obj_type.isdigit():
        obj_type = int(obj_type)

    elif not get_object_class(obj_type):
        raise ValueError('unknown object type')

    # check if vendor id is correct
    if not obj_inst.isdigit():
        obj_inst = 0
        i -= 1

    else:
        obj_inst = int(obj_inst)

    # create object id
    obj_id = (obj_type, obj_inst)

    initials = []

    # loop through arguments
    while i < len(args):
        # read property id
        prop_id = args[i]

        i += 1

        # check if value follows
        if i >= len(args):
            raise ValueError('value not found')

        # read value
        value = args[i]
        i += 1

        index = None

        # create property value object
        prop = PropertyValue()
        prop.propertyIdentifier = prop_id

        if i < len(args) and args[i].isdigit():
            # read and set index
            prop.propertyArrayIndex = int(args[i])

            i += 1

            if i < len(args) and args[i].isdigit():
                # read and set priority
                prop.priority = int(args[i])

                i += 1

        # get data type by object type and property id
        data_type = get_datatype(obj_type, prop_id, obj_inst)

        # cast value
        value = cast_value(
            value,
            data_type,
            index,
        )

        # set value data type and cast in value
        prop.value = Any()
        prop.value.cast_in(value)

        # append property value to initial list
        initials.append(prop)


    # create object specifier
    obj_spec = CreateObjectRequestObjectSpecifier()
    obj_spec.objectType = obj_id[0]
    obj_spec.objectIdentifier = obj_id

    # create request
    request = CreateObjectRequest()
    request.objectSpecifier = obj_spec
    request.listOfInitialValues = initials

    # send to specified address
    request.pduDestination = Address(address)

    # return created request
    return request


def delete_request(args, console=None):
    """
    This function creates a delete object request.

    Usage: delete <address> <type> <instance>

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if arguments were provided
    if len(args) < 3:
        raise ValueError('too few arguments')

    elif len(args) > 3:
        raise ValueError('too many arguments')

    # read address, type and instance
    address, obj_type, obj_inst = args

    # check if object type is correct
    if obj_type.isdigit():
        obj_type = int(obj_type)

    elif not get_object_class(obj_type):
        raise ValueError('unknown object type')

    # check if object instance is correct
    if not obj_inst.isdigit():
        raise ValueError('object instance invalid')

    # make object instance to integer
    obj_inst = int(obj_inst)

    # create request
    request = DeleteObjectRequest()
    request.objectIdentifier = (obj_type, obj_inst)

    # send to specified address
    request.pduDestination = Address(address)

    # return created request
    return request
