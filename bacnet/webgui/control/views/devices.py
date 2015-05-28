# pylint: disable=import-error

"""
Devices View Module
-------------------

This module contains the interface to provide data for the frontend.
"""

from django.views.decorators.csrf import csrf_exempt

from control.views import control_views_render
from control.models import BACnetObject
from caching import cache_transmit, cache_transmission_commit

from .access import json_dump


def devices_view_render(request, template_file, arg_dict={}, local=True):
    """
    This function is a generic rendering function for the module.

    :param request: Django request
    :param template_file: template filename
    :param arg_dict: arguments
    :param local: template is local
    :return: HTTP response
    """

    # provide default arguments
    default_dict = {}
    default_dict.update(arg_dict)

    # call general rendering function
    return control_views_render(request, template_file, default_dict, local)


def index(request):
    """
    This function provides the index page for the device overview.

    :param request: Django request
    :return: HTTP response
    """

    # return generic response
    return devices_view_render(request, 'devices/index.html')


def __get_objects(request_data, db_only=False):
    """
    This function handles the requested object access

    :param request_data: requested data
    :param db_only: only access cache
    :return: filtered objects
    """

    # get command from request
    command = request_data.get('get').lower()

    # initialize object
    objects = None

    # get parameters from request
    name = request_data.get('name')
    instance = request_data.get('instance')
    device_instance = request_data.get('device')

    # check if instance is given
    if instance is None:
        # create instance
        instance = (request_data.get('type'), request_data.get('id'))

    # check if instance is correctly formed
    if isinstance(instance[1], basestring) and instance[1].isdigit():
        # convert identifier within the instance
        instance = (instance[0], int(instance[1]))

    # check if name or instance were provided
    if name is not None or (isinstance(instance[0], basestring) and isinstance(instance[1], int)):
        # check if name was provided
        if name is not None:
            # get object by name
            objects = BACnetObject.objects.filter(
                name=name,
                is_device=command == 'device',
            )

        else:
            # get object by instance
            objects = BACnetObject.objects.filter(
                object_type=instance[0],
                object_id=instance[1],
                is_device=command == 'device',
            )

        # check if object was requested
        if command == 'object' and device_instance is not None and \
            (isinstance(device_instance[0], basestring) and isinstance(device_instance[1], int)):

            # filter objects by instance
            objects = objects.filter(
                device__object_type=device_instance[0],
                device__object_id=device_instance[1],
            )

        # check if no objects were found
        if objects.count() == 0:
            # check if only cache is supposed to be accessed
            if not db_only:
                # check if device was requested
                if command == 'device':
                    # request device information
                    cache_transmit('whois %s' % name if name is not None else '%s %i' % instance)

                else:
                    # get devices
                    devices = BACnetObject.objects.filter(_device__isnull=True, children__count=0)

                    # loop through known devices
                    for device in devices:
                        # request device object list
                        cache_transmit(
                            'read {0.address} {0.object_type} {0.object_id} objectList'.format(
                                device
                            )
                        )

    # return filtered objects
    return objects


def __update(request_data):
    """
    This function handles update and write requests.

    :param request_data: requested data
    :return: None
    """

    # get parameters from parsed data
    command = request_data.get('get').lower()
    name = request_data.get('property')
    device_id = request_data.get('device')
    object_id = request_data.get('object')
    value = request_data.get('value')

    # get device
    device = BACnetObject.objects.filter(short_id=device_id, is_device=True).all()

    # check if devices were found
    if device.count() > 0:
        # get first device
        device = device[0]

        # get address from device
        address = device.address.address

        # get objects from device
        obj = BACnetObject.objects.filter(short_id=object_id, device=device).all()

        # check if objects were found
        if obj.count() > 0:
            # get first object
            obj = obj[0]

        # check if object identifier was provided
        elif not object_id or object_id == 'false':
            # set object to device
            obj = device

        # check if object was found
        if obj:
            # check if command was update
            if command == 'update':
                # check if property name was provided
                if isinstance(name, basestring) and name != 'false':
                    # request object property
                    cache_transmit(
                        'read %s %s %i %s' % (
                            address,
                            obj.object_type,
                            obj.object_id,
                            name,
                        )
                    )

                else:
                    # request object property list
                    cache_transmit(
                        'read %s %s %i propertyList 0' % (
                            address,
                            obj.object_type,
                            obj.object_id,
                        )
                    )

                    # check if object is device
                    if obj.is_device:
                        # request device object list
                        cache_transmit(
                            'read %s %s %i objectList 0' % (
                                address,
                                obj.object_type,
                                obj.object_id,
                            )
                        )

            # check if command was write
            elif command == 'write':
                # request object property write access
                cache_transmit(
                    'write %s %s %i %s %s' % (
                        address,
                        obj.object_type,
                        obj.object_id,
                        name,
                        value,
                    )
                )

@csrf_exempt
def ajax(request):
    """
    This function provides ajax access for objects in the cache.

    :param request: Django request
    :return: HTTP response
    """

    # get request data
    request_data = request.REQUEST

    # initialize response data
    data = {}

    # check if command was provided
    if 'get' in request_data:
        # get command
        command = request_data.get('get').lower()

        # get access level
        db_only = request_data.get('db_only', 'false').lower() == 'false'

        # check if command was local device
        if command == 'localdevice':
            # get local device
            local_device = BACnetObject.objects.filter(is_local_device=True)

            # check if local devices were found
            if local_device.count() == 0:
                # check if access is limited to cache
                if not db_only:
                    # request local device identification
                    cache_transmit('whois 1')

                    # set updating in response data
                    data['updating'] = True

            # loop through local devices
            for device in local_device:
                # add information to response data
                data[device.short_id] = device.as_dict

        # check if command was devices
        elif command == 'devices':
            # get devices
            devices = BACnetObject.objects.filter(is_device=True)

            # check if access is limited to cache
            if not db_only:
                # request device information of all devices (potentially dangerous)
                cache_transmit('whois')

            # loop through all devices
            for device in devices:
                # add information to response data
                data[device.short_id] = device.as_dict

        # check if command is objects
        elif command == 'objects':
            # get devices
            devices = BACnetObject.objects.filter(is_device=True)

            # check if devices were found
            if devices is not None and devices.count() > 0:
                # loop through devices
                for device in devices:
                    # check if device has known objects
                    if device.children.count() > 0:
                        # get known device information
                        device_dict = data.get(device.short_id, {})

                        # loop through known device objects
                        for obj in device.children.all():
                            # add information to device data
                            device_dict[obj.short_id] = obj.as_dict

                        # add information to response data
                        data[device.short_id] = device_dict

                    # check if access is limited to cache
                    elif not db_only:
                        # request device object list
                        cache_transmit(
                            'read {0.address} {0.object_type} {0.object_id} objectList'.format(
                                device
                            )
                        )

        # check if command is device or object
        elif command in ('device', 'object'):
            # call handler
            objects = __get_objects(request_data, db_only)

            # check if objects were found
            if objects is not None and objects.count() > 0:
                # loop through devices
                for device in objects:
                    # add information to response data
                    data[device.short_id] = device.as_dict

        # check if command is properties
        elif command == 'properties':
            # get devices
            objects = BACnetObject.objects.filter(is_device=False)

            # check if objects were found
            if objects is not None and objects.count() > 0:
                # loop through objects
                for obj in objects:
                    # check if object has known properties
                    if obj.properties.all().count() > 0:
                        # get known device information
                        device_dict = data.get(obj.instance, {})

                        # loop through known object properties
                        for prop in obj.properties.children.all():
                            # add information to device data
                            device_dict[prop.instance] = prop.as_dict

                        # add information to response data
                        data[obj.instance] = device_dict

                    # check if access is limited to cache
                    elif db_only:
                        # request object property list
                        cache_transmit(
                            'read {0.address} {1.object_type} {1.object_id} propertyList'.format(
                                obj.device, obj
                            )
                        )

        # check if command is property
        elif command == 'property':
            # get parameters from request data
            name = request_data.get('property')
            device_id = request_data.get('device')
            object_id = request_data.get('object')

            # get device by identfiier
            device = BACnetObject.objects.filter(short_id=device_id, is_device=True).all()

            # check if devices were found
            if device.count() > 0:
                # get first device
                device = device[0]

                # get device objects
                obj = BACnetObject.objects.filter(short_id=object_id, device=device).all()

                # check if objects were found
                if obj.count() > 0:
                    # get first object
                    obj = obj[0]

                # check if object identifier was provided
                elif not object_id or object_id == 'false':
                    # set device as object
                    obj = device

                # check if object was found
                if obj:
                    # get properties
                    properties = obj.properties

                    # check if name was provided
                    if name:
                        # filter properties by name
                        properties = properties.filter(name=name)

                    # get all properties
                    properties = properties.all()

                    # loop through properties
                    for prop in properties:
                        # add information to response data
                        data[obj.short_id] = {
                            prop.name: prop.as_dict,
                        }

        # check if command was update or write
        elif command in ('update', 'write'):
            # call handler
            __update(request_data)

        else:
            # add error to response data
            data['error'] = 'unknown command'

    # commit requests
    cache_transmission_commit()

    # return HTTP response with json data
    return json_dump(data)
