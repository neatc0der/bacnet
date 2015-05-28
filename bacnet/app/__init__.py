# pylint: disable=invalid-name, star-args, too-many-locals, too-few-public-methods

"""
Application Module
------------------

This module contains just a single public function for creating a basic device and application to
ensure BACnet conform communications by using BACpypes.

Function for creating device and application:
    create_device_and_app(args)
"""

from __future__ import absolute_import

from bacpypes.basetypes import ServicesSupported
from bacpypes.pdu import Address

from bacnet.debugging import bacnet_debug, ModuleLogger

from bacnet.console.creator import request_creator

from bacnet.object import get_object_list, LocalDeviceObject

from .define import Application


# enable logging
ModuleLogger(level='INFO')


@bacnet_debug(formatter='%(levelname)s:application: %(message)s')
def create_app(args, device_init=None, stdout=None, **kwargs):
    """
    This function creates two BACpypes objects needed for BACnet communications. This includes a
    local device for identification of the BACnet device and grouping of related BACnet objects as
    well as an application for message handling from the network.

    :param args: configuration arguments
    :return: device, application
    """

    self = create_app

    # check if address was defined
    if not hasattr(args.ini, 'address'):
        raise AttributeError('address was not defined in argument nor config file')

    # define standard device parameters and their class (None equals string)
    device_args = (
        (str, 'objectName'),
        (int, 'objectIdentifier'),
        (int, 'maxApduLengthAccepted'),
        (str, 'segmentationSupported'),
        (int, 'vendorIdentifier'),
    )

    # populate device parameter dictionary
    device_kwargs = {}
    for arg_type, argument in device_args:
        value = getattr(args.ini, argument.lower(), None)

        # intercept missing parameters
        if value is not None:
            # cast value
            value = arg_type(value)

            device_kwargs[argument] = value

    # update device initials
    if device_init is not None:
        device_kwargs.update(device_init)

    # create local device object
    device = LocalDeviceObject(
        **device_kwargs
    )

    device.set_value('objectIdentifier', device.get_value('objectIdentifier').value)

    # collect supported services
    pss = ServicesSupported()

    # define standard services for support check
    services = ServicesSupported.bitNames

    # get supported functions from application
    supported_functions = [x.lower() for x in dir(Application)]
    # set supported services
    for service_name in services:
        if 'do_%srequest' % service_name.lower() in supported_functions:
            pss[service_name] = 1

    # set supported services
    device.protocolServicesSupported = pss.value

    # create address
    address = Address(
        args.ini.address if not hasattr(args.ini, 'port') else
        '%s:%s' % (args.ini.address, args.ini.port)
    )

    # get the list of objects to add to application
    kwargs['object_list'] = get_object_list()

    # create specific application
    application = Application(device, address, stdout=stdout, **kwargs)

    commands = []

    # check if examples are enabled and print info
    if args.examples:
        self._info('adding example hardware objects')

        # loop through hardware objects
        for obj_id, obj_dict in application.known_hardware.iteritems():
            # get object class
            options = 'objectIdentifier "%s %i"' % obj_id

            # loop through initials
            for key, value in obj_dict.get('initials', {}).iteritems():
                # add options
                options += ' %s "%s"' % (key, value)

            # add command
            commands.append((
                'create 1 %s %i %s' % (obj_id[0], obj_dict['vendor'], options),
                'added: "%s" as %s' % (obj_dict.get('initials', {}).get('objectName', '?'), obj_id),
            ))

    # sort commands
    commands.sort(key=lambda x: x[1])

    # add startup command for config
    commands.append(('write 1 program 1 programChange load', 'load config'))

    # loop through commands
    for line, comment in commands:
        if comment is not None:
            self._info(comment)

        # create request
        request = request_creator(line, local_id=255)

        # queue request
        application.requests.put(request)

    # return created device and application
    return device, application
