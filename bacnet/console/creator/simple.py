# pylint: disable=unused-argument, star-args

"""
Simple Handler Module
---------------------

This module contains rudimentary request functions.
"""

from bacnet.object import get_object_class, get_datatype

from bacpypes.constructeddata import Array, Any
from bacpypes.primitivedata import Atomic, Null, Integer, Real

from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.apdu import PropertyIdentifier, PropertyReference, ReadAccessSpecification, \
    ReadPropertyMultipleRequest, WriteAccessSpecification, WritePropertyMultipleRequest, \
    PropertyValue, WhoIsRequest, IAmRequest, WhoHasRequest, IHaveRequest, WhoHasObject, \
    WhoHasLimits

from bacnet.debugging import bacnet_debug, ModuleLogger

from bacnet.object import ObjectIdentifier
from bacnet.object.primitivedata import Unsigned


# enable logging
ModuleLogger()


@bacnet_debug
def cast_value(value, data_type, prop_index=None, prop=None):
    # pylint: disable=too-many-branches
    """
    This function casts value to data type.

    :param value: object
    :param data_type: data type
    :param prop_index: property array index
    :param prop: property instance
    :return: casted value
    """

    cast_value._debug('start %r, %r, %r, %r', value, data_type, prop_index, prop)

    # get value from value
    if not hasattr(data_type, 'subtype') or isinstance(value, ObjectIdentifier):
        value = getattr(value, 'value', value)

    # cast value
    if value == 'null':
        value = Null()

    elif issubclass(data_type, Atomic):
        if data_type is Integer:
            if value is None:
                value = 0

            value = int(value)

        elif data_type is Real:
            if value is None:
                value = 0

            value = float(value)

        elif data_type is Unsigned:
            if value is None:
                value = 0

            value = int(value)

        elif (data_type is ObjectIdentifier) and (isinstance(value, basestring)):
            value = value.split()
            value[1] = int(value[1])
            value = tuple(value)

        value = data_type(value)

    elif issubclass(data_type, Array) and (prop_index is not None):

        if prop_index == 0:
            if isinstance(value, basestring) and not value.isdigit():
                raise ValueError('array size must be integer')

            value = Unsigned(value)

        elif issubclass(data_type.subtype, Atomic):
            value = cast_value(value, data_type.subtype, prop_index, prop=prop)

        elif not isinstance(value, data_type.subtype):
            raise TypeError(
                'invalid result datatype, expecting %s and got %s' %
                (data_type.subtype.__name__, type(value).__name__)
            )

    elif not isinstance(value, data_type) and value is not None:
        # check if value exists or property is optional
        if value is not None or prop is None or (prop is not None and not prop.optional):
            raise TypeError(
                'invalid result datatype, expecting %s and got %s' %
                (data_type.__name__, type(value).__name__)
            )

    # return casted value
    return value


def __retrieve_prop_list(args, obj_type, i, write=False):
    """
    This private function retrieves the property reference list.

    :param args: list of parameters
    :param obj_type: object type
    :param i: parameter position
    :param write: specify if a read or write request is supposed to be created
    :return: access specification list
    """

    prop_reference_list = []

    while i < len(args):
        # read property id
        prop_id = args[i]

        # check if property exists
        if prop_id not in PropertyIdentifier.enumerations:
            break

        i += 1

        data_type = None

        # check if property id was generalization
        if prop_id not in ('all', 'required', 'optional'):
            # read data type
            data_type = get_datatype(obj_type, prop_id)

            # check if data type was set
            if not data_type:
                raise ValueError('invalid property for this object type')

        # check if specific property id is needed
        elif write:
            raise ValueError('provide specific property')

        # initialize property parameters
        prop_reference_dict = {
            'propertyIdentifier': prop_id,
        }

        # read value
        if write:
            # check if value was set
            if i >= len(args):
                raise ValueError('property value is not declared')

            value = args[i]
            i += 1

        # check if array index was set
        if (i < len(args)) and (args[i].isdigit()):
            # read array index
            prop_reference_dict['propertyArrayIndex'] = int(args[i])
            i += 1

            # check if priority was set
            if write and (i < len(args)) and args[i].isdigit():
                # read priority
                prop_reference_dict['priority'] = int(args[i])
                i += 1

        # check if property data type is array
        elif data_type is not None and issubclass(data_type, Array):
            raise ValueError('property index is required for arrays')

        # build a property reference
        if write:

            # cast value
            value = cast_value(
                value,
                data_type,
                prop_reference_dict.get('propertyArrayIndex', None)
            )

            prop_reference = PropertyValue(**prop_reference_dict)
            prop_reference.value = Any()
            prop_reference.value.cast_in(value)

        else:
            prop_reference = PropertyReference(**prop_reference_dict)

        # add property to property list
        prop_reference_list.append(prop_reference)

    # return property reference list and i
    return prop_reference_list, i


def __retrieve_access_list(args, write=False):
    """
    This private function retrieves the access specification list.

    :param args: list of parameters
    :param write: specify if a read or write request is supposed to be created
    :return: access specification list
    """

    access_spec_list = []
    i = 1

    while i < len(args):
        # read object type
        obj_type = args[i]
        i += 1

        # check if object type is correct
        if obj_type.isdigit():
            obj_type = int(obj_type)

        elif not get_object_class(obj_type):
            raise ValueError('unknown object type')

        # check if object instance is defined
        if i >= len(args):
            raise ValueError('object instance was not declared')

        # check if object instance is correct
        obj_inst = args[i]
        if not obj_inst.isdigit():
            raise ValueError('object instance must be an integer')

        obj_inst = int(obj_inst)
        i += 1

        prop_reference_list, i = __retrieve_prop_list(args, obj_type, i, write)

        # check if properties were specified
        if not prop_reference_list:
            raise ValueError('provide at least one property')

        access_spec_dict = {
            'objectIdentifier': (obj_type, obj_inst),
            'listOfPropertyReferences': prop_reference_list,
        }

        # build an access specification
        if write:
            access_spec_dict['listOfProperties'] = access_spec_dict['listOfPropertyReferences']
            del access_spec_dict['listOfPropertyReferences']
            access_spec = WriteAccessSpecification(**access_spec_dict)
        else:
            access_spec = ReadAccessSpecification(**access_spec_dict)

        # add access specification to access specification list
        access_spec_list.append(access_spec)

    # return access specification list
    return access_spec_list


def __read_write_multiple_request(args, write=False):
    """
    This function creates a read/write request for multiple objects.

    :param args: list of parameters
    :param write: specify if a read or write request is supposed to be created
    :return: request
    """

    # check if arguments are specified
    if len(args) == 0:
        raise ValueError('destination address was not declared')

    # read address
    addr = args[0]

    # retrieve access specification list from arguments
    access_spec_list = __retrieve_access_list(args, write)

    # check if read accesses were specified
    if not access_spec_list:
        raise RuntimeError('provide at least one access specification')

    # build the request
    if write:
        request = WritePropertyMultipleRequest(listOfWriteAccessSpecs=access_spec_list)
    else:
        request = ReadPropertyMultipleRequest(listOfReadAccessSpecs=access_spec_list)

    # set destination address
    request.pduDestination = Address(addr)

    # return created request
    return request


def read_request(args, console=None):
    """
    This function creates a read request for multiple objects.

    Usage: read <address> ( <type> <instance> ( <property> [ <index> ] )+ ... )+ ...

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    return __read_write_multiple_request(args, write=False)


def write_request(args, console=None):
    """
    This function creates a write request for multiple objects.

    Usage: write <address> ( <type> <instance> ( <property> <value> [ <index> [ <priority> ] ] )+ \
... )+ ...

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    return __read_write_multiple_request(args, write=True)


def whois_request(args, console=None):
    """
    This function creates a whois request.

    Usage: whois [ <address> ] [ <lowlimit> <highlimit> ]

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # create request
    request = WhoIsRequest()

    # check if address was set
    if len(args) in (1, 3):
        request.pduDestination = Address(args[0])
        del args[0]

    # send broadcast otherwise
    else:
        request.pduDestination = GlobalBroadcast()

    # check if limits were set
    if len(args) == 2:
        request.deviceInstanceRangeLowLimit = int(args[0])
        request.deviceInstanceRangeHighLimit = int(args[0])

    # return created request
    return request


def iam_request(args, console=None):
    """
    This function creates a iam request.

    Usage: iam [ <address> ]

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if console was provided
    if console is None:
        raise ValueError('console not found')

    address = None

    # check if too many arguments are defined
    if len(args) > 1:
        raise ValueError('too many arguments')

    elif len(args) == 1:
        # read address
        address = args[0]

    # create request
    request = IAmRequest()

    # check if address was specified
    if address is None:

        # send broadcast
        request.pduDestination = GlobalBroadcast()

    else:

        # send to specified address
        request.pduDestination = Address(address)

    # setup device parameters
    request.iAmDeviceIdentifier = console.device.objectIdentifier
    request.maxAPDULengthAccepted = console.device.maxApduLengthAccepted
    request.segmentationSupported = console.device.segmentationSupported
    request.vendorID = console.device.vendorIdentifier

    # return created request
    return request


def whohas_request(args, console=None):
    # pylint: disable=too-many-statements, too-many-branches
    """
    This function creates a whohas request.

    Usage: whohas [ <address> ] ( <name> | <type> <instance> ) [ <lowlimit> <highlimit> ]

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if too few arguments were passed
    if len(args) == 0:
        raise ValueError('too few arguments')

    # initialize position and result
    result = {}

    address = None

    # check if limits were defined
    if len(args) > 2:
        if args[-1].isdigit() and args[-2].isdigit():
            result['low'] = int(args[-2])
            result['high'] = int(args[-1])
            args = args[:-2]

    if len(args) == 0:
        raise ValueError('name not found')

    elif len(args) == 3:
        if args[2].isdigit():
            address, result['type'], result['inst'] = args
        else:
            result['type'], result['inst'], result['name'] = args

    elif len(args) == 2:
        if args[1].isdigit():
            result['type'], result['inst'] = args
        else:
            address, result['name'] = args

    elif len(args) == 1:
        result['name'] = args[0]

    else:
        raise ValueError('too many arguments')

    # check if type is correct
    if 'inst' in result:
        if result['inst'].isdigit():
            result['inst'] = int(result['inst'])
        else:
            raise ValueError('object instance invalid')

    # check if instance is correct
    if 'type' in result:
        if result['type'].isdigit():
            result['type'] = int(result['type'])

        elif not get_object_class(result['type']):
            raise ValueError('object type invalid')

    obj_id = None
    if 'inst' in result and 'type' in result:
        obj_id = (result['type'], result['inst'])

    # create whohas object
    console = WhoHasObject()
    console.objectName = result.get('name', None)
    console.objectIdentifier = obj_id

    if 'low' in result:
        limits = WhoHasLimits()
        limits.deviceInstanceRangeLowLimit = result['low']
        limits.deviceInstanceRangeHighLimit = result['high']
    else:
        limits = None

    # create request
    request = WhoHasRequest()

    # check if address was specified
    if address is None:

        # send broadcast
        request.pduDestination = GlobalBroadcast()

    else:

        # send to specified address
        request.pduDestination = Address(address)

    request.object = console
    request.limits = limits

    # return created request
    return request


def ihave_request(args, console=None):
    """
    This function creates a ihave request.

    Usage: ihave [ <address> ] ( <name> | <type> <instance> )

    :param args: list of parameters
    :param console: console object
    :return: request
    """

    # check if console was provided
    if console is None:
        raise ValueError('console not found')

    # check if arguments were provided
    if len(args) == 0:
        raise ValueError('too few arguments')

    elif len(args) > 3:
        raise ValueError('too many arguments')

    # read object name
    obj_name = args[0]

    # initialize address and object
    address = None

    # get object
    if len(args) == 1:
        obj = console.application.get_object_by_name(obj_name)

    # check if id or address was set
    elif len(args) == 2:

        # check if id was set
        if args[1].isdigit():
            # read object id
            obj_id = (obj_name, int(args[1]))

            # get object
            obj = console.application.get_object_by_id(obj_id)

        else:
            # read address
            address = obj_name

            # read object name
            obj_name = args[1]

            # get object
            obj = console.application.get_object_by_name(obj_name)

    else:
        # read address
        address = obj_name

        # read object name
        obj_id = args[1:3]

        # check if id is correct
        if not obj_id[1].isdigit():
            raise ValueError('identifier not correct')

        # get object
        obj = console.application.get_object_by_id(obj_id)

    if obj is None:
        raise ValueError('object not found')

    # create request
    request = IHaveRequest()

    # check if address was specified
    if address is None:

        # send broadcast
        request.pduDestination = GlobalBroadcast()

    else:

        # send to specified address
        request.pduDestination = Address(address)

    # setup device parameters
    request.deviceIdentifier = console.device.objectIdentifier
    request.objectIdentifier = obj.objectIdentifier
    request.objectName = obj.objectName

    # return created request
    return request
