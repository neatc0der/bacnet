# pylint: disable=invalid-name, star-args, broad-except

"""
Objects Handler Module
----------------------

This module provides object handlers.
"""

from bacpypes.errors import ExecutionError

from bacpypes.apdu import SimpleAckPDU, Error, CreateObjectACK

from bacnet.object import get_object_class, get_datatype

from bacnet.debugging import ModuleLogger


# enabling logging
ModuleLogger()


def do_CreateObjectRequest(self, apdu):
    """
    This functions handles object creation.

    :param apdu: incoming message
    :return: None
    """
    self._debug('do_CreateObjectRequest %r', apdu)

    # read object specifier
    obj_spec = apdu.objectSpecifier

    # read object type
    obj_type = obj_spec.objectType

    # check if object type is correct
    if obj_type.isdigit():
        obj_type = int(obj_type)

    # get object type
    obj_type = get_object_class(obj_type)

    # check if object type exists
    if obj_type is None:
        # create error
        raise ExecutionError(errorClass='object', errorCode='unsupportedObjectType')

    # read initial property values
    initials = apdu.listOfInitialValues

    # store object id
    obj_id = (obj_type.objectType, self.get_object_id(obj_type.objectType))

    # initialize
    obj_parameters = {
        'objectIdentifier': obj_id,
    }
    prop_write = ()

    # loop through initial values
    for prop in initials:
        # read value
        value = prop.value

        # get data type
        data_type = get_datatype(obj_type.objectType, prop.propertyIdentifier)

        # cast value
        value = value.cast_out(data_type)

        # check if property is an array
        if prop.propertyArrayIndex is None and prop.priority is None:
            # add property value to initialization
            obj_parameters[prop.propertyIdentifier] = value

        else:
            # add property value to list for later usage
            prop_write += ((
                prop.propertyIdentifier,
                value,
                prop.propertyArrayIndex,
                prop.priority
            ),)

    # check if object name was defined
    if not 'objectName' in obj_parameters:
        # set name
        obj_parameters['objectName'] = '%s_%i' % obj_id

    try:
        # create object
        obj = obj_type(**obj_parameters)

        # loop through property values
        for prop in prop_write:
            # set initial values
            obj.WriteProperty(*prop)

        try:
            # add object to application
            self.add_object(obj)

            # create response
            resp = CreateObjectACK(context=apdu)

            # set object identifier
            resp.objectIdentifier = obj.objectIdentifier

        except Exception as error:
            self._error(error)

            # create error
            resp = Error(
                errorClass='object',
                errorCode='objectIdentifierAlreadyExists',
                context=apdu
            )

    except Exception as error:
        self._error(error)

        # create error
        resp = Error(errorClass='object', errorCode='internalError', context=apdu)

    # return response
    return resp


def do_DeleteObjectRequest(self, apdu):
    """
    This functions handles object deletion.

    :param apdu: incoming message
    :return: None
    """
    self._debug('do_DeleteObjectRequest %r', apdu)

    # read object id
    obj_id = apdu.objectIdentifier

    try:
        # get object
        obj = self.get_object_by_id(obj_id)

        if obj is None:
            # create error
            raise ExecutionError(errorClass='object', errorCode='unknownObject')

        # check if object is protected
        elif obj.objectName in self.protected_properties:
            # create error
            resp = Error(
                errorClass='object',
                errorCode='objectDeletionNotPermitted',
                context=apdu
            )

        else:
            # delete object from application
            self.delete_object(obj)

            # create response
            resp = SimpleAckPDU(context=apdu)

    except Exception as error:
        self._error(error)

        # create error
        resp = Error(errorClass='object', errorCode='internalError', context=apdu)

        # transmit response
        self.response(resp)

        # set result dict
        result_dict = {
            'error': True,
        }

        # return result dict
        return result_dict

    # return response
    return resp
