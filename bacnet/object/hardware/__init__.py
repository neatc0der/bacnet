# pylint: disable=broad-except, star-args, too-many-locals, undefined-loop-variable, invalid-name

"""
Objects Hardware Module
-----------------------

This module collects objects and classes with hardware specific properties.
"""

from __future__ import absolute_import

from collections import Iterable
import pkgutil

from bacnet.debugging import bacnet_debug, ModuleLogger


# enabling logging
ModuleLogger(level='INFO')


def __create_id_overview(object_dict):
    """
    This function creates a list of available ids depending on the object type.

    :param object_dict: object dictionary
    :return: object id overview
    """

    object_ids = {}

    # loop through all entries
    for obj_type, obj_inst in object_dict.keys():
        # check if object instance is greater than the one previously found
        if obj_inst >= object_ids.get(obj_type, 1):
            # store new instance
            object_ids[obj_type] = obj_inst + 1

    # return object id overview
    return object_ids


def __create_object_dict(object_dict, hardware_list, module_name):
    """
    This function populates the object dictionary with new hardware.

    :param object_dict: existing object dictionary
    :param hardware_list: new hardware list
    :param module_name: module name of new hardware
    :return: updated object dictionary
    """

    # create id overview
    object_ids = __create_id_overview(object_dict)

    # loop through hardware objects
    for hw_dict in hardware_list:
        # read hardware list
        hardware_list = hw_dict['hardware']

        # read name
        name = hw_dict['name']

        # check if hardware is iterable
        if not isinstance(hardware_list, Iterable):
            hardware_list = (hardware_list,)

        # loop through hardware
        for i in range(len(hardware_list)):
            # read hardware
            hardware = hardware_list[i]

            # create information
            info = {
                'module': module_name.lower(),
                'Module': module_name.title(),
                'index': i,
                'index1': i + 1,
            }

            # create new initials
            initials = hw_dict['initials'].copy()

            # update initial contents
            for key, value in initials.iteritems():
                initials[key] = value.format(**info)

            # get object type
            obj_type = hw_dict['objectType']

            # set vendor id
            vendor_id = 0

            # check if vendor id was included
            if isinstance(obj_type, tuple) and len(obj_type) == 2:
                vendor_id = obj_type[1]
                obj_type = obj_type[0]

            # get free object id
            obj_inst = object_ids.get(obj_type, 1)

            # update object ids
            object_ids[obj_type] = obj_inst + 1

            # create new object dictionary entry
            object_dict[(obj_type, obj_inst)] = {
                'name': name,
                'vendor': vendor_id,
                'hardware': hardware,
                'initials': initials,
                'poll': hw_dict.get('poll', False),
            }

    # return updated object dictionary
    return object_dict


@bacnet_debug(formatter='%(levelname)s:hardware: %(message)s')
def discover_hardware_objects():
    """
    This function registers all defined objects in all hardware  modules.

    :return: object dictionary
    """

    self = discover_hardware_objects

    object_dict = {}

    # loop through all submodules
    for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):

        # check if module is package
        if is_pkg:

            # set name
            name = '%s.%s' % (__name__, module_name)

            # load module
            module = loader.find_module(name).load_module(name)

            # check if objects exist
            if isinstance(getattr(module, 'HARDWARE_LIST', None), (tuple, list)):

                # check if module name contains an underscore
                if '_' in module_name:
                    # print error message
                    self._warning(
                        'hardware module "%s" has invalid module name '
                        '(underscore is not allowed)' % module_name
                    )

                    # continue
                    continue

                # log info
                self._debug(
                    'found module "%s" to import hardware objects' % module_name
                )

                # create and register classes
                object_dict = __create_object_dict(object_dict, module.HARDWARE_LIST, module_name)

    # return object dictionary
    return object_dict
