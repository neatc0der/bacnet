# pylint: disable=invalid-name, star-args, too-many-locals, too-many-lines, broad-except

"""
Application Handler Module
--------------------------

This module provides handler for communication callbacks.
"""

from __future__ import absolute_import

from threading import Event
import time

from bacpypes.errors import ExecutionError

from bacpypes.basetypes import DeviceAddress, Recipient, RecipientProcess

from bacpypes.app import Application as BACpypesApplication

from bacpypes.pdu import Address
from bacpypes.apdu import ConfirmedCOVNotificationRequest, UnconfirmedCOVNotificationRequest, \
    WhoIsRequest, RejectReason, ConfirmedRequestPDU, Error, RejectPDU

from bacnet.debugging import bacnet_debug, ModuleLogger

from bacnet.app.handler.simple import property_to_result

from bacnet.console.parser import response_parser

from bacnet.object.primitivedata import COVSubscription, ObjectPropertyReference, Remaining

from .simple import do_IAmRequest, do_WhoIsRequest, do_IHaveRequest, do_WhoHasRequest, \
    do_ReadPropertyMultipleRequest, do_WritePropertyMultipleRequest, do_ReadPropertyRequest, \
    do_WritePropertyRequest
from .fileaccess import do_AtomicReadFileRequest, do_AtomicWriteFileRequest
from .objects import do_CreateObjectRequest, do_DeleteObjectRequest
from .events import do_ConfirmedCOVNotificationRequest, do_UnconfirmedCOVNotificationRequest, \
    do_SubscribeCOVRequest, do_SubscribeCOVPropertyRequest
from .error import do_AbortPDU, do_RejectPDU, do_Error


# enable logging
ModuleLogger()


def restart_on_failure(func=None, retries=3, fail_time=1):
    # pylint: disable=unused-argument
    """
    This function is a decorator for thread functions to restart after failure
    :param func: function reference
    :param retries: restart count within fail time
    :param fail_time: time between failures to count retries
    :return: updated function
    """

    def wrapper(obj):
        """
        This function is a decorator wrapper.

        :param obj: function
        :return: updated function
        """

        def inner(self, *args, **kwargs):
            """
            This function is the actual wrapper of the function call.
            """

            # initialize counter
            tries = 0

            # restart until limit is reached
            while tries <= retries:
                # get current time
                last_time = time.time()

                # start function
                finished = func(self, *args, **kwargs)

                # check if function finished
                if not finished in (False, None):
                    return finished

                # check if time in between was below the limit to count
                if time.time() < last_time or time.time() - last_time < fail_time:
                    # count try
                    tries += 1

                else:
                    # reset tries to 1
                    tries = 1

            return False

        # return function
        return inner

    # return wrapper
    if func is None:
        return wrapper

    return wrapper(func)


def lock_subscriptions(func=None, block=True, retries=3, sleep=0.05):
    """
    This function is a decorator for functions to lock subscriptions during execution.

    :param func: function reference
    :param block: wait until lock is acquired
    :param retries: retry count if not block
    :param sleep: sleep time in secs if not block
    :return: updated function
    """

    def wrapper(obj):
        """
        This function is a decorator wrapper.

        :param obj: function
        :return: updated function
        """

        def inner(self, *args, **kwargs):
            """
            This function is the actual wrapper of the function call.
            """

            tries = 0
            if 'tries' in kwargs:
                del kwargs['tries']

            # check if too many retries
            if tries > retries:
                return None

            # get active cov subscription property
            active_cov_subscriptions_property = self.localDevice.get_property(
                'activeCovSubscriptions'
            )

            # acquire lock
            if active_cov_subscriptions_property.lock.acquire(block):

                try:
                    # get active subscriptions
                    active_subscriptions = self.localDevice.ReadProperty(
                        'activeCovSubscriptions',
                        dictionary=True
                    )

                    # cast sequence of subscriptions to list
                    if active_subscriptions is None:
                        active_subscriptions = dict()

                    else:
                        active_subscriptions = active_subscriptions

                    kwargs['active_subscriptions'] = active_subscriptions

                    # call function
                    result = obj(self, *args, **kwargs)

                finally:
                    # release lock
                    active_cov_subscriptions_property.lock.release()

                # return result
                return result

            # sleep
            time.sleep(sleep)

            # retry
            return inner(self, *args, tries=tries+1, **kwargs)

        # return function
        return inner

    if func is None:
        return wrapper

    return wrapper(func)


@bacnet_debug(formatter='%(levelname)s:app: %(message)s')
class HandlerApplication(BACpypesApplication):
    # pylint: disable=abstract-method, too-many-instance-attributes, too-many-arguments
    """
    This class provides handler functionality for basic requests.
    """

    def __init__(self, *args, **kwargs):
        """
        This function constructs the application object.

        :return: BasicApplication instance
        """

        # call constructor of predecessor class
        BACpypesApplication.__init__(self, *args, **kwargs)

        # reset protected properties
        self.protected_properties = (
            # device itself
            self.objectName.keys()[0],

            # python program
            'configuration',

            # program control
            'control',
        )

        # initialize device dictionary
        self.known_devices = {}

        # initialize remote subscriptions
        self.remote_subscriptions = {}

        # set event
        self.update_devices_now = Event()

    def get_object_by_id(self, obj_id):
        """
        This function returns object by id.

        :param obj_id: object id
        :return: object
        """

        # return object
        return self.objectIdentifier.get(obj_id, None)

    def get_object_by_name(self, obj_name):
        """
        This function returns object by name.

        :param obj_name: object name
        :return: object
        """

        # return object
        return self.objectName.get(obj_name, None)

    def get_object_id(self, obj_type):
        """
        This function provides a unique object id.

        :param obj_type: object type
        :return: object id
        """

        # read object ids
        obj_ids = sorted(tuple(
            obj_id[1] for obj_id in self.objectIdentifier.iterkeys() if obj_id[0] == obj_type
        ))

        # initialize object id
        obj_id = 1

        # loop through object ids to found an unused one
        for used_id in obj_ids:

            # set object id
            obj_id = used_id + 1

            # check if object id is in use
            if not obj_id in obj_ids:
                break

        # store sorted object ids
        self.objectIdentifier[(obj_type, obj_id)] = None

        # return object id
        return obj_id

    @lock_subscriptions(block=False)
    def check_subscription_updates(self, apdu, active_subscriptions=None):
        """
        This function updates subscriptions with device id if needed.

        :param apdu: incoming i am request
        :param active_subscriptions: dictionary of active cov subscriptions
        :return: None
        """

        # read address
        address = str(apdu.pduSource)

        # get device identifier
        update_device_id = apdu.iAmDeviceIdentifier

        # loop through subscription lists
        for device_id in (None, update_device_id):

            # get subscriptions
            subscriptions = active_subscriptions.get(device_id, [])

            # check if address is in update list
            if address in subscriptions:
                # loop through subscriptions
                for i in range(len(subscriptions)):
                    # get subscription
                    subscription = subscriptions[i]

                    # check if address is equal
                    if str(subscription.recipient.recipient.address.macAddress) == address:
                        # update device identifier
                        subscription.recipient.recipient.device = device_id

                        # store subscription
                        subscriptions[i] = subscription

                # store subscriptions
                active_subscriptions[device_id] = subscriptions

        # store new active subscriptions
        self.localDevice.WriteProperty(
            'activeCovSubscriptions',
            active_subscriptions,
            direct=True
        )

    def get_device(self, address):
        """
        This function returns device identifier if known.

        :param address: device address
        :return: device identifier
        """

        # check if address is known
        if not 'id' in self.known_devices.get(address, {}):
            # create request
            request = WhoIsRequest()

            # set destination to address
            request.pduDestination = Address(address)

            self._debug('   - request: %s', request)

            # queue request
            self.requests.put(request)

            # exit
            return

        # get device
        device = self.known_devices[address]

        # return device
        return device['id']

    def send_cov_notification(self, subscription, values):
        """
        This function transmits cov notifications for subscriptions

        :param subscription: subscription
        :param values: sequence of property values
        :return: None
        """

        try:
            # initialize request type
            request_type = UnconfirmedCOVNotificationRequest

            # check if request must be confirmed
            if subscription.issueConfirmedNotifications:
                # reset request type
                request_type = ConfirmedCOVNotificationRequest

            # get device identifier from address
            device_id = self.localDevice.ReadProperty('objectIdentifier')

            # create request
            request = request_type(
                subscriberProcessIdentifier=subscription.recipient.processIdentifier,
                initiatingDeviceIdentifier=device_id,
                monitoredObjectIdentifier=subscription.monitoredPropertyReference.objectIdentifier.\
                                          get_tuple(),
                timeRemaining=subscription.timeRemaining.remaining_time,
                listOfValues=values,
            )

            # set destination
            request.pduDestination = Address(subscription.recipient.recipient.address.macAddress)

            self._debug('   - request: %s', request)

            # queue request
            self.requests.put(request)

        except Exception as error:
            self._exception(error)

    @lock_subscriptions
    def delete_cov_subscriptions(self, subscriptions,
                                 inform_object=True, active_subscriptions=None):
        """
        This function removes a list of subscriptions from the cov subscription list.

        :param subscriptions: subscription list
        :param inform_object: inform object
        :param active_subscriptions: dictionary of active cov subscriptions
        :return: None
        """

        # loop through subscriptions
        for subscription in subscriptions:
            # check if object must be informed
            if inform_object:
                # read object identifier
                obj_id = subscription.monitoredPropertyReference.objectIdentifier

                # get object by identifier
                obj = self.get_object_by_id(obj_id)

                # delete subscription
                obj.delete_cov_subscription(subscription, inform_app=False)

            # read device identifier
            device_id = subscription.recipient.recipient.device

            # get device subscriptions
            device_subscriptions = active_subscriptions.get(device_id, [])

            # delete subscription from list
            if subscription in device_subscriptions:
                device_subscriptions.remove(subscription)
                active_subscriptions[device_id] = device_subscriptions

                if not any(device_subscriptions):
                    del active_subscriptions[device_id]

        # store new active subscriptions
        self.localDevice.WriteProperty('activeCovSubscriptions', active_subscriptions, direct=True)

    @lock_subscriptions
    def delete_cov_subscription(self, apdu, obj,
                                prop=None, prop_index=None, active_subscriptions=None):
        """
        This function deletes subscription from cov subscription list.

        :param apdu: incoming message
        :param obj: object
        :param prop: property
        :param active_subscriptions: dictionary of active cov subscriptions
        :return: None
        """

        # read subscriber
        subscriber = apdu.subscriberProcessIdentifier

        # read object identifier
        obj_id = obj.ReadProperty('objectIdentifier')

        # initialize loop variable
        i = 0

        # get device identifier from address
        device_ids = self.get_device(str(apdu.pduSource))

        if device_ids is None:
            device_ids = active_subscriptions.keys()

        else:
            device_ids = (device_ids,)

        # loop through device ids
        for device_id in device_ids:
            # get device subscriptions
            device_subscriptions = active_subscriptions.get(device_id, [])

            # loop through subscriptions
            while i < len(device_subscriptions):
                # get subscription
                subscription = device_subscriptions[i]

                # read recipient
                recipient = subscription.recipient.recipient

                # check if recipient matches
                recipient_match = subscription.recipient.device == subscriber and \
                                  str(recipient.address.macAddress) == str(apdu.pduSource)
                                  # recipient.address.networkNumber == apdu.pduSource.addrNet

                # check if subscription is matching
                if recipient_match:

                    # read property reference
                    prop_ref = subscription.monitoredPropertyReference

                    # check if object matches
                    obj_match = prop_ref.objectIdentifier == obj_id

                    # check if property matches
                    prop_match = prop_ref.propertyIdentifier == prop.identifier and \
                                 prop_ref.propertyArrayIndex == prop_index

                    # check if object is matching
                    if obj_match and prop_match:

                        # remove subscription from object
                        obj.delete_cov_subscription(subscription)

                        # remove index from active subscriptions
                        del device_subscriptions[i]

                        # store device subscriptions in active subscriptions
                        active_subscriptions[device_id] = device_subscriptions

                        if not any(device_subscriptions):
                            del active_subscriptions[device_id]

                        continue

                # go to next subscription
                i += 1

        # store new active subscriptions
        self.localDevice.WriteProperty('activeCovSubscriptions', active_subscriptions, direct=True)

    @lock_subscriptions
    def renew_cov_subscription(self, subscription, obj, active_subscriptions=None):
        """
        This function checks if subscription can be renewed and returns boolean of this action.

        :param subscription: subscription
        :param obj: object
        :param active_subscriptions: dictionary of active cov subscriptions
        :return: subscription renewed
        """

        # initialize result
        renewed = False

        # read device identifier
        device_id = str(subscription.recipient.recipient.device)

        # read device subscriptions
        device_subscriptions = active_subscriptions.get(str(device_id), [])

        # loop through all device subscriptions
        for i in range(len(device_subscriptions)):
            # get entry
            entry = device_subscriptions[i]

            # check if device and process id match
            if entry.recipient.recipient.device == subscription.recipient.recipient.device and \
                entry.recipient.processIdentifier == subscription.recipient.processIdentifier:
                # check if objects and properties match

                if entry.monitoredPropertyReference.objectIdentifier == \
                        subscription.monitoredPropertyReference.objectIdentifier and \
                    entry.monitoredPropertyReference.propertyIdentifier == \
                        subscription.monitoredPropertyReference.propertyIdentifier and \
                    entry.monitoredPropertyReference.propertyArrayIndex == \
                        subscription.monitoredPropertyReference.propertyArrayIndex:

                    # store new subscription
                    device_subscriptions[i] = subscription
                    active_subscriptions[device_id] = device_subscriptions

                    # renew subscription in object
                    obj.renew_cov_subscription(subscription)

                    # store new active subscriptions
                    self.localDevice.WriteProperty(
                        'activeCovSubscriptions',
                        active_subscriptions,
                        direct=True
                    )

                    # set result
                    renewed = True

                    # break loop
                    break

        # check if subscription was renewed
        if not renewed:
            # append new subscription
            device_subscriptions.append(subscription)
            active_subscriptions[device_id] = device_subscriptions

            # add subscription to object
            obj.add_cov_subscription(subscription)

            # store new active subscriptions
            self.localDevice.WriteProperty(
                'activeCovSubscriptions',
                active_subscriptions,
                direct=True
            )

        # return result
        return renewed

    def add_cov_subscription(self, apdu, obj, prop=None):
        """
        This function adds subscription to cov subscription list.

        :param apdu: incoming message
        :param obj: object
        :param prop: property
        :return: None
        """

        # initialize cov increment and property array index
        cov_inc = None
        prop_index = None

        # check if object supports cov notification
        if not obj.cov_supported():
            raise ExecutionError(
                errorClass='object',
                errorCode='optionalFunctionalityNotSupported'
            )

        # check if property was defined
        if prop is not None:
            # check if property supports cov notification
            if not obj.cov_supported(prop):
                raise ExecutionError(
                    errorClass='property',
                    errorCode='optionalFunctionalityNotSupported'
                )

            # read cov increment
            cov_inc = apdu.covIncrement

            # read property array index
            prop_index = apdu.monitoredPropertyIdentifier.propertyArrayIndex

        # read life time
        lifetime = apdu.lifetime

        # check if life time out of range
        if False:
            raise ExecutionError(errorClass='services', errorCode='valueOutOfRange')

        # check if activeCovSubscription is full
        if False:
            raise ExecutionError(errorClass='resources', errorCode='noSpaceToAddListElement')

        # read if requests should be confirmed
        confirmed = bool(apdu.issueConfirmedNotifications)

        # check if subscription was canceled
        if confirmed and lifetime is None:
            # delete subscription
            return self.delete_cov_subscription(apdu, obj, prop=prop, prop_index=prop_index)

        # read subscriber
        subscriber = apdu.subscriberProcessIdentifier

        # read address
        address = str(apdu.pduSource)

        # get device identifier from address
        device_id = self.get_device(address)

        # create subscription
        subscription = COVSubscription(
            recipient=RecipientProcess(
                recipient=Recipient(
                    device=device_id,
                    address=DeviceAddress(
                        # TODO: distinguish between local and remote, 0 == local
                        networkNumber=0,
                        macAddress=address,
                    ),
                ),
                processIdentifier=subscriber,
            ),
            monitoredPropertyReference=ObjectPropertyReference(
                objectIdentifier=obj.ReadProperty('objectIdentifier'),
                propertyIdentifier=None,
                propertyArrayIndex=None,
            ),
            issueConfirmedNotifications=confirmed,
            timeRemaining=Remaining(lifetime),
            covIncrement=cov_inc,
        )

        # check if property is defined
        if prop is not None:
            # set property identifier and array index
            subscription.monitoredPropertyReference.propertyIdentifier = prop.identifier
            subscription.monitoredPropertyReference.propertyArrayIndex = prop_index

        self.renew_cov_subscription(subscription, obj)

    @staticmethod
    def __get_remote_subscription_index(subscriptions, subscription):
        """
        This function looks for the provided subscription

        :param subscriptions: list of subscriptions
        :param subscription: subscription(s)
        :return: subscription index(es)
        """

        if not isinstance(subscription, (tuple, list)):
            subscription = (subscription,)

        result = [None] * len(subscription)

        # loop through all existing subscriptions
        for i in range(len(subscriptions)):
            # get subscription
            entry = subscriptions[i]

            # loop through single subscriptions
            for j in range(len(subscription)):
                # get single subscription
                single_subscription = subscription[j]

                subscription_exists = True

                # loop through subscription keys
                for key, value in single_subscription.iteritems():
                    # ignore remote address and remaining lifetime - might change during runtime
                    if key in ['address', 'remaining', 'renew']:
                        continue

                    # check if subscription exists
                    if entry[key] != value:
                        subscription_exists = False

                        # break loop
                        break

                # check if subscription was found
                if subscription_exists:
                    # return index
                    result[j] = i

                    # break loop
                    break

            # check if all single subscriptions were found
            if not None in result:
                # break loop
                break

        if len(result) == 1:
            result = result[0]

        # return result
        return result

    def handle_remote_subscription(self, apdu):
        """
        This function stores a new remote subscription.

        :param apdu: outgoing request
        :return: None
        """

        # get device id
        device_id = self.get_device(str(apdu.pduDestination))

        # get parsed data
        parsed_data = response_parser(apdu)

        # read lifetime
        lifetime = parsed_data['content']['object']

        # create new subscription
        new_subscription = {
            'address': parsed_data['destination'],
            'property': None,
            'index': None,
        }
        new_subscription.update(parsed_data['content'])

        remove_subscription = not lifetime > 0

        # get subscriptions
        subscriptions = self.remote_subscriptions.get(device_id, [])

        subscription_index = self.__get_remote_subscription_index(subscriptions, new_subscription)

        # check if subscription was found
        if subscription_index is not None:
            # check if subscription is supposed to be removed
            if remove_subscription:
                # remove subscription
                del subscriptions[subscription_index]

            else:
                # update subscription
                subscriptions[subscription_index] = new_subscription

        # check if subscription exists
        elif not subscription_index and not remove_subscription:
            subscriptions.append(new_subscription)

        # store subscriptions
        self.remote_subscriptions[device_id] = subscriptions

    def receive_remote_notification(self, apdu):
        """
        This function checks if the cov notification was initiated correctly.

        :param apdu: incoming message
        :return: remote subscription exists
        """

        # TODO: handle received cov notification
        pass

    def check_remote_subscription_updates(self, apdu):
        """
        This function checks if the cov notification was initiated correctly.

        :param apdu: incoming message
        :return: remote subscription exists
        """

        # get subscriptions
        subscriptions = self.remote_subscriptions.get(None, [])

        i = 0

        # loop through subscriptions
        while i < len(subscriptions):
            # get subscription
            subscription = subscriptions[i]

            # check if address matches
            if subscription['address'] == str(apdu.pduSource):
                # get actual device identifier
                device_id = self.get_device(str(apdu.pduSource))

                # check if device identifier was found
                if device_id is not None:
                    # get list of remote subscriptions
                    remote_subscriptions = self.remote_subscriptions.get(device_id, [])

                    # append subscription to appropriate device identifier
                    remote_subscriptions.append(subscription)

                    # store new remote subscriptions
                    self.remote_subscriptions[device_id] = remote_subscriptions

                    # remove subscription from unknown device identifier list
                    del subscriptions[i]

                    # go to next subscription
                    continue

            i += 1

        # store subscriptions
        self.remote_subscriptions[None] = subscriptions

    def do_indication(self, apdu):
        """
        This function initiates appropriate function call for a received request.

        :param apdu: incoming message
        :return: None
        """

        self._debug('indication %r', apdu)

        # get helper function by name
        helper_name = "do_%s" % apdu.__class__.__name__
        helper_func = getattr(self, helper_name, None)

        self._debug('   - helper_func: %r', helper_func)

        # update last seen
        device = self.known_devices.get(str(apdu.pduSource), {})
        device['last_seen'] = time.time()
        self.known_devices[str(apdu.pduSource)] = device
        del device

        # reject messages for unrecognized services
        if not helper_func:
            rejected = isinstance(apdu, ConfirmedRequestPDU)

            # send rejection in case confirmation needed
            if rejected:
                resp = RejectPDU(
                    apdu.apduInvokeID,
                    RejectReason.UNRECOGNIZEDSERVICE,
                    context=apdu
                )
                self.requests.put(resp)
            return

        try:
            # call helper function
            resp = helper_func(apdu)

            # queue response
            if resp is not None:
                self._debug('   - resp: %r', resp)

                # queue response
                self.requests.put(resp)

        except ExecutionError as error:
            self._debug('   - execution error: %r', error)

            # return the error to the sender
            if isinstance(apdu, ConfirmedRequestPDU):
                resp = Error(errorClass=error.errorClass, errorCode=error.errorCode, context=apdu)

                # queue error
                self.requests.put(resp)

        except Exception as error:
            self._exception('exception: %r', error)

            # return the error to the sender
            if isinstance(apdu, ConfirmedRequestPDU):
                resp = Error(errorClass='device', errorCode='operationalProblem', context=apdu)

                # queue error
                self.requests.put(resp)


# loop through all global objects
for name, reference in globals().items():
    # check if object is a request
    if name.startswith('do_'):
        # assign method to class
        setattr(HandlerApplication, name, reference)
