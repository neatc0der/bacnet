# pylint: disable=

"""
Local Handler Module
--------------------

This module provides local access requests. - DEPRECATED !
"""

from __future__ import absolute_import

import sys

from bacpypes.constructeddata import Array


# code dump
# ---------
#
# def do_set(self, args):
#     """
#     This function sets the property value of a local property.
#
#     Usage: set ( <name> | <type> <instance> ) <property> <value> [ <index> ]
#
#     :param args: string of parameters
#     :return: None
#     """
#
#     self._debug('do_set %r', args)
#
#     # read object name
#     obj_name = args[0]
#
#     i = 1
#
#     # check if object id was set
#     if i < len(args) and args[i].isdigit():
#         # read object id
#         obj_id = (obj_name, int(args[i]))
#         i += 1
#
#         # get object by id
#         obj = self.application.get_object_by_id(obj_id)
#
#     else:
#         # get object by name
#         obj = self.application.get_object_by_name(obj_name)
#
#     # call helper function
#     local_set(args, i, obj)
#
# def do_list(self, args):
#     """
#     This function lists all objects within the application, all properties within an object, or
#     the property value of a property.
#
#     Usage: list [ ( <name> | <type> <instance> ) [ <property> [ <index> ] ] ]
#
#     :param args: string of parameters
#     :return: None
#     """
#
#     self._debug('do_list %r', args)
#
#     obj = None
#     objs = None
#
#     i = 0
#
#     # read all objects
#     if len(args) == 0:
#         objs = self.application.objectName.values()
#
#     else:
#         # read object name
#         obj_name = args[0]
#
#         i += 1
#
#         # check if object id was set
#         if i < len(args) and args[i].isdigit():
#             # read object id
#             obj_id = (obj_name, int(args[i]))
#             i += 1
#
#             # get object by id
#             obj = self.application.get_object_by_id(obj_id)
#
#         else:
#             # get object by name
#             obj = self.application.get_object_by_name(obj_name)
#
#     local_list(args, i, obj, objs)


def __list_property_value(obj, prop_id, prop_index=None):
    """
    This function handles listing of property values.

    :param args: list of parameters
    :param i: parameter position
    :param obj: object
    :return: None
    """

    # check if property id is set to 'all'
    if prop_id == 'all':
        # check if property index is set
        if prop_index is not None:
            ValueError('property index invalid for "all"')

        # collect all property ids of the object
        prop_ids = tuple(
            p_id for p_id in obj.propertyList
            if p_id != 'propertyList' and isinstance(p_id, basestring)
        )

        values = [
            (
                'Identifier',
                'Type',
                'Value'
            ),
        ]

    else:
        prop_ids = (prop_id,)

        values = [
            (
                'Type',
                'Value'
            ),
        ]

    # loop through
    for prop_id in prop_ids:
        # read property value
        value = obj.ReadProperty(prop_id, prop_index)

        # get data type
        data_type = obj.get_datatype(prop_id)

        # check if property index was set
        if prop_index is not None:

            # check if property data type is array
            if not issubclass(data_type, Array):
                raise ValueError('property data type is not an array')

            # get subtype of array
            data_type = data_type.subtype

        elif issubclass(data_type, Array):
            value = ()

            # loop through values
            for i in range(obj.ReadProperty(prop_id, 0)):

                # read new value
                new_value = obj.ReadProperty(prop_id, i+1)
                new_value = getattr(new_value, 'value', new_value)

                # reset new value
                value += (new_value,)

        # create value line
        value_line = (
            data_type.__name__,
            value,
        )

        # add identifier if required
        if len(prop_ids) > 1:
            value_line = (prop_id,) + value_line

        # append line
        values.append(value_line)

    # print value
    print_values(values)


def print_values(values):
    """
    This function prints all arguments.

    :param values: list of argument tuples
    :return: None
    """

    def __get_max_values(values):
        """
        This function collects maximum lengths for all arguments.

        :param values: list of argument tuples
        :return: maximum lengths
        """
        # initialize max values
        max_values = len(values[0]) * (0,)

        # loop through values
        for i in range(len(values)):
            new_max_values = ()

            # loop through arguments
            for j in range(len(values[i])):
                new_max_values += (
                    len(str(values[i][j]))
                    if len(str(values[i][j])) > max_values[j]
                    else max_values[j],
                )

            max_values = new_max_values

        # return max values
        return max_values

    # get maximum lengths
    max_values = __get_max_values(values)

    # loop through values
    for i in range(len(values)):
        # loop through arguments
        for j in range(len(values[i])):
            sys.stdout.write(
                '%s%s' %
                (
                    str(values[i][j]).ljust(max_values[j]),
                    ' ' if j+1 < len(values[i]) else '\n'
                )
            )

        # add line under header
        if i == 0:
            sys.stdout.write('%s\n' % ((sum(max_values) + len(values[0]) - 1) * '-'))

    sys.stdout.flush()


def local_set(args, i, obj):
    """
    This function sets the property value of a local property.

    :param args: list of parameters
    :param obj: object
    :return: None
    """
    # check if arguments were provided
    if len(args) < 3:
        raise ValueError('too few arguments')

    elif len(args) > 5:
        raise ValueError('too many arguments')

    # check if object id is valid
    if obj is None:
        raise ValueError('object not found')

    # read property id
    prop_id = args[i]
    i += 1

    if i >= len(args):
        raise ValueError('value not found')

    # read value
    value = args[i]
    i += 1

    # read property
    prop = obj._properties.get(prop_id)

    # check if property is valid
    if prop is None:
        raise ValueError('property not found')

    prop_index = None

    # check if property check was set
    if i < len(args):
        if not args[i].isdigit():
            raise ValueError('array index must be integer')

        # read property index
        prop_index = int(args[i])

    # read property value
    old_value = obj.ReadProperty(prop_id, prop_index)

    datatype = prop.datatype

    # check if property index was set
    if prop_index is not None:

        # check if property data type is array
        if not issubclass(datatype, Array):
            raise ValueError('property data type is not an array')

        datatype = datatype.subtype

    # check if property value is an array
    elif issubclass(datatype, Array):
        raise ValueError('property index is required for an array')

    # write property value
    obj.WriteProperty(prop_id, value, arrayIndex=prop_index)

    # get value string if available
    value = getattr(value, 'value', value)
    old_value = getattr(old_value, 'value', old_value)

    # print info
    sys.stdout.write('(%s) %r -> %r\n' % (datatype.__name__, old_value, value))
    sys.stdout.flush()


def local_list(args, i, obj=None, objs=None):
    """
    This function lists all objects within the application, all properties within an object, or the
    property value of a property.

    :param args: list of parameters
    :param obj: object
    :return: None
    """

    # check if no argument was passed
    if objs:
        values = [
            (
                'Type',
                'Name',
                'Identifier',
            ),
        ]

        # collect all objects
        for obj in objs:
            values.append(
                (
                    '%s:' % obj.__class__.__name__,
                    '%s,' % obj.objectName,
                    obj.objectIdentifier,
                )
            )

        # print all objects
        print_values(values)

        # exit
        return

    # arguments are malformed
    elif len(args) > 3:
        raise ValueError('too many arguments')

    # check if object id is valid
    if obj is None:
        raise ValueError('object not found')

    # check if property was set
    if i < len(args):
        # read property id
        prop_id = args[i]
        i += 1

        # check if all properties were requested
        if prop_id != 'all':
            # read property
            data_type = obj.get_datatype(prop_id)

            # check if property is valid
            if data_type is None:
                raise ValueError('property not found')

        prop_index = None

        # check if property check was set
        if i < len(args):
            if not args[i].isdigit():
                raise ValueError('array index must be integer')

            # read property index
            prop_index = int(args[i])

        # list property value
        __list_property_value(obj, prop_id, prop_index)

    else:
        values = [
            (
                'Type',
                'Identifier',
            ),
        ]

        # collect all properties
        for prop in obj.properties:
            values.append(
                (
                    '%s:' % prop.__class__.__name__,
                    prop.identifier,
                )
            )

        # print all properties
        print_values(values)
