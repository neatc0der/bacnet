# pylint: disable=anomalous-backslash-in-string, import-error, no-init, too-few-public-methods
# pylint: disable=invalid-name, attribute-defined-outside-init

"""
Control Models Module
---------------------

This module contains the model description of all used cache objects.
"""

from datetime import datetime
import re

from django.conf import settings

from caching import base, get_objects


DEVICE_ID = u'device_{0}'
DEVICE_REGEX = re.compile(u'^device[a-z]*_\d+$', re.IGNORECASE)


class BACnetAddress(base.CacheObject):
    """
    BACnet Address as Cache Object
    """

    dict_data = (
        'id',
        'address',
    )

    address = base.CacheField('')

    def get_id(self):
        """
        Custom Identifier Setting
        """

        if not self.address:
            raise ValueError('address needs an address')

        identifier = 'ip_%s' % self.address

        return identifier


class BACnetObject(base.CacheObject):
    """
    BACnet Object as Cache Object
    """

    dict_data = (
        'id',
        'name',
        'file_content',
        'instance',
        'short_id',
        'is_device',
        'is_local_device',
        'properties_dict',
        'objects_dict',
        'address_dict',
    )

    # device is local
    is_local_device = base.CacheField(False)

    # instance parameters
    object_type = base.CacheField('')
    object_id = base.CacheField('')

    # content for file objects
    file_content = base.CacheField('')

    # device object
    device = base.CacheForeignReference(
        'BACnetObject',
        related_name='children',
        recursive_delete=True,
        loosely_coupled=True,
    )

    # ip address
    ip = base.CacheForeignReference(
        BACnetAddress,
        related_name='device',
        recursive_delete=False,
        loosely_coupled=False,
    )

    def get_id(self):
        """
        Custom Identifier Setting
        """

        if not self.object_type or not self.object_id:
            raise ValueError('objects needs type and id')

        elif self.object_type != 'device' and self.is_device:
            raise ValueError('object needs a device')

        elif self.object_type == 'device' and not self.is_device:
            raise ValueError('device must have no device')

        elif self.object_type == 'device' and self.is_device and not self.address:
            raise ValueError('device needs an address')

        identifier = ('%s_' % self.device.short_id) if not self.is_device else ''
        identifier += '%s_%s' % (self.object_type, self.object_id)

        if self.address.address in ('1', settings.IP_ADDRESS):
            self.is_local_device = True

        return identifier

    _is_device = None

    @property
    def is_device(self):
        """
        Device Indicator
        """

        if self._is_device is None:
            self._is_device = not bool(self.device)

        return self._is_device

    @property
    def address(self):
        """
        Address Getter
        """

        if self.is_device:
            return self.ip

        return self.device.address

    @address.setter
    def address(self, value):
        """
        Address Setter
        """

        if not self.is_device:
            raise ValueError('address can only be set for devices')

        self.ip = value

    @property
    def instance(self):
        """
        Instance Getter
        """
        return self.object_type, self.object_id

    @instance.setter
    def instance(self, object_instance):
        """
        Instance Setter
        """

        self.object_type = object_instance[0]
        self.object_id = object_instance[1]

    @property
    def short_id(self):
        """
        Shortened Instance Getter
        """

        return '%s_%s' % (self.object_type, self.object_id)

    def get_child_objects(self, subkey):
        """
        Child Selector
        """

        return get_objects('%s_%s' % (self.id, subkey))

    def get_or_create_property(self, **kwargs):
        """
        Property Creator
        """

        prop = self.get_property(kwargs['name'])
        if prop is None:
            kwargs['parent'] = self
            prop = BACnetProperty(**kwargs)
            prop.save()
            self.save()

        return prop

    def get_property(self, name):
        """
        Property Getter
        """

        for prop in self.properties.iter_all():
            if prop.name == name:
                return prop

    _object_name = None

    @property
    def name(self):
        """
        Name Indicator
        """

        if self._object_name is None:
            prop = self.get_property('objectName')
            if prop is not None:
                self._object_name = prop.value

            else:
                return '%s %s' % (self.object_type.title(), self.object_id)

        return self._object_name

    @property
    def properties_dict(self):
        """
        Property Summery
        """

        return self.properties.values_list('as_dict', index='name', flat=True)

    @property
    def objects_dict(self):
        """
        Object Summery
        """

        return self.children.values_list('as_dict', index='short_id', flat=True)

    @property
    def address_dict(self):
        """
        Address Summery
        """

        if self.address is not None:
            return self.address.as_dict

        return {}


class BACnetProperty(base.CacheObject):
    """
    BACnet Property as Cache Object
    """

    dict_data = (
        'id',
        'name',
        'value',
        'updated',
    )

    # object
    parent = base.CacheForeignReference(
        BACnetObject,
        related_name='properties',
        recursive_delete=True,
        loosely_coupled=True,
    )

    # property value
    _value = ''

    # last updated
    _updated = ''

    def get_id(self):
        """
        Custom Identifier Setting
        """

        if self.parent is None:
            raise ValueError('property needs an object to exist')

        if not self.name:
            raise ValueError('property needs a name')

        self._updated = datetime.utcnow()

        identifier = '%s_property_%s' % (self.parent.id, self.name)

        return identifier

    @property
    def instance(self):
        """
        Instance Getter
        """

        return self.name

    @instance.setter
    def instance(self, name):
        """
        Instance Setter
        """

        self.name = name

    @property
    def updated(self):
        """
        Last Time Updated
        """

        return (datetime.utcnow() - self._updated).seconds

    @property
    def value(self):
        """
        Value Output
        """

        return self._value

    def set_value(self, data, index=None):
        """
        Value Input
        """

        if index is not None:
            if index == 0:
                if not isinstance(self._value, list):
                    self._value = list(None for i in xrange(data + 1))
                elif data > len(self._value):
                    self._value += list(None for i in xrange(data - len(self._value) + 1))
                elif data < len(self._value):
                    self._value = self._value[:data + 1]

            else:
                if not isinstance(self._value, list):
                    self._value = list(None for i in xrange(index + 1))
                elif index >= len(self._value):
                    self._value += list(None for i in xrange(index - len(self._value) + 1))

            self._value[index] = data

        else:
            self._value = data

        self._updated = datetime.utcnow()

        if self.name == 'objectName':
            self.parent._object_name = None
            self.parent.save()
