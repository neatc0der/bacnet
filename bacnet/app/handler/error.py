# pylint: disable=invalid-name

"""
Error Module
--------------------------

This module provides error handlers.
"""

from __future__ import absolute_import

import copy

from bacpypes.apdu import SubscribeCOVPropertyRequest, SubscribeCOVRequest


def do_AbortPDU(self, apdu):
    """
    This function handles abortions.

    :param apdu: incoming message
    :return: None
    """

    initiators = ()

    # loop through all request message ids
    for message_id, message in self.request_dict.iteritems():
        # check if source and invoke id are identical
        if message_id[0] == str(apdu.pduSource) and message_id[3] == apdu.apduInvokeID:
            # set initiator
            initiators += (message_id,)

    # check if initiators were found
    if not any(initiators):
        return

    # loop through initiators
    for initiator in initiators:
        # get aborted message
        message = self.request_dict[initiator]

        # check if message was subscription
        if isinstance(message, (SubscribeCOVPropertyRequest, SubscribeCOVRequest)):
            # copy message
            altered_apdu = copy.copy(message)

            # set life time to zero = remove subscription
            altered_apdu.lifetime = 0

            # remove subscription
            self.handle_remote_subscription(altered_apdu)

            # remove altered message
            del altered_apdu


def do_RejectPDU(self, apdu):
    """
    This function handles rejections.

    :param apdu: incoming message
    :return: None
    """

    initiators = ()

    # create message id
    message_id = (str(apdu.pduSource), False, apdu.apduService, apdu.apduInvokeID)

    # check if message was stored in ring buffer
    if message_id in self.request_dict:
        # set initiator
        initiators += (message_id,)

    # check if initiators were found
    if not any(initiators):
        return

    # loop through initiators
    for initiator in initiators:
        # get aborted message
        message = self.request_dict[initiator]

        # check if message was subscription
        if isinstance(message, (SubscribeCOVPropertyRequest, SubscribeCOVRequest)):
            # copy message
            altered_apdu = copy.copy(message)

            # set life time to zero = remove subscription
            altered_apdu.lifetime = 0

            # remove subscription
            self.handle_remote_subscription(altered_apdu)

            # remove altered message
            del altered_apdu


def do_Error(self, apdu):
    # pylint: disable=unused-argument
    """
    This function handles rejections.

    :param apdu: incoming message
    :return: None
    """

    # got Error, but ErrorPDU is required for full error handling - service, type, etc. missing!

    return
