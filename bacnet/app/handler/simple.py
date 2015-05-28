# pylint: disable=invalid-name, too-many-locals, star-args

"""
Application Handler Module
--------------------------

This module provides basic functions for value casting, property creation and general handlers.
"""

from __future__ import absolute_import

import time

from bacpypes.constructeddata import Array, Any
from bacpypes.primitivedata import Unsigned, Null
from bacpypes.basetypes import ErrorType

from bacpypes.errors import ExecutionError

from bacpypes.object import PropertyError

from bacpypes.apdu import ReadAccessResultElement, ReadAccessResultElementChoice, SimpleAckPDU, \
    ReadPropertyACK, ReadPropertyMultipleACK, ReadAccessResult, IAmRequest, IHaveRequest

from bacnet.object import get_object_class

from bacnet.console.creator import cast_value

from bacnet.debugging import bacnet_debug, ModuleLogger


# enable logging
ModuleLogger()


def do_WhoIsRequest(self, apdu):
    """
    This function responses to WhoIs requests.

    :param apdu: incoming message
    :return: None
    """

    self._debug('do_WhoIsRequest %r', apdu)

    # check if restrictions exist
    if apdu.deviceInstanceRangeLowLimit is not None and \
            apdu.deviceInstanceRangeHighLimit is not None:

        # get device identifier
        device_id = self.localDevice.objectIdentifier

        # check if identifier is of class object identifier
        if hasattr(device_id, 'get_tuple'):
            # make device identifier tuple
            device_id = device_id.get_tuple()

        # check if device id is below limit
        if device_id[1] < apdu.deviceInstanceRangeLowLimit or \
            device_id[1] > apdu.deviceInstanceRangeHighLimit:

            # exit
            return

    # create IAm request
    request = IAmRequest()
    request.pduDestination = apdu.pduSource
    request.iAmDeviceIdentifier = self.localDevice.objectIdentifier
    request.maxAPDULengthAccepted = self.localDevice.maxApduLengthAccepted
    request.segmentationSupported = self.localDevice.segmentationSupported
    request.vendorID = self.localDevice.vendorIdentifier

    self._debug('   - request: %r', request)

    # send request to request queue - IAm is not a response!
    self.requests.put(request)

    # return
    return


def do_IAmRequest(self, apdu):
    """
    This function reads data from I Am request.

    :param apdu: incoming message
    :return: None
    """
    self._debug('do_IAmRequest %r', apdu)

    # update known devices
    self.known_devices[str(apdu.pduSource)] = {
        'id': apdu.iAmDeviceIdentifier,
        'last_seen': time.time(),
    }

    # update unknown device identifiers within remote subscriptions
    self.check_remote_subscription_updates(apdu)

    # check for subscription that need an update
    self.check_subscription_updates(apdu)

    # return
    return


def do_WhoHasRequest(self, apdu):
    """
    This function responses to WhoHas requests.

    :param apdu: incoming message
    :return: None
    """
    self._debug('do_WhoHasRequest %r', apdu)

    # check if restrictions exist
    if hasattr(apdu, 'deviceInstanceRangeLowLimit') and \
            apdu.deviceInstanceRangeLowLimit is not None and \
            apdu.deviceInstanceRangeHighLimit is not None:

        # get device identifier
        device_id = self.localDevice.objectIdentifier

        # check if identifier is of class object identifier
        if hasattr(device_id, 'get_tuple'):
            # make device identifier tuple
            device_id = device_id.get_tuple()

        # check if device id is above or below limit
        if device_id[1] < apdu.deviceInstanceRangeLowLimit or \
            device_id[1] > apdu.deviceInstanceRangeHighLimit:

            # exit
            return

    # read object identifier or name
    if apdu.object.objectIdentifier is not None:
        obj = self.get_object_by_id(apdu.object.objectIdentifier)

    elif apdu.object.objectName is not None:
        obj = self.get_object_by_name(apdu.object.objectName)

    else:
        apdu.debug_contents(file=self.stdout)

        # exit
        return

    # check if object exists
    if obj is not None:
        # read device identifier
        device_id = getattr(
            self.localDevice.objectIdentifier,
            'value',
            self.localDevice.objectIdentifier
        )

        # read object identifier
        obj_id = getattr(obj.objectIdentifier, 'value', obj.objectIdentifier)

        # read object name
        obj_name = getattr(obj.objectName, 'value', obj.objectName)

        # create IHave request
        request = IHaveRequest()
        request.pduDestination = apdu.pduSource
        request.deviceIdentifier = device_id
        request.objectIdentifier = obj_id
        request.objectName = obj_name

        self._debug('   - request: %r', request)

        # send request to request queue - IHave is not a response!
        self.requests.put(request)

    # return
    return


def do_IHaveRequest(self, apdu):
    """
    This function reads data from I Have request.

    :param apdu: incoming message
    :return: None
    """
    self._debug('do_IHaveRequest %r', apdu)

    # return
    return


@bacnet_debug
def read_property_any(obj, prop_id, prop_index=None, prop=None):
    """
    This function creates an appropriate property value of type Any.

    :param obj: object
    :param prop_id: property id
    :param prop_index: property array index
    :param prop: property instance
    :return: Any instance
    """
    read_property_any._debug(
        'ReadPropertyToAny %s %r %r',
        obj,
        prop_id,
        prop_index,
    )

    # get property
    prop_instance = prop if prop is not None else obj._properties.get(prop_id)

    # check if obj exists
    if obj is None:
        raise ExecutionError(errorClass='object', errorCode='objectNotFound')

    # get data type
    data_type = obj.get_datatype(prop_id)

    read_property_any._debug('   - datatype: %r', data_type)

    # check if data type was set
    if data_type is None:
        raise ExecutionError(errorClass='property', errorCode='datatypeNotSupported')

    # read value
    value = obj.ReadProperty(prop_id, prop_index)

    read_property_any._debug('   - value: %r', value)

    # cast value
    value = cast_value(value, data_type, prop_index, prop=prop_instance)

    # create result
    result = Any()

    # cast value
    if value is not None:
        result.cast_in(value)

    read_property_any._debug('   - result: %r', result)

    # return result
    return result


@bacnet_debug
def property_to_result(obj, prop_id, prop_index=None):
    """
    This function creates an appropriate ReadAccessResultElement.

    :param obj: object
    :param prop_id: property id
    :param prop_index: property array index
    :return: ReadAccessResultElement instance
    """
    self = property_to_result

    self._debug(
        'ReadPropertyToResultElement %s %r %r',
        obj,
        prop_id,
        prop_index,
    )

    # create read result
    read_result = ReadAccessResultElementChoice()

    # check if object exists
    if obj is None:
        # set access error
        read_result.propertyAccessError = ErrorType(
            errorClass='object',
            errorCode='unknownObject'
        )

        self._debug('   - error: object does not exist',)

    else:
        try:
            # set property value
            read_result.propertyValue = read_property_any(
                obj,
                prop_id,
                prop_index,
            )

            self._debug('   - success')

        except PropertyError as error:
            # set access error
            read_result.propertyAccessError = ErrorType(
                errorClass='property',
                errorCode='unknownProperty'
            )

            self._debug('   - error: %r', error)

        except ExecutionError as error:
            # set access error
            read_result.propertyAccessError = ErrorType(
                errorClass=error.errorClass,
                errorCode=error.errorCode
            )

            self._debug('   - error: %r', error)

    # create result element
    result_element = ReadAccessResultElement(
        propertyIdentifier=prop_id,
        propertyArrayIndex=prop_index,
        readResult=read_result,
    )

    # return result element
    return result_element


def __partial_PropertyMultipleRequest(write, access, obj):
    # pylint: disable=too-many-branches
    """
    This function loops through received properties.

    :param write: specify if a read or write request is handed over
    :param access: current access object
    :param obj: object
    :return: parsed data
    """
    result_dict = {}

    # store object
    result_dict['object'] = obj

    # read list of results
    if write:
        result_list = access.listOfProperties

    else:
        result_list = access.listOfPropertyReferences

    # loop through properties
    for element in result_list:
        # read property id
        prop_id = element.propertyIdentifier

        # read property array index
        prop_index = element.propertyArrayIndex

        # read property id and array index
        parameter = (prop_id, prop_index)

        # read property result
        if write:

            # set priority
            result_dict['priority'] = element.priority

            # read value and priority
            parameter += (element.value, element.priority)

            # call partial function for request
            __partial_WritePropertyRequest(obj, *parameter)

        else:

            # read element list
            element_list = result_dict.get('element_list', [])

            # check if property id is special
            if prop_id in ('all', 'required', 'optional'):

                # get properties
                if obj is None:
                    properties = tuple(
                        (p.identifier, p)
                        for p in getattr(
                            get_object_class(access.objectIdentifier.get_tuple()[0]),
                            'properties',
                            ()
                        )
                    )

                else:
                    properties = obj._properties.items()

                # loop through all properties
                for prop_id_spec, prop in properties:

                    # check if property is required
                    if prop_id == 'required' and prop.optional:
                        continue

                    # check if property is optional
                    elif prop_id == 'optional' and not prop.optional:
                        continue

                    # preset property index
                    prop_index_spec = None

                    # check if property is array
                    if isinstance(prop.datatype, Array):
                        # set property index to 0
                        prop_index_spec = 0

                    # create result element for response
                    result_element = property_to_result(
                        obj,
                        prop_id_spec,
                        prop_index_spec,
                    )

                    # append element to list
                    element_list.append(result_element)

                    # store property
                    result_dict[prop_id_spec] = prop

            else:

                # create result element for response
                result_element = property_to_result(
                    obj,
                    prop_id,
                    prop_index,
                )

                # append element to list
                element_list.append(result_element)

            # store element list
            result_dict['element_list'] = element_list

    # return result dict
    return result_dict


def __do_PropertyMultipleRequest(self, apdu, write=False):
    """
    This function reads all values from request response.

    :param apdu: incoming message
    :param write: specify if a read or write request is handed over
    :return: parsed data
    """
    self._debug('__do_PropertyMultipleRequest %r', apdu)

    result_dict = {}

    # retrieve objects
    if write:
        access_list = apdu.listOfWriteAccessSpecs
    else:
        access_list = apdu.listOfReadAccessSpecs

    # loop through objects
    for access in access_list:

        # read object id
        obj_id = access.objectIdentifier

        # get object by id
        obj = self.get_object_by_id(obj_id)

        # get result
        result = __partial_PropertyMultipleRequest(write, access, obj)

        # check if request is to read data
        if not write:

            # get element list
            element_list = result.get('element_list', [])

            # check if element list is defined in result
            if 'element_list' in result:
                # remove element list from result
                del result['element_list']

                # create results
                access_results = ReadAccessResult(
                    objectIdentifier=obj_id,
                    listOfResults=element_list,
                )

                # get result list
                result_list = result_dict.get('result_list', [])

                # append access results to result list
                result_list.append(access_results)

                # store result list
                result_dict['result_list'] = result_list

        # read stored object ids
        obj_ids = result_dict.get(obj_id[0], {})

        # read stored properties
        properties = obj_ids.get(obj_id[1], {})

        # update properties
        properties.update(result)

        # store updated properties
        obj_ids[obj_id[1]] = properties

        # store updated object ids
        result_dict[obj_id[0]] = obj_ids

    # return result dict
    return result_dict


def do_ReadPropertyMultipleRequest(self, apdu):
    """
    This function reads all values from request.

    :param apdu: incoming message
    :return: response
    """
    self._debug('do_ReadPropertyMultipleRequest %r', apdu)

    # retrieve data
    result_dict = __do_PropertyMultipleRequest(self, apdu, write=False)

    # get result list
    result_list = result_dict.get('result_list', [])
    if 'result_list' in result_dict:
        del result_dict['result_list']

    # create acknowledgement
    resp = ReadPropertyMultipleACK(context=apdu)
    resp.listOfReadAccessResults = result_list

    # return response
    return resp


def do_WritePropertyMultipleRequest(self, apdu):
    """
    This function reads all values from request.

    :param apdu: incoming message
    :return: response
    """
    self._debug('do_WritePropertyMultipleRequest %r', apdu)

    resp = None

    # loop through objects
    for access in apdu.listOfWriteAccessSpecs:

        # read object id
        obj_id = access.objectIdentifier

        # get object by id
        obj = self.get_object_by_id(obj_id)

        # check if object exists
        if obj is None:

            # create error
            raise ExecutionError(errorClass='object', errorCode='unknownObject')

        # loop though properties
        for prop in access.listOfProperties:

            # read property id
            prop_id = prop.propertyIdentifier

            # read property index
            prop_index = prop.propertyArrayIndex

            try:

                # read property value
                obj.ReadProperty(prop_id, prop_index)

            except Exception as error:
                self._error(error)

                # create error
                raise ExecutionError(errorClass='object', errorCode='unknownProperty')

        # check if error was created
        if resp is not None:

            # stop here
            break

    if resp is None:
        # retrieve data
        __do_PropertyMultipleRequest(self, apdu, write=True)

        # create acknowledgement
        resp = SimpleAckPDU(context=apdu)

    # return response
    return resp


def __partial_ReadPropertyRequest(obj, prop_id, prop_index, prop=None):
    """
    This function reads values from request and returns value.

    :param obj: object
    :param prop_id: property id
    :param prop_index: property array index
    :param prop: property instance
    :return: value
    """

    # check if obj exists
    if obj is None:
        raise ExecutionError(errorClass='object', errorCode='unknownObject')

    # get property
    prop_instance = prop if prop is not None else obj._properties.get(prop_id)

    # get data type
    data_type = obj.get_datatype(prop_id)

    # read value
    value = obj.ReadProperty(prop_id, prop_index)

    # check if value was set
    if data_type is None:
        raise PropertyError(prop_id)

    # cast value
    value = cast_value(value, data_type, prop_index, prop=prop_instance)

    # return value
    return value


def do_ReadPropertyRequest(self, apdu):
    """
    This function reads value from request response.

    :param apdu: incoming message
    :return: None
    """
    self._debug('do_ReadPropertyRequest %r', apdu)

    # read object id
    obj_id = apdu.objectIdentifier

    # check if device has wildcard
    if obj_id == ('device', 4194303):
        self._debug('   - wildcard device identifier')

        # read object id from local device
        obj_id = self.localDevice.objectIdentifier

    # get the object
    obj = self.get_object_by_id(obj_id)

    self._debug('   - object: %r', obj)

    # check if object was found
    if not obj:
        raise ExecutionError(errorClass='object', errorCode='unknownObject')

    try:
        # read value from apdu
        value = __partial_ReadPropertyRequest(
            obj,
            apdu.propertyIdentifier,
            apdu.propertyArrayIndex
        )

        # create acknowledgement
        resp = ReadPropertyACK(context=apdu)
        resp.objectIdentifier = obj_id
        resp.propertyIdentifier = apdu.propertyIdentifier
        resp.propertyArrayIndex = apdu.propertyArrayIndex

        # cast in value
        resp.propertyValue = Any()
        if value is not None:
            resp.propertyValue.cast_in(value)

    except PropertyError:
        raise ExecutionError(errorClass='property', errorCode='unknownProperty')

    # return response
    return resp


def __partial_WritePropertyRequest(obj, *args):
    """
    This function reads values from request response and returns value.

    :param obj: object
    :param prop_id: property id
    :param prop_index: property array index
    :param priority: property priority
    :return: value
    """
    prop_id, prop_index, prop_value, prop_priority = args

    # check if property exists
    if obj.get_datatype(prop_id) is None:
        raise PropertyError('property %s does not exist' % prop_id)

    # get data type
    if prop_value.is_application_class_null():
        datatype = Null

    else:
        datatype = obj.get_datatype(prop_id)

    # cast value if necessary
    if issubclass(datatype, Array) and (prop_index is not None):

        if prop_index == 0:
            value = prop_value.cast_out(Unsigned)

        else:
            value = prop_value.cast_out(datatype.subtype)

    else:
        value = prop_value.cast_out(datatype)

    # change the value
    obj.WriteProperty(
        prop_id,
        value,
        prop_index,
        prop_priority
    )

    # return value
    return value


def do_WritePropertyRequest(self, apdu):
    """
    This function reads value from request response.

    :param apdu: incoming message
    :return: None
    """
    # get object
    obj = self.get_object_by_id(apdu.objectIdentifier)

    self._debug('do_WritePropertyRequest %r', apdu)
    self._debug('   - object: %r', obj)

    # check if object was found
    if not obj:
        raise ExecutionError(errorClass='object', errorCode='unknownObject')

    try:
        # read value from apdu
        __partial_WritePropertyRequest(
            obj,
            apdu.propertyIdentifier,
            apdu.propertyArrayIndex,
            apdu.propertyValue,
            apdu.priority
        )

        # create acknowledgement
        resp = SimpleAckPDU(context=apdu)

    except PropertyError:
        raise ExecutionError(errorClass='property', errorCode='unknownProperty')

    # return response
    return resp
