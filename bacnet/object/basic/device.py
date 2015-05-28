# pylint: disable=invalid-name, no-name-in-module, unused-import, too-few-public-methods

"""
Object Basic Module
--------------------

This module contains basic definitions of BACpypes Object.
"""

from __future__ import absolute_import

from bacpypes.primitivedata import ObjectIdentifier
from bacpypes.constructeddata import ArrayOf

from .general import DeviceObject, properties, register_object_type

from bacnet.debugging import bacnet_debug, ModuleLogger


# enable logging
ModuleLogger()


@bacnet_debug
@register_object_type
class LocalDeviceObject(DeviceObject):
    """
    This class provides additional functionality for device objects.
    """

    properties = [
        properties.CurrentTimeProperty('localTime'),
        properties.CurrentDateProperty('localDate')
    ]

    defaultProperties = {
        'maxApduLengthAccepted': 1024,
        'segmentationSupported': 'segmentedBoth',
        'maxSegmentsAccepted': 16,
        'apduSegmentTimeout': 20000,
        'apduTimeout': 3000,
        'numberOfApduRetries': 3,
    }

    def __init__(self, **kwargs):
        """
        This function initializes the object.

        :return: None
        """

        self._debug("__init__ %r", kwargs)

        # fill in default property values not in kwargs
        for attr, value in LocalDeviceObject.defaultProperties.items():
            if attr not in kwargs:
                kwargs[attr] = value

        # proceed as usual
        DeviceObject.__init__(self, **kwargs)

        # create a default implementation of an object list for local devices.
        # If it is specified in the kwargs, that overrides this default.
        if 'objectList' not in kwargs:
            self.objectList = ArrayOf(ObjectIdentifier)([self.objectIdentifier])

            # if the object has a property list and one wasn't provided
            # in the kwargs, then it was created by default and the objectList
            # property should be included
            if ('propertyList' not in kwargs) and self.propertyList:
                # make sure it's not already there
                if 'objectList' not in self.propertyList:
                    self.propertyList.append('objectList')

        # initialize cov subscriptions
        self.WriteProperty('activeCovSubscriptions', {}, direct=True)
