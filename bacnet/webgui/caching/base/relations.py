# pylint: disable=too-few-public-methods, no-member

"""
Base Relations Module
-------------------

This module contains relation references for cache objects.
"""

from ..cache import get_objects

from .helpers import get_class
from .filter import BaseObjectFilter


class CacheField(object):
    """
    Basic Cache Field for Cache Objects
    """

    def __init__(self, value=None):
        """
        Instance Initialization
        """

        self.target = value
        self.name = ''


class CacheReference(CacheField):
    """
    Basic Cache Reference for Cache Objects
    """

    def __init__(self, cls, related_name='', recursive_delete=True, loosely_coupled=True):
        """
        Instance Initialization
        """

        if cls is None:
            raise ValueError('unknown class: %s' % cls)

        cls = get_class(cls)
        cls_name = cls.lower() if isinstance(cls, basestring) else '%s_obj' % cls.__name__.lower()

        CacheField.__init__(self, cls)

        self.field = related_name if related_name else '%s_obj' % cls_name
        self.recursive_delete = recursive_delete
        self.loosely_coupled = loosely_coupled


class CacheOneToOneReference(CacheReference):
    """
    Cache One to One Reference for Cache Objects
    """

    pass


class CacheForeignReference(CacheReference):
    """
    Cache Foreign Reference for Cache Objects
    """

    def __init__(self, *args, **kwargs):
        """
        Instance Initialization
        """

        self.related_attribute = kwargs.pop('related_attribute', False)
        CacheReference.__init__(self, *args, **kwargs)


class CacheRelatedReference(CacheReference):
    """
    Cache Related Reference for Cache Objects
    """

    def __init__(self, *args, **kwargs):
        """
        Instance Initialization
        """

        self.foreign_attribute = kwargs.pop('foreign_attribute', False)
        CacheReference.__init__(self, *args, **kwargs)


class CacheManyToManyReference(CacheReference):
    """
    Cache Many to Many Reference for Cache Objects
    """

    pass


class CacheReferenceSet(CacheField, BaseObjectFilter, set):
    """
    Cache Reference Set for Handling Related Cache Objects
    """

    def __init__(self, *args):
        """
        Instance Initialization
        """

        set.__init__(self)

        if len(args) < 3:
            # return
            # would raise error when unpickled
            #
            raise ValueError(
                '%s needs relation, class and field name as parameters' % self.__class__.__name__
            )

        self.relation = args[0]
        cls = get_class(args[1])
        self.field = args[2]

        self.update(getattr(self.relation, self.field))

        if isinstance(cls, basestring):
            raise ValueError('unknown class: %s' % cls)

        CacheField.__init__(self, cls)

    @classmethod
    def get_or_update(cls, *args, **kwargs):
        """
        Get or Update Instance by positional and keyword arguments
        """

        update = kwargs.pop('update_fields', ())
        updated = ()

        instance = cls(*args, **kwargs)
        existing = get_objects(instance.id)

        if existing is not None:
            instance = existing
            for attribute in update:
                if getattr(instance, attribute) != kwargs[attribute]:
                    setattr(instance, attribute, kwargs[attribute])
                    updated += (attribute,)

        if any(updated) or existing is None:
            instance.save()

        return instance

    def __copy__(self):
        """
        Copy Instance
        """

        return self.__class__(
            self.target,
            self.relation,
        )

    def add(self, obj):
        """
        Add Object
        """

        if hasattr(obj, 'id'):
            key = obj.id

        else:
            key = obj

        if not key:
            raise ValueError('key must not be none')

        set.add(self, key)
        setattr(self.relation, self.field, tuple(self))
        self.relation.save()

    def remove(self, obj):
        """
        Remove Object
        """

        if hasattr(obj, 'id'):
            key = obj.id

        else:
            key = obj

        if key in self:
            set.remove(self, key)
            setattr(self.relation, self.field, tuple(self))

        if self.count() == 0 and not self.relation.loosely_coupled:
            self.relation.remove()

        else:
            self.relation.save()

    def values_list(self, *args, **kwargs):
        """
        Value Output of All Objects
        """

        flat = kwargs.pop('flat', False)
        index_set = 'index' in kwargs
        index = kwargs.pop('index', 'instance')

        if len(args) == 0:
            raise ValueError('at least one attribute must be provided')

        elif len(args) > 1 and flat is True:
            raise ValueError('more than one attribute provided and flat requested')

        elif len(kwargs) > 0:
            keys = kwargs.keys()
            raise ValueError('unknown keyword argument: %s' % keys[0])

        result = () if flat and not index_set else {}

        for obj in self.iter_all():
            if flat:
                if index_set:
                    identifier = getattr(obj, index)
                    result[identifier] = getattr(obj, args[0], None)

                else:
                    result += (getattr(obj, args[0], None),)

            else:
                identifier = getattr(obj, index)

                result[identifier] = {}
                for attribute in args:
                    result[identifier][attribute] = getattr(obj, attribute, None)

        return result

    def all(self):
        """
        All Objects
        """

        return list(self.iter_all())

    def iter_all(self):
        """
        Iterator for All Objects
        """

        return (get_objects(key) for key in self)

    def count(self):
        """
        Count Objects
        """

        return len(self)
