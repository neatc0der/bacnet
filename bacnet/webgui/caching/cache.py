"""
Cache Module
------------

This module provides basic cache access functions.
"""

from django.core.cache import cache

from collections import Iterable


def set_line(line, timeout=None):
    """
    This function stores a transmitted line.

    :param line: command
    :param timeout: timeout for storage
    :return: stored in cache
    """

    # return stored in cache
    return cache.set(line.replace(' ', '_'), line, timeout=timeout)


def has_line(line):
    """
    This function checks if line has been transmitted already.

    :param line: command
    :return: line is in cache
    """

    # returns line in cache
    return has_objects(line.replace(' ', '_'))


def get_objects(key, iterable=False):
    """
    This function loads an objects from cache.
    :param key: object key
    :param iterable: iterable result
    :return: objects
    """

    # check if key is iterable and not string
    if isinstance(key, Iterable) and not isinstance(key, basestring):
        # get objects by keys
        objs = cache.get_many(key)

        # check if result must be iterable
        if iterable:
            # return generator
            return (objs[k] for k in key)

        # return tuple of objects
        return tuple(objs[k] for k in key)

    # check if key is string
    elif isinstance(key, basestring) and '*' in key:
        # check if result must be iterable
        if iterable:
            # return generator
            return (get_objects(k) for k in cache.iter_keys(key))

        # return tuple of objects
        return tuple(get_objects(k) for k in cache.keys(key))

    # return object by key
    return cache.get(key)


def set_object(obj, timeout=None):
    """
    This function stores an object.

    :param obj: objects
    :param timeout: timeout for storage
    :return: stored in cache
    """

    # return stored in cache
    return cache.set(obj.id, obj, timeout=timeout)


def has_objects(key):
    """
    This function checks if object has been stored already.

    :param key: object key
    :return: object in cache
    """

    # return object in cache
    return any(cache.keys(key))


def delete_objects(key):
    """
    This function deletes an object from cache.

    :param key: object key
    :return: object deleted
    """

    # check if key is iterable and not string
    if isinstance(key, Iterable) and not isinstance(key, basestring):
        # return objects deleted
        return any(delete_objects(k) for k in key)

    # check if key is string
    elif isinstance(key, basestring) and '*' in key:
        # return objects deleted
        return any(delete_objects(k) for k in cache.keys(key))

    # return object deleted
    return bool(cache.delete(key))


def get_object_ids(key):
    """
    This functions returns all existing keys for a certain format.

    :param key: format key
    :return: existing keys
    """

    # return existing keys
    return cache.keys(key)
