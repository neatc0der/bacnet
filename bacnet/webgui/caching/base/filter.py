# pylint: disable=no-member, not-callable

"""
Base Filter Module
-------------------

This module contains filter for cache objects.
"""

from ..cache import get_objects, get_object_ids


class BaseObjectFilter(object):
    """
    This class describes a filter for cache objects.
    """
    cls = None

    def get_or_update(self, *args, **kwargs):
        """
        Get or Update Instance by positional and keyword arguments
        """

        # get update fields
        update = kwargs.pop('update_fields', ())

        # initialize updated fields
        updated = ()

        # create new object
        instance = self.cls(*args, **kwargs)

        # get existing instance
        existing = get_objects(instance.id)

        # check if object must be created
        created = existing is None

        # check if object already exists
        if not created:
            # set instance to existing
            instance = existing

            # loop through update fields
            for attribute in update:
                # get old value
                old_value = getattr(instance, attribute)

                # get old values id if available
                old_value = getattr(old_value, 'id', old_value)

                # get new value
                new_value = kwargs[attribute]

                # get new values id if available
                new_value = getattr(new_value, 'id', new_value)

                # check if values differ
                if old_value != new_value:
                    # store new value in object
                    setattr(instance, attribute, kwargs[attribute])

                    # add field to updated fields
                    updated += (attribute,)

        # check if fields were updated
        updated = any(updated)

        # check if there were updated fields or the object was created
        if updated or created:
            # store object
            instance.save()

        # return object
        return instance

    def filter(self, **kwargs):
        """
        Filter Objects by keyword arguments
        """

        # initialize results
        result = []

        # loop through all objects
        for obj in self.iter_all():
            # initialize match criteria
            match = True

            # loop through all
            for key, value in kwargs.iteritems():
                # check if more than one key was provided
                if '__' in key.strip('_'):
                    # split keys
                    split_keys = key.split('__')

                    # check if first key is private
                    if split_keys[0] == '':
                        # remove empty part of split keys
                        del split_keys[0]

                        # add private part to first key
                        split_keys[0] = '__' + split_keys[0]

                    # check if last key ends with two underscores
                    if split_keys[-1] == '':
                        # remove empty part of split keys
                        del split_keys[-1]

                        # add underscores to last key
                        split_keys[-1] += '__'

                    # initialize object value
                    obj_value = obj

                    # loop through all split keys
                    for separate_key in split_keys:
                        # get value for key
                        obj_value = getattr(obj_value, separate_key, None)

                else:
                    # get value by key
                    obj_value = getattr(obj, key, None)

                # get id from value if available
                value = getattr(value, 'id', value)

                # get id from object value if available
                obj_value = getattr(obj_value, 'id', obj_value)

                # check if value differs
                if obj_value != value:
                    # set match to False
                    match = False

                    # break loop
                    break

            # check if values matched
            if not match:
                # go to next object
                continue

            # add object to result
            result.append(obj)

        # return object list
        return BaseObjectList(result)

    def count(self):
        """
        Count Objects
        """

        # return count of all objects
        return len(self.all())


class BaseObjectList(BaseObjectFilter, list):
    """
    This class provides list functionality for filter.
    """

    def all(self):
        """
        All Objects
        """

        # returns all objects
        return self

    def iter_all(self):
        """
        Iterator for All Objects
        """

        # return iterator for all objects
        return iter(self)


class BaseObjectHandler(BaseObjectFilter):
    """
    This class describes handler functions for cache object filter.
    """

    def __init__(self, cls):
        """
        Initialization
        """

        # set class
        self.cls = cls

    @staticmethod
    def get(key):
        """
        Get Object by Key
        """

        # return cache object
        return get_objects(key)

    def all(self):
        """
        All Objects
        """

        # return list of all objects
        return list(self.iter_all())

    def iter_all(self):
        """
        Iterator for All Objects
        """

        # return cache objects
        return get_objects(
            '%s_%s_*' % (self.cls.__module__.replace('.', '_'), self.cls.__name__),
            iterable=True
        )

    def all_by_id(self):
        """
        All Object IDs
        """

        # return cache object ids
        return get_object_ids(
            '%s_%s_*' % (
                self.cls.__module__.replace('.', '_'),
                self.cls.__name__,
            )
        )

    def count(self):
        """
        Count Objects
        """

        # return count of all objects
        return len(self.all_by_id())
