# pylint: disable=invalid-name

"""
Control URL Module
------------------

This module contains the description of all app based pages on the web interface.
"""

from django.conf.urls import patterns, url


# define update url
OBJECT_UPDATE_URL = 'devices/update/'


# define url patterns
urlpatterns = patterns(
    'control.views',

    url(r'^$', 'index', name='index'),

    url(r'^devices/$', 'devices.index', name='devices'),
    url(r'^devices/data/$', 'devices.ajax', name='device_data'),
    url(r'^%s$' % OBJECT_UPDATE_URL, 'access.update', name='device_update'),
)
