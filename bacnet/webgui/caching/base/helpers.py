"""
Base Helpters Module
-------------------

This module contains helper functions for cache objects.
"""

import sys


def get_class(cls, new_class=None):
    """
    This function returns the class for a given name.

    :param cls: class name
    :param new_class: new class description
    :return: class
    """

    # check if class is string
    if isinstance(cls, basestring):
        # get class from globals
        cls = globals().get(cls, cls)

        # check if new class is defined and class name belongs to new class
        if new_class is not None and cls == new_class.__name__:
            # set class to new class
            cls = new_class

    # check if class is dictionary
    elif isinstance(cls, dict):
        # get class from module
        cls = getattr(sys.modules[cls['module']], cls['name'], cls)

    # return class
    return cls


def class_dict(cls):
    """
    This function returns a short class description for any given class.

    :param cls: class
    :return: class description
    """

    # check if class is dictionary
    if isinstance(cls, dict):
        # return class
        return cls

    # check if class is string
    elif isinstance(cls, basestring):
        # return class description
        return {
            'name': cls.strip('.')[-1],
            'module': '.'.join(cls.strip('.')[:-1]),
        }

    # return class description
    return {
        'name': cls.__name__,
        'module': cls.__module__,
    }
