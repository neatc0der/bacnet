# pylint: disable=invalid-name, too-many-arguments, star-args

"""
Object Basic Module
--------------------

This module contains basic definitions of BACpypes Object.
"""

from __future__ import absolute_import

from collections import Iterable

import bacpypes

from bacpypes.primitivedata import Unsigned, Real, ObjectIdentifier, CharacterString
from bacpypes.constructeddata import Array, ArrayOf, Any
from bacpypes.basetypes import PropertyValue, PropertyIdentifier

from bacpypes.pdu import Address
from bacpypes.apdu import ReadPropertyACK

from bacnet.debugging import bacnet_debug, ModuleLogger

from .. import properties, primitivedata

from .cov_support import COV_SUPPORT


# enable logging
ModuleLogger()


# list of all redefined bacpypes objects
COVObjectClasses = []


@bacnet_debug
class Object(bacpypes.object.Object):
    """
    This class is an extension of the bacpypes Object class to support COV notifications.
    """

    properties = [
        properties.ObjectIdentifierProperty('objectIdentifier', ObjectIdentifier, optional=False),
        properties.ReadableProperty('objectName', CharacterString, optional=False),
        properties.ReadableProperty('description', CharacterString),
        properties.OptionalProperty('profileName', CharacterString),
        properties.ReadableProperty('propertyList', ArrayOf(PropertyIdentifier)),
    ]

    def __init__(self, **kwargs):
        # pylint: disable=super-init-not-called
        """
        This function initializes the property.

        :return: None
        """

        self._debug('__init__ %s', kwargs)

        # set cov support
        self._hardware = kwargs.get('hardware', None)

        # get application
        application = kwargs.get('app', None)

        # set application
        self.set_application(application)

        # remove unnecessary keys from keywords
        for key in ('hardware', 'app'):
            if key in kwargs:
                del kwargs[key]

        # set cov support
        self._cov_support = self.__class__.__name__ in COV_SUPPORT

        # set cov dictionary
        self._cov_dict = {}

        # call predecessor
        # bacpypes.object.Object.__init__(self, **kwargs)

        initargs = {}
        for key, value in kwargs.items():
            if key not in self._properties:
                raise bacpypes.object.PropertyError(key)
            initargs[key] = value

        # start with a clean dict of values
        self._values = {}

        # start with a clean array of property identifiers
        if 'propertyList' in initargs:
            propertyList = None
        else:
            propertyList = ArrayOf(PropertyIdentifier)()
            initargs['propertyList'] = propertyList

        # initialize the object
        for propid, prop in self._properties.items():
            if propid in initargs:
                # defer to the property object for error checking
                prop.WriteProperty(self, initargs[propid], direct=True)

            elif prop.default is not None:
                # default values bypass property interface
                self._values[propid] = prop.default

            else:
                self._values[propid] = None

            # add it to the property list if we are building one
            if propertyList is not None:
                propertyList.append(propid)

    def __repr__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return u'<%s.%s \'%s %s\'>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.objectType,
            str(self.get_value('objectIdentifier')),
        )

    def __str__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()

    def __unicode__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()

    def set_application(self, application):
        """
        This function defines the application associated to this object.

        :param application: application object
        :return: None
        """

        # set application
        self._application = application

    def get_property(self, identifier):
        """
        This function returns the property for identifier.
        :param identifier: property identifier
        :return: property
        """

        # get property
        prop = self._properties.get(identifier, None)

        # return property
        return prop

    def get_value(self, identifier):
        """
        This function returns the value for property identifier.
        :param identifier: property identifier
        :return: value
        """

        # return value
        return self._values.get(identifier)

    def set_value(self, identifier, value):
        """
        This function sets the value for property identifier.
        :param identifier: property identifier
        :param value: property value
        :return: None
        """

        # set value
        self._values[identifier] = value

    def poll_hardware(self):
        """
        This function checks for value updates for hardware.

        :return: None
        """

        # check if object has hardware
        if self._hardware is not None:
            # get hardware value
            hw_value = self._hardware.get()

            # get present value property
            present_value = self.get_property('presentValue')

            # cast value
            hw_value = present_value.datatype(hw_value)

            # get current property value
            current_value = self.ReadProperty('presentValue')

            # check if value has changed
            if hw_value != current_value:
                # write value
                self.WriteProperty('presentValue', hw_value, direct=True)

    def cov_supported(self, prop=None):
        """
        This function checks if COV subscription is supported.

        :param prop: property object or identifier
        :return: COV is supported
        """

        # check if object supports cov
        if getattr(self, '_cov_support', False) is True:
            # check if property was defined
            if prop is None:
                return True

            # check if property is identifier
            if isinstance(property, (CharacterString, basestring)):
                # get property by identifier
                prop = self.get_property(prop)

            # check if property supportes cov
            if getattr(prop, 'cov_support', False) is True:
                return True

        return False

    def __get_property_list(self, prop_id=None, prop_index=None):
        """
        This function returns a tuple of supported cov properties.

        :param prop_id: property identifier
        :return: properties
        """

        # check if subscription is property specific
        if prop_id is None:
            # initialize properties
            props = ()

            # loop through supported cov properties
            for prop_id in COV_SUPPORT.get(self.__class__.__name__, {}).keys():
                # get property by identifier
                prop = self.get_property(prop_id)

                # check if property exists
                if prop is not None:
                    # initialize property array
                    prop_array = (None,)

                    # check if property is array
                    if issubclass(prop.datatype, Array):
                        # reset property array
                        prop_array = range(1, prop.ReadProperty(self, 0) + 1)

                    # loop through property array index
                    for prop_index in prop_array:
                        # add property to properties
                        props += ((prop, prop_index),)

        else:
            # create properties
            props = ((self.get_property(prop_id), prop_index),)

        # return properties
        return props

    def delete_cov_subscription(self, subscriptions, inform_app=False):
        """
        This function deletes subscription from cov subscription list.

        :param subscriptions: subscriptions
        :param inform_app: inform application
        :return: None
        """

        # check if subscriptions is iterable
        if not isinstance(subscriptions, Iterable):
            subscriptions = (subscriptions,)

        # get properties
        props = self.__get_property_list()

        # loop through all subscribed properties
        for prop, prop_index in props:
            # get property dictionary from cov dictionary
            prop_dict = self._cov_dict.get(prop.identifier, {})

            # get property array index list from property dictionary
            prop_index_list = prop_dict.get(prop_index, [])

            # initialize loop variable
            i = 0

            # loop through subscriptions
            while i < len(prop_index_list):
                # get entry
                entry = prop_index_list[i]

                # check if subscription is stored within the entry
                if entry['subscription'] in subscriptions:
                    # remove entry by index
                    del prop_index_list[i]

                    continue

                # go to next subscription
                i += 1

            # store property array index list
            prop_dict[prop_index] = prop_index_list

            # check if property array index list is empty
            if not any(prop_index_list):
                # remove property array index from property dictionary
                del prop_dict[prop_index]

            # store property dictionary
            self._cov_dict[prop.identifier] = prop_dict

            # check if property dictionary is empty
            if not any(prop_index_list):
                # remove property dictionary from cov dictionary
                del self._cov_dict[prop.identifier]

        # check if inform_app was set
        if inform_app:
            # inform app to delete subscriptions
            self._application.delete_cov_subscriptions(subscriptions, inform_object=False)

    def __create_cov_entry(self, subscription, prop=None, prop_index=None):
        """
        This function creates a cov entry for a subscription.

        :param subscription: subscription
        :param prop: property
        :return: entry dictionary
        """

        # create entry dictionary
        entry = {
            'subscription': subscription,
            'value': None
        }

        # check if property exists
        if prop is not None:
            # store current value to entry dictionary
            entry['value'] = prop.ReadProperty(self, prop_index)

        # return entry dictionary
        return entry

    def renew_cov_subscription(self, subscription):
        """
        This function checks if subscription can be renewed and returns boolean of this action.

        :param subscription: subscription
        :return: subscription renewed
        """

        # read property reference
        prop_ref = subscription.monitoredPropertyReference

        # read property identifier
        prop_id = prop_ref.propertyIdentifier

        # get properties
        props = self.__get_property_list(prop_id, prop_ref.propertyArrayIndex)

        # loop through all subscribed properties
        for prop, prop_index in props:
            # get property dictionary from cov dictionary
            prop_dict = self._cov_dict.get(prop.identifier, {})

            # get property array index list from property dictionary
            prop_index_list = prop_dict.get(prop_index, [])

            # loop through property array index list
            for i in range(len(prop_index_list)):
                # get subscription entry
                entry = prop_index_list[i]['subscription']

                # check if device and process id match
                if entry.recipient.recipient.device == subscription.recipient.recipient.device and \
                    entry.recipient.processIdentifier == subscription.recipient.processIdentifier:
                    # add subscription to property array index list
                    prop_index_list[i] = self.__create_cov_entry(subscription, prop, prop_index)

            # store property array index list
            prop_dict[prop_index] = prop_index_list

            # store property dictionary
            self._cov_dict[prop.identifier] = prop_dict

    def add_cov_subscription(self, subscription):
        """
        This function adds subscription to cov subscription list.

        :param subscription: subscription
        :return: None
        """

        # read property reference
        prop_ref = subscription.monitoredPropertyReference

        # read property identifier
        prop_id = prop_ref.propertyIdentifier

        # get properties
        props = self.__get_property_list(prop_id, prop_ref.propertyArrayIndex)

        # loop through all subscribed properties
        for prop, prop_index in props:
            # get property dictionary from cov dictionary
            prop_dict = self._cov_dict.get(prop.identifier, {})

            # get property array index list from property dictionary
            prop_index_list = prop_dict.get(prop_index, [])

            # add subscription to property array index list
            prop_index_list.append(self.__create_cov_entry(subscription, prop, prop_index))

            # store property array index list
            prop_dict[prop_index] = prop_index_list

            # store property dictionary
            self._cov_dict[prop.identifier] = prop_dict

    def __check_cov(self, prop, value):
        """
        This function checks if cov notification should be sent.

        :param prop: property
        :param value: property value
        :return: None
        """

        # check if application was set
        if self._application is not None:
            # check if application supports config queue
            if hasattr(self._application.requests, 'put'):
                # create read acknowledgement
                read_ack = ReadPropertyACK(
                    objectIdentifier=self.ReadProperty('objectIdentifier'),
                    propertyIdentifier=value.propertyIdentifier,
                    propertyArrayIndex=value.propertyArrayIndex,
                    propertyValue=value.value,
                )

                # set destination address
                read_ack.pduDestination = Address(('', 2))

                # inform config
                if hasattr(self._application.requests, 'put'):
                    self._application.requests.put(read_ack)

                # delete read acknowledgement
                del read_ack

        # check if cov is supported for this property
        if getattr(prop, 'cov_support', False) is True:
            # get property indexes
            prop_indexes = self._cov_dict.get(value.propertyIdentifier, {})

            # get subscriptions
            subscriptions = prop_indexes.get(
                value.propertyArrayIndex,
                []
            )

            # initialize list of removable subscriptions
            removables = ()

            # cast value
            casted_value = value.value.cast_out(prop.datatype)

            # check if value has correct data type
            if not isinstance(casted_value, prop.datatype):
                casted_value = prop.datatype(casted_value)

            # loop through subscriptions
            for i in range(len(subscriptions)):
                # read entry
                entry = subscriptions[i]

                # check if subscription expired
                if entry['subscription'].timeRemaining.remaining_time == 0:
                    # add subscription to removables
                    removables += (entry['subscription'],)

                # check if value has changed
                elif entry['value'] != casted_value:
                    # read subscription cov increment
                    cov_inc = entry['subscription'].covIncrement

                    # get cov increment property
                    obj_cov_inc = self.get_property('covIncrement')

                    # read property if it exists
                    if obj_cov_inc is not None:
                        obj_cov_inc = obj_cov_inc.ReadProperty(self)

                    # check if cov increment is reached
                    change = not isinstance(casted_value, (Real, Unsigned, int, float)) or \
                             entry['value'] is None or \
                             ((not cov_inc and not obj_cov_inc) or
                              (not obj_cov_inc and cov_inc <= abs(entry['value'] - casted_value)) or
                              (not cov_inc and obj_cov_inc <= abs(entry['value'] - casted_value)))

                    if change:
                        # send notification
                        self._application.send_cov_notification(
                            entry['subscription'],
                            [value],
                        )

                        # reset value
                        entry['value'] = casted_value

                        # store entry
                        subscriptions[i] = entry

            # store subscriptions
            prop_indexes[value.propertyArrayIndex] = subscriptions

            # store property indexes
            self._cov_dict[value.propertyIdentifier] = prop_indexes

            # check if removables were found
            if any(removables):
                # remove subscriptions
                self.delete_cov_subscription(removables, inform_app=True)

    def ReadProperty(self, propid, arrayIndex=None, **kwargs):
        """
        This function handles reading of property values.

        :param propid: property identifier
        :param arrayIndex: property index
        :return: property value
        """
        self._debug('ReadProperty %r arrayIndex=%r', propid, arrayIndex)

        # get the property
        prop = self.get_property(propid)

        # check if property exists
        if prop is None:
            raise bacpypes.object.PropertyError(propid)

        # get value
        value = prop.ReadProperty(self, arrayIndex, **kwargs)

        # return value
        return value

    def WriteProperty(self, propid, value, arrayIndex=None, priority=None, direct=False, **kwargs):
        """
        This function handles writing of property values.

        :param propid: property identifier
        :param value: property value
        :param arrayIndex: property index
        :param priority: write priority
        :param direct: direct write
        :return: property value
        """
        self._debug(
            'WriteProperty %r %r arrayIndex=%r priority=%r',
            propid,
            value,
            arrayIndex,
            priority
        )

        # get the property
        prop = self.get_property(propid)

        # check if property exists
        if prop is None:
            raise bacpypes.object.PropertyError(propid)

        # set value
        value = prop.WriteProperty(self, value, arrayIndex, priority, direct, **kwargs)

        # check if return value is supported and not an object
        if not isinstance(value, (dict, Object)):
            # convert value to any
            any_value = Any()
            any_value.cast_in(value)

            self.__check_cov(
                prop,
                PropertyValue(
                    propertyIdentifier=propid,
                    propertyArrayIndex=arrayIndex,
                    value=any_value,
                    priority=priority
                )

            )

        # return value
        return value


def register_object_type(cls, vendor_id=0):
    """
    This function stores new object types.

    :param cls: object class
    :return: None
    """

    # hand over register data
    return bacpypes.object.register_object_type(cls, vendor_id)


def get_object_class(cls, vendor_id=0):
    """
    This function returns the object type for a specified class.

    :param cls: object class
    :return: object type
    """

    # return object type
    return bacpypes.object.get_object_class(cls, vendor_id)


def get_datatype(cls, prop_id, vendor_id=0):
    """
    This function returns the data type for a specified class and property identifier.

    :param cls: object class
    :param prop_id: property identifier
    :return: object type
    """

    # return object type
    return bacpypes.object.get_datatype(cls, prop_id, vendor_id)


def new_property(cls_type, old_prop):
    """
    This function converts bacpypes properties into new bacnet properties.

    :param cls_type: object type
    :param old_prop: old property
    :return: new property
    """

    # read property class name
    cls_name = old_prop.__class__.__name__

    # get new class
    cls = getattr(properties, cls_name, None)

    # check if class exists
    if cls is None:
        raise RuntimeError('class "%s" not defined in this scope' % cls_name)

    # create attribute dictionary
    prop_attributes = {}

    # loop through necessary attributes
    for attribute in ('identifier', 'datatype', 'default', 'optional', 'mutable'):
        # get instance
        instance = getattr(old_prop, attribute)

        # check if attribute is default
        if attribute == 'default' and hasattr(instance, '__class__'):
            # get redefined attribute class
            attribute_class = getattr(primitivedata, instance.__class__.__name__, None)

            # check if new attribute class exists
            if attribute_class is not None:
                # reset instance
                instance = attribute_class(instance)

            # else:
            #     # set instance
            #     try:
            #         instance = old_prop.datatype(instance)
            #
            #     except:
            #         pass

        # check if attribute is data type
        if attribute == 'datatype':
            # get redefined attribute class
            instance = getattr(primitivedata, instance.__name__, instance)

        # collect attribute value
        prop_attributes[attribute] = instance

    prop_attributes['cov_support'] = COV_SUPPORT.get(cls_type.__name__, {}).get(
        prop_attributes['identifier'],
        False
    )

    # check if property is active cov subscriptions
    if prop_attributes['identifier'] == 'activeCovSubscriptions':
        # reset new class
        cls = properties.ActiveCovSubscriptionsProperty
        prop_attributes['datatype'] = primitivedata.SequenceOfCOVSubscription

    # check if object type is character string value and property is present value
    elif cls_type.objectType == 'characterstringValue' and \
        prop_attributes['identifier'] == 'presentValue':
        # reset property to writable
        cls = properties.WritableProperty

        # remove mutable attribute
        del prop_attributes['mutable']

    # create new property
    new_prop = cls(**prop_attributes)

    # return new property
    return new_prop


# create new object classes
for cls_obj in bacpypes.object.Object.__subclasses__():
    # ignore Object defined above
    if cls_obj.__name__ == 'Object':
        continue

    # create new properties
    cls_properties = []

    # loop through old properties
    for cls_prop in Object.properties + cls_obj.properties:
        # append new property instance
        cls_properties.append(new_property(cls_obj, cls_prop))

    # create new class
    new_class = type(
        cls_obj.__name__,
        (Object,),
        {
            'objectType': cls_obj.objectType,
            'properties': cls_properties,
            '__doc__': 'This class is an cov extended version of bacpypes %s.' % cls_obj.__name__,
        }
    )

    # register object class
    register_object_type(new_class)

    # append class to list
    COVObjectClasses.append(new_class)
    globals()[new_class.__name__] = new_class
