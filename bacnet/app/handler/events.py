# pylint: disable=invalid-name

"""
Event Handler Module
--------------------------

This module provides event handlers.
"""

from __future__ import absolute_import

from bacpypes.errors import ExecutionError

from bacpypes.apdu import SimpleAckPDU


def __do_SubscribeCOV(self, apdu):
    """
    This function reads data from request and returns response.

    :param apdu: incoming message
    :return: response
    """

    self._debug('__do_SubscribeCOV %r', apdu)

    # read object identifier
    obj_id = apdu.monitoredObjectIdentifier

    # get object
    obj = self.get_object_by_id(obj_id)

    # check if object exists
    if obj is None:
        raise ExecutionError(errorClass='object', errorCode='unknownObject')

    # initialize property
    prop = None

    # check if property identifier was provided
    if hasattr(apdu, 'monitoredPropertyIdentifier'):
        # read property identifier
        prop_id = apdu.monitoredPropertyIdentifier.propertyIdentifier

        # get property
        prop = obj.get_property(prop_id)

        # check if property exists
        if prop is None:
            raise ExecutionError(errorClass='property', errorCode='unknownProperty')

    self.add_cov_subscription(
        apdu,
        obj,
        prop=prop,
    )

    # create response
    resp = SimpleAckPDU(context=apdu)

    # return response
    return resp


def do_SubscribeCOVRequest(self, apdu):
    """
    This function reads data from request and returns response.

    :param apdu: incoming message
    :return: response
    """

    self._debug('do_SubscribeCOVRequest %r', apdu)

    # return response
    return __do_SubscribeCOV(self, apdu)


def do_SubscribeCOVPropertyRequest(self, apdu):
    """
    This function reads data from request and returns response.

    :param apdu: incoming message
    :return: response
    """

    self._debug('do_SubscribeCOVPropertyRequest %r', apdu)

    # return response
    return __do_SubscribeCOV(self, apdu)


def do_ConfirmedCOVNotificationRequest(self, apdu):
    """
    This function reads data from request and returns response.

    :param apdu: incoming message
    :return: response
    """

    self._debug('do_ConfirmedCOVNotificationRequest %r', apdu)

    # call handler
    self.receive_remote_notification(apdu)

    # create response
    resp = SimpleAckPDU(context=apdu)

    # return response
    return resp


def do_UnconfirmedCOVNotificationRequest(self, apdu):
    """
    This function reads data from request.

    :param apdu: incoming message
    :return: None
    """

    self._debug('do_UnconfirmedCOVNotificationRequest %r', apdu)

    # call handler
    self.receive_remote_notification(apdu)

    return None


def do_ConfirmedEventNotificationRequest(self, apdu):
    """
    This function reads data from request and returns response.

    :param apdu: incoming message
    :return: None
    """

    self._debug('do_ConfirmedEventNotificationRequest %r', apdu)

    raise RuntimeError('not yet supported')


def do_UnconfirmedEventNotificationRequest(self, apdu):
    """
    This function reads data from request and returns response.

    :param apdu: incoming message
    :return: None
    """

    self._debug('do_UnconfirmedEventNotificationRequest %r', apdu)

    raise RuntimeError('not yet supported')


def do_GetEventInformationRequest(self, apdu):
    """
    This function reads data from request and returns response.

    :param apdu: incoming message
    :return: None
    """

    self._debug('do_GetEventInformationRequest %r', apdu)

    raise RuntimeError('not yet supported')
