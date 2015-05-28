# pylint: disable=invalid-name, too-many-instance-attributes, broad-except

"""
Application Basic Module
------------------------

This module provides a basic BACpypes application object.
"""

from __future__ import absolute_import

from multiprocessing import Process
import random
import signal
import sys
from threading import Thread
import time

from bacpypes.appservice import StateMachineAccessPoint, ApplicationServiceAccessPoint
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import BIPSimple, AnnexJCodec, UDPMultiplexer

from bacpypes.comm import bind
from bacpypes.apdu import AbortPDU, Error, ErrorPDU, RejectPDU, SimpleAckPDU, ComplexAckPDU, APDU, \
    SubscribeCOVRequest, SubscribeCOVPropertyRequest, WhoIsRequest, WhoHasRequest, IAmRequest, \
    IHaveRequest
from bacpypes.pdu import Address, GlobalBroadcast

from bacpypes import core
from bacpypes.task import RecurringFunctionTask

from bacnet.debugging import ModuleLogger, bacnet_debug

from bacnet.system.managing import client_manager

from bacnet.console.creator import request_creator

from bacnet.object.hardware import discover_hardware_objects
from bacnet.object.primitivedata import RingDict

from .handler import HandlerApplication, restart_on_failure


# enabling logging
ModuleLogger()


# get all broadcast types
BROADCASTS = (
    Address.globalBroadcastAddr,
    Address.localBroadcastAddr,
    Address.remoteBroadcastAddr,
)


@bacnet_debug
def poll_hardware(application, obj_tuple):
    """
    This function polls hardware values.

    :param application: application object
    :param obj_tuple: object tuples
    :return: None
    """

    self = poll_hardware

    try:
        # loop through hardware objects
        for obj_id in obj_tuple:
            # get object
            obj = application.objectIdentifier.get(obj_id, None)

            # check if obj_id is defined
            if hasattr(obj, 'poll_hardware'):
                # update value
                obj.poll_hardware()

    except Exception as error:
        self._exception(error)


class BasicApplication(HandlerApplication, Process):
    # pylint: disable=broad-except, star-args, unused-argument, no-self-use, too-many-branches
    """
    This class describes a basic BACpypes application including simple functionality.
    """

    stdout = None

    def __init__(self, *args, **kwargs):
        """
        This function initializes the application object.

        :return: BasicApplication instance
        """

        self._debug('__init__ %r', args)

        # set stdout
        self.stdout = kwargs.pop('stdout', sys.stdout)

        # deactivate hardware poll
        self.deactivate_hardware_poll = kwargs.pop('deactivate_hardware_poll', False)

        # set environmental variables
        single = kwargs.pop('single', False)
        self.object_list = kwargs.pop('object_list', ())

        # call constructor of predecessor class
        HandlerApplication.__init__(self, *args, **kwargs)
        Process.__init__(self, name='app')

        # include an application decoder
        self.asap = ApplicationServiceAccessPoint()

        # pass the device object to a state machine access point
        self.smap = StateMachineAccessPoint(args[0])

        # add a network service access point
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)

        # bind the top layers
        bind(self, self.asap, self.smap, self.nsap)

        # create a generic BIP stack, bound to the Annex J server on the UDP multiplexer
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.localAddress)

        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)

        # bind the BIP stack to the network, no network number
        self.nsap.bind(self.bip)

        self.daemon = True

        if single and hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self.console_interrupt)

        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.shutdown)

        # get hardware
        self.known_hardware = discover_hardware_objects()

        # duplicate check
        self.request_dict = RingDict(500)
        self.response_dict = RingDict(500)

        # get manager
        self._manager = client_manager()

        # get log queue
        self.log = self._manager.log()

        # get required communication queues
        self.indication_queue = self._manager.Queue()
        self.requests = self._manager.app()
        self.config = self._manager.config()
        self.console = self._manager.console()
        self.webgui = self._manager.webgui()

        # predefine threads
        self.comm_thread = None
        self.update_thread = None
        self.indication_thread = None

        # set poll hardware dictionary
        self.poll_hardware_dict = {}

        # loop through hardware objects
        for obj_id, obj_dict in self.known_hardware.iteritems():
            # get poll
            poll = obj_dict.get('poll')

            # check if poll was set
            if isinstance(poll, (int, float)) and not isinstance(poll, bool):
                # add object identifier to poll hardware dictionary
                self.poll_hardware_dict[poll] = self.poll_hardware_dict.get(poll, ()) + (obj_id,)

        # start process
        self.start()

    @restart_on_failure
    def update_devices(self):
        """
        This function initiates who is requests periodically.

        :return: None
        """

        self._debug('running: device update thread')

        try:
            # create whois request
            request = WhoIsRequest()

            # set destination to global broadcast
            request.pduDestination = GlobalBroadcast()

            # set max identifier: 2^22 - 1 = 4.194.303
            max_id = 2 ** 22 - 1

            # set device count, 4096 => 1024 rounds to go
            count = 4096

            # set wait time for each whois cycle, 5 secs
            wait_time = 5

            # start at a random offset
            offset = random.randint(0, max_id / count) * count

            # subscription update cycle every 15 mins
            subscription_update = 15 * int(60.0 / wait_time)

            # wait for random startup time or next event
            self.update_devices_now.wait(random.random() * 15)

            # loop variable
            i = 1

            # do as long as the queue exists
            while hasattr(self.requests, 'put'):
                # set high limit
                high_limit = offset + count - 1

                # check if high limit is greater than max identifier
                if high_limit > max_id:
                    # set high limit to max identifier
                    high_limit = max_id

                # set instance limits
                request.deviceInstanceRangeLowLimit = offset
                request.deviceInstanceRangeHighLimit = high_limit

                self._debug('   - request: %s', request)

                # queue whois request
                self.requests.put(request)

                # check if subscriptions should be updated
                if i % subscription_update == 0:
                    # loop through remote devices
                    for subscriptions in self.remote_subscriptions.itervalues():
                        # loop through subscriptions
                        for subscription in subscriptions:
                            # check if subscription should be updated
                            if subscription['remaining'].remaining_time < 1200:
                                # create subscribe cov request
                                cov_request = request_creator(
                                    'subscribe %s %s' %
                                    (subscription['address'], subscription['renew'])
                                )

                                # queue cov request
                                self.requests.put(cov_request)

                                # remove cov request from scope
                                del cov_request

                # wait for 5 secs or next event => 1024 rounds * 5 secs = 85.33 mins
                self.update_devices_now.wait(wait_time)

                # change offset
                offset += count

                # update loop variable
                i += 1

                # check if offset must be reset
                if offset > max_id:
                    # reset offset
                    offset = 0

                    # reset loop variable
                    i = 0

                    # loop through known devices
                    for address, device in self.known_devices.items():
                        # check if device was last seen more than 90 mins ago
                        if 'last_seen' in device and time.time() - device['last_seen'] > 5400:
                            # remove device from known devices
                            del self.known_devices[address]

                        # check if last seen was not set or system clock reset
                        elif not 'last_seen' in device or time.time() < device['last_seen']:
                            # reset last seen
                            device['last_seen'] = time.time()

            # signal finishing was desired
            return True

        except Exception as error:
            self._exception(error)

        finally:
            self._debug('finished: device update thread')

    @restart_on_failure
    def check_queue(self):
        # pylint: disable=too-many-statements
        """
        This function checks for queued outgoing requests.

        :return: None
        """

        self._debug('running: comm thread')

        try:
            # handle request queue
            while hasattr(self.requests, 'get'):
                try:
                    # wait for request
                    apdu = self.requests.get()

                except (IOError, EOFError):
                    # broken pipe
                    continue

                except Exception as error:
                    self._exception(error)

                    continue

                # check if apdu is an apdu
                if not isinstance(apdu, APDU):
                    self._error('queued request is invalid: %r', apdu)

                    # go to next apdu
                    continue

                # no internal broadcast
                internal_broadcast = False

                # check if apdu is supposed to be processed locally
                if hasattr(apdu.pduDestination, 'addrIP') and apdu.pduDestination.addrIP == 0:
                    # get local address
                    local_address = apdu.pduDestination.addrTuple[1]

                    # internal broadcast
                    if local_address == 0:
                        internal_broadcast = True

                    # for app
                    elif local_address == 1:
                        self.indication(apdu)

                    # for config
                    elif local_address == 2 and hasattr(self.config, 'put'):
                        self.config.put(apdu)

                    # for console
                    elif local_address == 3 and hasattr(self.console, 'put'):
                        self.console.put(apdu)

                    # for webgui
                    elif local_address == 4 and hasattr(self.webgui, 'put'):
                        self.webgui.put(apdu)

                    # for nobody
                    elif local_address == 255:
                        continue

                    # destination unknown
                    else:
                        self._debug('unknown local destination: %r', apdu.pduDestination)

                else:
                    # check if message originated on this system
                    if apdu.pduSource is None or \
                        apdu.pduSource.addrAddr == self.localAddress.addrAddr or \
                        (hasattr(apdu.pduSource, 'addrIP') and apdu.pduSource.addrIP == 0):
                        # internal broadcast
                        internal_broadcast = True

                        # check if message is a response
                        if isinstance(apdu, (AbortPDU, RejectPDU, ErrorPDU, ComplexAckPDU,
                                             SimpleAckPDU)):
                            # transmit response
                            self.response(apdu)

                            # create message id
                            message_id = (
                                str(apdu.pduDestination),
                                False,
                                apdu.apduService,
                                (self.smap.nextInvokeID + 255) % 256,
                            )

                            # check for duplicate
                            if message_id[3] is not None and message_id in self.response_dict and \
                                abs(self.response_dict[message_id][1] - time.time()) < 15:
                                self._info('duplicate response found: %s', apdu)

                                # go to next apdu
                                continue

                            # append message id to response dict
                            self.response_dict[message_id] = (apdu, time.time())

                        else:
                            # transmit request
                            self.request(apdu)

                            if not isinstance(apdu, (WhoIsRequest, IAmRequest, WhoHasRequest,
                                                     IHaveRequest)):

                                # create message id
                                message_id = (
                                    str(apdu.pduDestination),
                                    False,
                                    apdu.apduService,
                                    (self.smap.nextInvokeID + 255) % 256,
                                )

                                # check for duplicate
                                if message_id[3] is not None and \
                                    message_id in self.request_dict and \
                                    abs(self.request_dict[message_id][1] - time.time()) < 15:
                                    self._info('duplicate request found: %s', apdu)

                                    # go to next apdu
                                    continue

                                # append message id to request dict
                                self.request_dict[message_id] = (apdu, time.time())

                    else:
                        # interpret request
                        self.indication_queue.put(apdu)

                # check if message is supposed to be broadcasted internally
                if internal_broadcast:
                    # send to processes
                    if hasattr(self.config, 'put'):
                        self.config.put(apdu)
                    if hasattr(self.console, 'put'):
                        self.console.put(apdu)
                    if hasattr(self.webgui, 'put'):
                        self.webgui.put(apdu)

            # signal finishing was desired
            return True

        except Exception as error:
            self._exception(error)

        finally:
            self._debug('finished: comm thread')

    @restart_on_failure
    def check_indication_queue(self):
        """
        This function checks for new packages to be indicated.

        :return: None
        """

        self._debug('running: indication thread')

        # check if hardware was defined and poll was not deactivated
        if any(self.poll_hardware_dict) and not self.deactivate_hardware_poll:
            # wait for core to initialize task manager
            while core.taskManager is None:
                # sleep for 0.1 seconds
                time.sleep(0.1)

            # loop through hardware polls
            for poll_time, obj_tuple in self.poll_hardware_dict.iteritems():
                # create task
                poll_task = RecurringFunctionTask(poll_time, poll_hardware, self, obj_tuple)

                # initialize hardware polling tasks
                core.taskManager.install_task(poll_task)

        try:

            while hasattr(self.indication_queue, 'get'):
                try:
                    # wait for request
                    apdu = self.indication_queue.get()

                except (IOError, EOFError):
                    # broken pipe
                    continue

                except Exception as error:
                    self._exception(error)

                    continue

                # check if apdu is an apdu
                if not isinstance(apdu, APDU):
                    self._error('queued request is invalid: %r', apdu)

                    # go to next apdu
                    continue

                # check if apdu is supposed to be processed locally
                if not hasattr(apdu.pduDestination, 'addrIP') or apdu.pduDestination.addrIP != 0:
                    # send to processes
                    if hasattr(self.config, 'put'):
                        self.config.put(apdu)
                    if hasattr(self.console, 'put'):
                        self.console.put(apdu)
                    if hasattr(self.webgui, 'put'):
                        self.webgui.put(apdu)

                    # check if message is a response
                    if isinstance(apdu, (AbortPDU, RejectPDU, ErrorPDU, ComplexAckPDU,
                                         SimpleAckPDU)):
                        # create message id
                        message_id = (
                            str(apdu.pduSource),
                            True,
                            apdu.apduService,
                            getattr(apdu, 'apduInvokeID', None),
                        )

                        # check for duplicate
                        if message_id[3] is not None and message_id in self.response_dict and \
                            abs(self.response_dict[message_id][1] - time.time()) < 15:
                            self._info('duplicate response found: %s', apdu)

                            # go to next apdu
                            continue

                        # append message id to response dict
                        self.response_dict[message_id] = (apdu, time.time())

                    else:
                        # create message id
                        message_id = (
                            str(apdu.pduSource),
                            True,
                            apdu.apduService,
                            getattr(apdu, 'apduInvokeID', None),
                        )

                        # check for duplicate
                        if message_id[3] is not None and message_id in self.request_dict and \
                            abs(self.request_dict[message_id][1] - time.time()) < 15:
                            self._info('duplicate request found: %s', apdu)

                            # go to next apdu
                            continue

                        # append message id to request dict
                        self.request_dict[message_id] = (apdu, time.time())

                # do indication
                self.do_indication(apdu)

        except Exception as error:
            self._exception(error)

        finally:
            self._debug('finished: indication thread')

    @restart_on_failure
    def run(self):
        """
        This function initiates processing.

        :return: None
        """

        self._debug('running as %r', self.pid)

        # populate application
        for obj in self.object_list:
            self.add_object(obj)

        # remove object list from application
        del self.object_list

        # start communication thread
        self.comm_thread = Thread(target=self.check_queue)
        self.comm_thread.setDaemon(True)
        self.comm_thread.start()

        # start update device thread
        self.update_thread = Thread(target=self.update_devices)
        self.update_thread.setDaemon(True)
        self.update_thread.start()

        # start update device thread
        self.indication_thread = Thread(target=self.check_indication_queue)
        self.indication_thread.setDaemon(True)
        self.indication_thread.start()

        try:
            # run BACpypes core
            core.run()

            # signal finishing was desired
            return True

        except Exception as error:
            self._exception('exception: %r', error)

        finally:
            self._debug('finished')

    def terminate(self):
        """
        This function terminates processing.

        :return: None
        """

        self._debug('terminate')

        # terminate process
        self._popen.terminate()

    def console_interrupt(self, *args):
        """
        This function is the catch for interrupts.

        :return: None
        """

        # check if this the forked process
        if self._popen is not None:

            self._debug('console_interrupt %r', args)

            self.stdout.write('keyboard interrupt\n')

            # print info
            self.terminate()

    def shutdown(self, *args):
        """
        This function shuts down the process.

        :return: None
        """

        self._debug('shutdown')

        # stop BACpypes core
        core.stop()

        # safe object deletion
        for obj in self.objectIdentifier.values():
            # check if object has safe deletion procedure
            if hasattr(obj, 'safe_delete'):
                # safe delete object
                obj.safe_delete()

    def add_object(self, obj):
        """
        This functions adds an object to the collection.

        :param obj: object
        :return: None
        """
        self._debug('add_object %r', obj)

        # read object name
        object_name = getattr(obj.objectName, 'value', obj.objectName)
        if not object_name:
            raise RuntimeError('object name required')

        # read object id
        object_identifier = getattr(obj.objectIdentifier, 'value', obj.objectIdentifier)

        # check if object id exists
        if not object_identifier:
            raise RuntimeError('object identifier required')

        # check if object name already exists in collection
        if object_name in self.objectName:
            raise RuntimeError('already an object with name "%s"' % object_name)

        # check if object id already exists in collection
        if self.objectIdentifier.get(object_identifier, None) is not None:
            raise RuntimeError('already an object with identifier %s' % object_identifier)

        # add object name and id to directories
        self.objectName[object_name] = obj
        self.objectIdentifier[object_identifier] = obj

        # check if object allowes application setting
        if hasattr(obj, 'set_application'):
            # set application
            obj.set_application(self)

        # get hardware dict
        hardware = self.known_hardware.get(object_identifier, {})

        # set hardware object
        obj._hardware = hardware.get('hardware', None)

        # check if hardware was defined
        if obj._hardware is not None:
            # loop through initials
            for prop_id, value in hardware.get('initials', {}).iteritems():
                # check if property was set already
                if not obj.ReadProperty(prop_id):
                    # set new value
                    obj.WriteProperty(prop_id, value, direct=True)

            # initialize present value
            obj.poll_hardware()

        # add object to collection
        self.localDevice.objectList.append(object_identifier)

    def delete_object(self, obj):
        """
        This function removes object from collection.

        :param obj: object
        :return: None
        """

        self._debug('delete_object %r', obj)

        # read object name and id
        object_name = obj.objectName
        object_identifier = obj.objectIdentifier

        # remove object from directories
        del self.objectName[object_name]
        del self.objectIdentifier[object_identifier]

        # remove object from collection
        index = self.localDevice.objectList.index(object_identifier)
        del self.localDevice.objectList[index]

    def iter_objects(self):
        """
        This function returns an iterator of the object collection.

        :return: object iterator
        """

        # return iterator
        return self.objectIdentifier.itervalues()

    def indication(self, apdu):
        """
        This function queues received requests.

        :param apdu: incoming message
        :return: None
        """

        # queue request
        self.indication_queue.put(apdu)

    def request(self, *args, **kwargs):
        """
        This function handles outgoing messages.

        :param apdu: outgoing message
        :return: None
        """

        # read apdu
        apdu = args[0]

        self._debug('request %r', apdu)

        # check if apdu is subscribe cov request
        if isinstance(apdu, (SubscribeCOVRequest, SubscribeCOVPropertyRequest)):
            # register subscription
            self.handle_remote_subscription(apdu)

        # forward the request
        HandlerApplication.request(self, *args, **kwargs)

    def response(self, *args, **kwargs):
        """
        This function handles outgoing messages as response to a request.

        :param apdu: outgoing message
        :return:
        """

        try:
            # call predecessor
            HandlerApplication.response(self, *args, **kwargs)

        except Exception as error:
            self._exception('exception: %r', error)

            # return the error to the sender
            if isinstance(args[0], (SimpleAckPDU, ComplexAckPDU)):
                resp = Error(errorClass='device', errorCode='operationalProblem', context=args[0])

                # transmit error
                self.response(resp)

    def confirmation(self, *args, **kwargs):
        """
        This function queues incoming messages.

        :param apdu: incoming message
        :return: None
        """

        # queue message
        self.requests.put(args[0])
