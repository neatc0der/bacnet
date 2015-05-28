# pylint: disable=invalid-name, no-member, protected-access, too-few-public-methods
# pylint: disable=global-variable-not-assigned, attribute-defined-outside-init

"""
Caching Base Module
-------------------

This module contains the basic description of cache objects and their relation.
"""

from copy import copy
from six import with_metaclass
from uuid import uuid4

from ..cache import get_objects, set_object, delete_objects

from .options import Options
from .filter import BaseObjectFilter, BaseObjectHandler, BaseObjectList
from .helpers import get_class, class_dict
from .relations import CacheField, CacheForeignReference, CacheManyToManyReference, CacheReference,\
    CacheReferenceSet, CacheOneToOneReference, CacheRelatedReference


def create_class(name, parents, attributes):
    """
    This function creates a new class.

    :param name: class name
    :param parents: class parents
    :param attributes: attributes
    :return: new class
    """

    # create class
    cls = type(name, parents, attributes)

    # make it accessible
    globals()[name] = cls

    # return class
    return cls


def get_store_id(attr_name):
    """
    This function provides the storage id for relation attributes.

    :param attr_name: relation attribute
    :return: storage id
    """

    # check if attribute starts with underscore
    if attr_name.startswith('_'):
        # add storage to attribute name
        attr_name = 'storage_%s' % attr_name

    # return storage id
    return '_%s' % attr_name


def get_store_relation(attr_name):
    """
    This function provides the object storage for relation attributes.
    :param attr_name: relation attribute
    :return: object storage
    """

    # check if attribute starts with underscore
    if attr_name.startswith('_'):
        # add storage to attribute name
        attr_name = 'storage_%s' % attr_name

    # return object storage
    return '_%s_obj' % attr_name


META_REFERENCES = {}


class BaseObject(type):
    """
    Base Object Class
    """

    def __new__(cls, reference_name, bases, attrs):
        # pylint: disable=bad-mcs-classmethod-argument
        """
        Class Creation
        """

        def create_foreign_relation(related_class, foreign_class, attribute):
            """
            Foreign Relation Creation
            """

            def get_func(self):
                """
                Foreign Relation Output
                """

                relation = getattr(self, get_store_relation(attribute.name), None)
                if relation is None:
                    relation = get_objects(getattr(self, get_store_id(attribute.name), None))
                    setattr(self, get_store_relation(attribute.name), relation)

                if isinstance(relation, CacheRelation):
                    return relation.foreign

            def set_func(self, value):
                """
                Foreign Relation Input
                """

                if value is None:
                    value = ''

                if getattr(self, get_store_id(attribute.name), None) != value:
                    relation = getattr(self, get_store_relation(attribute.name), None) or \
                               get_objects(getattr(self, get_store_id(attribute.name), None))

                    if isinstance(relation, CacheRelation):
                        related_set = relation.related
                        related_set.remove(self)

                    if attribute.relation_class.related_name in dir(value):
                        obj = value

                    else:
                        obj = get_objects(getattr(value, 'id', value))


                    related_set = getattr(obj, attribute.relation_class.related_name, None)
                    if isinstance(related_set, CacheReferenceSet):
                        relation = related_set.relation
                        if self.id:
                            related_set.add(self)
                        relation.save()

                        setattr(self, get_store_id(attribute.name), relation.id)
                        setattr(self, get_store_relation(attribute.name), relation)

                    elif attribute.relation_class.recursive_delete:
                        self.remove()

                    else:
                        setattr(self, get_store_id(attribute.name), None)
                        setattr(self, get_store_relation(attribute.name), '')

            related_class._meta.foreign += (attribute.name,)
            setattr(related_class, attribute.name, property(get_func, set_func))
            setattr(related_class, get_store_id(attribute.name), CacheField(''))
            setattr(related_class, get_store_relation(attribute.name), CacheField())

            if hasattr(foreign_class, '_meta'):
                create_related_relation(foreign_class, attribute)

            else:
                setattr(
                    foreign_class,
                    attribute.field,
                    CacheRelatedReference(
                        related_class,
                        related_name=attribute.field,
                    )
                )

        def create_related_relation(foreign_class, attribute):
            """
            Related Relation Creation
            """

            def get_func(self):
                """
                Related Relation Output
                """
                relation = getattr(self, get_store_relation(attribute.field), None)

                if not isinstance(relation, CacheRelation):
                    relation = get_objects(getattr(self, get_store_id(attribute.field), None))

                    if not isinstance(relation, CacheRelation):
                        relation = attribute.relation_class(foreign=self)
                        relation.save()

                        setattr(self, get_store_id(attribute.field), relation.id)

                    self.save()
                    setattr(self, get_store_relation(attribute.field), relation)

                return relation.related

            foreign_class._meta.related += (attribute.field,)
            setattr(foreign_class, attribute.field, property(get_func))
            setattr(foreign_class, get_store_id(attribute.field), CacheField(''))
            setattr(foreign_class, get_store_relation(attribute.field), CacheField())

        global META_REFERENCES

        super_new = super(BaseObject, cls).__new__

        module = attrs.pop('__module__')
        new_class = super_new(cls, reference_name, bases, {'__module__': module})
        attr_meta = attrs.pop('Meta', None)
        abstract = getattr(attr_meta, 'abstract', False)

        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta

        setattr(new_class, '_meta', Options(meta))

        if abstract:
            attr_meta.abstract = False
            if not hasattr(attr_meta, 'attrs'):
                attr_meta.attrs = {}
            attr_meta.attrs.update(attrs)
            new_class.Meta = attr_meta
            return new_class

        if meta:
            new_attrs = meta.attrs.copy()
            new_attrs.update(attrs)

        else:
            new_attrs = attrs

        setattr(new_class, 'objects', BaseObjectHandler(new_class))

        if reference_name in META_REFERENCES:
            for attr_name, value in META_REFERENCES.iteritems():
                if attr_name:
                    setattr(new_class, attr_name, value)
            for ref_class, attributes in META_REFERENCES[''].iteritems():
                for attr_name, value in attributes:
                    if issubclass(value, CacheForeignReference):
                        value.name = attr_name
                        create_foreign_relation(ref_class, new_class, value)

            del META_REFERENCES[reference_name]

        for attr_name, attribute in new_attrs.iteritems():
            if isinstance(attribute, CacheField):
                attribute.name = attr_name

            if type(attribute) == CacheReference:
                raise TypeError('%s not allowed as instance' % attribute.__class__.__name__)

            elif isinstance(attribute, CacheReference):
                if isinstance(attribute, CacheOneToOneReference):
                    # TODO: support for One To One Relationship (if needed)
                    raise TypeError('One To One Relationship not yet supported (TODO)')
                    # parent_relation = CacheOneToOneRelation

                elif isinstance(attribute, CacheForeignReference):
                    parent_relation = CacheForeignRelation

                elif isinstance(attribute, CacheManyToManyReference):
                    # TODO: support for Many To Many Relationship (if needed)
                    raise TypeError('Many To Many Relationship not yet supported (TODO)')
                    # parent_relation = CacheManyToManyRelation

                else:
                    raise TypeError(
                        'unsupported cache reference defined in %s.%s' % (
                            new_class.__module__,
                            new_class.__name__
                        )
                    )

                ref_class = get_class(attribute.target, new_class=new_class)

                new_class_name = new_class.__name__
                ref_class_name = getattr(ref_class, '__name__', ref_class)

                relation_class = create_class(
                    '%s_%s_%s_%s_%s' % (
                        new_class.__module__.replace('.', '_'),
                        parent_relation.__name__,
                        new_class_name,
                        ref_class_name,
                        attribute.name
                    ),
                    (parent_relation,),
                    {
                        '__module__': parent_relation.__module__,
                        'foreign_name': attribute.name,
                        'related_name': attribute.field,
                        '_foreign_cls': ref_class,
                        '_related_cls': new_class,
                        'loosely_coupled': attribute.loosely_coupled,
                        'recursive_delete': attribute.recursive_delete,
                    }
                )

                attribute.relation_class = relation_class

                if isinstance(attribute, CacheForeignReference):
                    if issubclass(ref_class, CacheObject):
                        create_foreign_relation(
                            new_class,
                            ref_class,
                            attribute.related_attribute
                            if attribute.related_attribute else attribute,
                        )

                    else:
                        cls_references = META_REFERENCES.get(ref_class, {})
                        cls_references[attr_name] = CacheRelatedReference(
                            new_class,
                            related_name=attribute.field,
                            foreign_attribute=attribute,
                        )
                        open_refences = cls_references.get('', {})
                        attributes = open_refences.get(new_class, {})
                        attributes[attr_name] = attribute
                        open_refences[new_class] = attributes
                        cls_references[''] = open_refences
                        META_REFERENCES[ref_class] = cls_references

                elif isinstance(attribute, CacheManyToManyReference):
                    new_class._meta.many2many += (attr_name,)

                elif isinstance(attribute, CacheRelatedReference):
                    if attribute.foreign_attribute:
                        create_foreign_relation(ref_class, new_class, attribute.foreign_attribute)
                    create_related_relation(ref_class, attribute)

            elif isinstance(attribute, CacheField):
                new_class._meta.fields += (attr_name,)
                setattr(new_class, attr_name, attribute.target)

            else:
                setattr(new_class, attr_name, attribute)

        return new_class


class CacheObject(with_metaclass(BaseObject)):
    """
    Basic Cache Object
    """

    class Meta(object):
        """
        Meta Description
        """

        abstract = True

    no_save = ()
    dict_data = ()

    # cache key
    id = CacheField('')

    # instance name
    name = CacheField('')

    def __init__(self, **kwargs):
        """
        Instance Initialization
        """

        for attribute in set(dir(self)) - set(self._meta.related):
            if attribute in kwargs:
                setattr(self, attribute, kwargs.pop(attribute))

            else:
                value = getattr(self.__class__, attribute, None)

                if type(value) is CacheField:
                    setattr(self, attribute, copy(value.target))

        for attribute, value in kwargs.iteritems():
            setattr(self, attribute, value)

        identifier = self.get_id()
        self.id = '%s_%s_%s' % (
            self.__class__.__module__.replace('.', '_'),
            self.__class__.__name__,
            identifier
        )

        # add instance to related foreign object
        for attribute in self._meta.foreign:
            relation = get_objects(getattr(self, get_store_id(attribute)))
            if relation:
                relation.related.add(self)

    def __repr__(self):
        """
        Representation
        """

        return '<%s ID:%s>' % (self.__class__.__name__, self.id)

    def __str__(self):
        """
        String Conversion
        """

        return self.__repr__()

    def get_id(self):
        """
        Basic Identifier Setting
        """

        return str(uuid4())

    @property
    def as_dict(self):
        """
        Basic Dictionary Output
        """

        return {key: getattr(self, key) for key in self.dict_data}

    @property
    def instance(self):
        """
        Basic Instance Name Output
        """

        return self.name

    def save(self):
        """
        Instance Saving
        """

        tmp = {}
        for attribute in self.no_save:
            tmp[attribute] = getattr(self, attribute, None)
            setattr(self, attribute, None)

        for attribute in self._meta.foreign + self._meta.related:
            setattr(self, get_store_relation(attribute), None)

        set_object(self, 7200)

        for attribute, value in tmp.iteritems():
            setattr(self, attribute, value)

    def remove(self):
        """
        Instance Removing
        """

        if delete_objects(self.id):
            for name in self._meta.foreign:
                setattr(self, name, None)

            for name in self._meta.related:
                related_set = getattr(self, name)
                if related_set is not None:
                    related_set.remove()


class CacheRelation(CacheObject):
    """
    Basic Cache Relation
    """

    class Meta(object):
        """
        Meta Description
        """

        abstract = True
        attrs = copy(CacheObject.Meta.attrs)

    no_save = ('_foreign_obj', '_related_obj')

    _relation = ''
    _foreign_cls = None
    _related_cls = None

    _foreign_obj = None
    _related_obj = None

    foreign_name = ''
    related_name = ''

    loosely_coupled = False
    recursive_delete = False

    def get_id(self):
        """
        Basic Identifier Setting
        """

        if not self._foreign:
            raise ValueError('foreign key must be set')

        self._foreign_cls = class_dict(self._foreign_cls)
        self._related_cls = class_dict(self._related_cls)

        identifier = 'relation_%s' % (
            self._foreign,
        )

        return identifier

    @property
    def foreign(self):
        """
        Foreign Relation Getter
        """

        if self._foreign_obj is None:
            self._foreign_obj = get_objects(self._foreign)

        return self._foreign_obj

    @foreign.setter
    def foreign(self, key):
        """
        Foreign Relation Setter
        """

        if hasattr(key, 'id'):
            self._foreign = key.id
            self._foreign_obj = key

        else:
            self._foreign = key
            self._foreign_obj = None

    @property
    def related(self):
        """
        Related Relation Getter
        """

        if self._related_obj is None:
            self._related_obj = get_objects(self._related)

        return self._related_obj

    @related.setter
    def related(self, key):
        """
        Related Relation Setter
        """

        if hasattr(key, 'id'):
            self._related = key.id
            self._related_obj = key

        else:
            self._related = key
            self._related_obj = None


class CacheOneToOneRelation(CacheRelation):
    """
    Cache One To One Relation
    """

    class Meta(object):
        """
        Meta Description
        """

        abstract = True
        attrs = copy(CacheRelation.Meta.attrs)

    _relation = 'one-to-one'

    _foreign = CacheField('')
    _related = CacheField('')


class CacheForeignRelation(CacheRelation):
    """
    Cache Foreign (One To Many) Relation
    """

    class Meta(object):
        """
        Meta Description
        """

        abstract = True
        attrs = copy(CacheRelation.Meta.attrs)

    _relation = 'one-to-many'

    _foreign = CacheField('')
    _related = CacheField(tuple())

    @property
    def related(self):
        """
        Related Relation Getter
        """

        if self._related_obj is None:
            self._related_obj = CacheReferenceSet(self, get_class(self._related_cls), '_related')

        return self._related_obj


class CacheManyToManyRelation(CacheRelation):
    """
    Cache Many To Many Relation
    """

    class Meta(object):
        """
        Meta Description
        """

        abstract = True
        attrs = copy(CacheRelation.Meta.attrs)

    _relation = 'many-to-many'

    _foreign = CacheField(tuple())
    _related = CacheField(tuple())

    @property
    def foreign(self):
        """
        Foreign Relation Getter
        """

        if self._foreign_obj is None:
            self._foreign_obj = CacheReferenceSet(self, get_class(self._foreign_cls), '_foreign')

        return self._foreign_obj

    @property
    def related(self):
        """
        Related Relation Getter
        """

        if self._related_obj is None:
            self._related_obj = CacheReferenceSet(self, get_class(self._related_cls), '_related')

        return self._related_obj
