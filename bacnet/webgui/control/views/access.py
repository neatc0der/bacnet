# pylint: disable=import-error, invalid-name, broad-except

"""
Access View Module
------------------

This module contains update functionality for BACnet objects.
"""

from __future__ import print_function

from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from collections import Iterable
from json import loads, dumps
import sys
import traceback

from control.models import BACnetAddress, BACnetObject
from caching import cache_transmit, cache_transmission_commit

from threading import Lock


def json_dump(ret):
    """
    This function converts basic objects into a HTTP response with json string.

    :param ret: basic object
    :return: HTTP response
    """

    # dump object
    j = dumps(ret)

    # return HTTP response with json string
    return HttpResponse(j, content_type="text/plain")


IMPORTANT_PROPERTIES = (
    'objectIdentifier',
    'objectType',
    'objectName',
    'presentValue',
    'description',
    'vendorIdentifier',
    'vendorName',
    'modelName',
    'applicationSoftwareVersion',
    'programState',
    'programChange',
    'reasonForHalt',
    'profileName',
    'programLocation',
)


IMPORTANT_OBJECT_TYPES = (
    'file',
    'program',
    'device',
)


UPDATE_LOCK = Lock()


def __iam(address, parsed_data):
    """
    This function handles the I Am Request.

    :param address: cache object for address
    :param parsed_data: parsed data
    :return: None
    """

    # get object identifier
    obj_inst = parsed_data['content']['id']

    # get device object
    device = BACnetObject.objects.get_or_update(
        instance=obj_inst,
        address=address,
        update_fields=('address',),
    )

    # request device object list
    cache_transmit('read %s device %i objectList 0' % (address.address, device.object_id))


def __readfile(address, content):
    """
    This function handles Atomic Read File ACK.

    :param address: cache object for address
    :param content: parsed content
    :return: None
    """

    # get config file of device object from address
    file_obj = address.device.all()[0].children.filter(object_type='file')[0]

    # check if data was added
    if len(content['data']) + content['start'] > len(file_obj.file_content):
        # append file content
        file_obj.file_content += ' ' * (
            len(content['data']) + content['start'] - len(file_obj.file_content)
        )

    # add received content to file
    file_obj.file_content = file_obj.file_content[:content['start']] + content['data'] \
                          + file_obj.file_content[len(content['data']) + content['start']:]

    # store file object
    file_obj.save()

    # check if end of file was reached
    if not content['eof']:
        # request additional file content
        cache_transmit(
            'rdstr %s %i %i 1000' %
            (
                address.address,
                file_obj.object_id,
                len(content['data']) + content['start']
            )
        )


def __readprop(address, content):
    """
    This function handles Read Property (Multiple) ACK

    :param address: cache object fo address
    :param content: parsed content
    :return: None
    """

    def __device(identifier):
        """
        This function handles the interpretation of devices.

        :param identifier: object identifier
        :return: cache object for device
        """

        # check if device is local
        is_local = address.address == settings.IP_ADDRESS or address.address == '1'

        # get device object
        device = BACnetObject.objects.get_or_update(
            object_type='device',
            object_id=identifier,
            address=address,
            is_local_device=is_local,
            update_fields=('address',),
        )

        # return device object
        return device

    def __object(otype, identifier):
        """
        This function handles the interpretation of objects.

        :param otype: object type
        :param id: object identifier
        :return: cache object
        """

        # get object from device
        obj = device.get_child_objects('%s_%s' % (otype, identifier))

        # check if object was found
        if not obj:
            # get object
            obj = BACnetObject.objects.get_or_update(
                object_type=otype,
                object_id=identifier,
                device=device,
            )

            # request object property list
            cache_transmit(
                'read %s %s %i propertyList 0' %
                (address.address, obj.object_type, obj.object_id)
            )

        # return object
        return obj

    def __objectlist(obj, index, value):
        """
        This function handles the interpretation of object lists.

        :param obj: object
        :param index: property index
        :param value: property value
        :return: cache object
        """

        # check if property index is zero (value == array length)
        if index == 0:
            # loop through array
            for i in xrange(1, value + 1):
                # request object list item i
                cache_transmit(
                    'read %s %s %i objectList %i' %
                    (
                        address.address,
                        obj.object_type,
                        obj.object_id,
                        i
                    )
                )

        # check if property index is an integer
        elif isinstance(index, int):
            # request object property list
            cache_transmit(
                'read %s %s %i propertyList 0' %
                ((address.address,) + value)
            )

    def __proplist(obj, index, value):
        """
        This function handles the interpretation of property lists.

        :param obj: object
        :param index: property index
        :param value: property value
        :return: cache object
        """

        # check if property index is zero (value == array length)
        if index == 0:
            # loop through array
            for i in range(1, value + 1):
                # request property list item i
                cache_transmit(
                    'read %s %s %i propertyList %i' %
                    (
                        address.address,
                        obj.object_type,
                        obj.object_id,
                        i
                    )
                )

        # check if property index is an integer
        elif isinstance(index, int):
            # check if property value is an important property identifier
            if not value in ('propertyList', 'objectList') and \
                (value in IMPORTANT_PROPERTIES or
                 obj.object_type in IMPORTANT_OBJECT_TYPES):
                # request property value
                cache_transmit(
                    'read %s %s %i %s' %
                    (
                        address.address,
                        obj.object_type,
                        obj.object_id,
                        value
                    )
                )

    # loop through defined object types
    for obj_type, obj_ids in content.iteritems():

        # loop through defined object identifiers
        for obj_id, properties in obj_ids.iteritems():

            # check if object id is an integer
            if obj_id.isdigit():
                # interpret object id as integer
                obj_id = int(obj_id)

            # check if object type is device
            if obj_type == 'device':
                # call handler
                current_obj = __device(obj_id)

            else:
                # get all devices originating from the source address
                device = address.device.all()

                # check if devices were found
                if not device:
                    # request device identification
                    cache_transmit('whois %s' % address.address)

                    # continue
                    continue

                # get first device
                device = device[0]

                # call handler
                current_obj = __object(obj_type, obj_id)

            # loop through property identifiers
            for prop_id, prop_dict in properties.iteritems():
                # loop through property indices
                for prop_index, prop_value in prop_dict.iteritems():
                    # check if property index is an integer
                    if prop_index.isdigit():
                        # convert property index to integer
                        prop_index = int(prop_index)

                    # check if property index is null
                    elif prop_index == u'null':
                        # set property index to None
                        prop_index = None

                    # check if property is a value from the object List
                    if prop_id == 'objectList' and \
                        (isinstance(prop_value, Iterable) and
                         not isinstance(prop_value, basestring)):
                        # convert property value to tuple
                        prop_value = tuple(prop_value)

                    # get property
                    prop = current_obj.get_or_create_property(
                        name=prop_id,
                    )

                    # set property value
                    prop.set_value(prop_value, prop_index)

                    # store property
                    prop.save()

                    # check if property identifier is object list
                    if prop_id == 'objectList':
                        # call handler
                        __objectlist(current_obj, prop_index, prop_value)

                    # check if property identifier is property list
                    elif prop_id == 'propertyList':
                        # call handler
                        __proplist(current_obj, prop_index, prop_value)

                    # check if property belongs to file object
                    elif prop_id == 'objectType' and prop_value == 'file':

                        # request file content
                        cache_transmit(
                            'rdstr %s %i 0 1000' %
                            (
                                address.address,
                                obj_id,
                            )
                        )


@csrf_exempt
def update(request):
    """
    This function receives parsed APDUs as json and updates the cache.

    :param request: Django request
    :return: Http response
    """

    # get submitted data
    parsed_data = request.body

    try:
        # parse json
        parsed_data = loads(parsed_data)

    except:
        # return HTTP 404 error if parsing failed
        return Http404()

    # check if APDU is Who Is Request
    if parsed_data['class'] == 'WhoIsRequest':
        # return empty HTTP response
        return HttpResponse()

    try:
        # acquire lock for updating the cache
        UPDATE_LOCK.acquire()

        # get content of the APDU
        content = parsed_data.get('content', {})

        # get cache object for ip address
        address = BACnetAddress.objects.get_or_update(
            address=parsed_data['source'],
        )

        # check if APDU is I Am Request
        if parsed_data['class'] == 'IAmRequest':
            # call handler
            __iam(address, parsed_data)

        # check if APDU is Atomic Read File ACK
        elif parsed_data['class'] == 'AtomicReadFileACK':
            # call handler
            __readfile(address, content)

        # check if APDU is Read Property (Multiple) ACK
        elif parsed_data['class'] in ('ReadPropertyACK', 'ReadPropertyMultipleACK'):
            # call handler
            __readprop(address, content)

    except Exception as error:
        # collect error information
        exc_traceback = sys.exc_info()[-1]

        # print traceback
        traceback.print_tb(exc_traceback, file=sys.stdout)

        # print error message
        print(error)

    finally:
        # commit cached transmission lines
        cache_transmission_commit()

        # release update lock
        UPDATE_LOCK.release()

    # return HTTP response
    return HttpResponse()
