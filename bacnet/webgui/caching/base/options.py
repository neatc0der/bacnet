# pylint: disable=too-few-public-methods

"""
Base Options Module
-------------------

This module contains the options description of basic cache objects.
"""


class Options(object):
    """
    This class provides information of structure and relations.
    """

    def __init__(self, meta):
        """
        This function initializes the instance.
        """

        # general fields
        self.fields = ()

        # foreign relations
        self.foreign = ()

        # many to many relations
        self.many2many = ()

        # related objects for foreign relation
        self.related = ()

        # meta description
        self.meta = meta
