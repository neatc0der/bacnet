#pylint: disable=no-name-in-module, bare-except

"""
Handler Helper Module
-------------------------

This module provides access to local interface addresses.
"""

from __future__ import absolute_import

from netifaces import interfaces, ifaddresses, AF_INET


def __netmask_to_bits(netmask):
    """
    This function converts a ip_address netmask to its related bit count.

    :param netmask: ip_address netmask
    :return: bit_count
    """
    bit_count = len(''.join([bin(int(x))[2:] for x in netmask.split('.')]).split('0')[0])

    # returns bit_count
    return bit_count


def get_local_ip(interface):
    """
    This function retrieves an IP address from the defined interface.

    :param interface: network interface for IP address retrieval
    :return: ip_address
    """
    ip_address = None

    try:
        # check if interface exists
        if interface in interfaces():
            idata = ifaddresses(interface).setdefault(AF_INET, [])[0]
            ip_address = idata.get('addr', None)
            netmask = idata.get('netmask', None)

    except:
        ip_address = None

    # no ip_address was retrieved
    if ip_address is None or netmask is None:
        return None

    netmask = __netmask_to_bits(netmask)

    # return IP address including netmask
    return '%s/%i' % (ip_address, netmask)
