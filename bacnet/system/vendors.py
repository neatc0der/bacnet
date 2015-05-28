#!/usr/bin/env python
# pylint: disable=unused-argument

"""
Vendors
-------

This module provides an updater for BACnet vendor IDs.
"""

from formatter import NullFormatter
from htmllib import HTMLParser
from urllib2 import urlopen, HTTPError


VENDOR_URL = 'http://www.bacnet.org/VendorID/BACnet%20Vendor%20IDs.htm'
ROW_ORDER = ['id', 'name', 'contact', 'address']


class TableParser(HTMLParser):
    """
    This class implements a table parser for the BACnet vendor list.
    """

    def __init__(self):
        """
        This function initiates the object.

        :return: None
        """

        # call predecessor
        HTMLParser.__init__(self, NullFormatter())

        # reset column count
        self.col = 0

        # initialize vendor dictionary
        self.vendors = {}

        # initialize vendor data
        self.vendor = {}

        # initialize tag handlers
        self.current_tag = None

    def handle_starttag(self, tag, method, attrs):
        """
        This function is called on every start tag.

        :param tag: full tag
        :param method: tag function
        :param attrs: tag attributes
        :return: None
        """

        # check if tag is not break line
        if tag != 'br':

            # set current tag
            self.current_tag = tag

        # call predecessor
        HTMLParser.handle_starttag(self, tag, method, attrs)

    def start_td(self, attrs):
        """
        This function handles a new column.

        :param attrs: tag attributes
        :return: None
        """

        # add to column count
        self.col += 1

    def end_tr(self):
        """
        This function handles the end of a column.

        :return:
        """

        # check if id was defined
        if 'id' in self.vendor:

            # read id
            identifier = self.vendor['id']

            # check if id is integer
            if identifier.isdigit():

                # cast to integer
                identifier = int(identifier)

                # remove id from vendor data
                del self.vendor['id']

                # store vendor
                self.vendors[identifier] = self.vendor

        # reset column count
        self.col = 0

        # reset vendor
        self.vendor = {}

    def handle_data(self, data):
        """
        This function handles tag data.

        :param data: tag data
        :return: None
        """

        # check if object has handler function for tag
        if self.current_tag is not None and hasattr(self, 'handle_%s' % self.current_tag):

            # call handler
            getattr(self, 'handle_%s' % self.current_tag)(data.rstrip('\r\n'))

        # call predecessor
        HTMLParser.handle_data(self, data)

    def handle_td(self, data):
        """
        This function handles a new column.

        :param data: tag content
        :return: None
        """

        # check if column was defined in order
        if self.col <= len(ROW_ORDER):

            # read current vendor data
            current_data = self.vendor.get(ROW_ORDER[self.col - 1], '')

            # check if data and current data exist
            if current_data and data:

                # add line break
                current_data += '\n'

            # add to current data
            current_data += data

            # store to vendor data
            self.vendor[ROW_ORDER[self.col - 1]] = current_data


def get_vendors():
    """
    This function requests the current vendor list and returns a parsed dictionary

    :return: vendor dictionary
    """

    try:

        # open url
        opener = urlopen(VENDOR_URL)

        # download page
        page = opener.read()

        # create parser
        parser = TableParser()

        # parse page
        parser.feed(page)

        # return vendor dictionary
        return parser.vendors

    except HTTPError as error:

        # check if main
        if __name__ == '__main__':

            # print error
            print error

        # return empty dictionary
        return {}


# execute if main
if __name__ == '__main__':

    # import pretty print
    from pprint import pprint

    # pretty print vendors
    pprint(get_vendors())
