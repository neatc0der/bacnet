# pylint: disable=invalid-name

"""
WebGUI URL Module
------------------

This module contains the description of all available pages on the web interface.
"""

from django.conf.urls import patterns, include
from django.conf import settings
from sys import stderr


urlpatterns = patterns('',)


# add new patterns from active apps
for app_name in settings.ACTIVE_APPS:
    # get app dictionary
    app_dict = settings.ACTIVE_APPS_DICT.get(app_name, {})
    # get app pattern
    app_pattern = app_dict.get('prefix', app_name.replace('.', '-'))

    # get namespace
    namespace = app_dict.get('namespace', app_name.replace('.', '-'))

    try:
        # import urls
        urls = __import__('%s.urls' % app_name)

        # append patterns to url patterns
        urlpatterns += patterns(
            '',
            (app_pattern, include('%s.urls' % app_name, app_name=app_name, namespace=namespace)),
        )

    except ImportError as error:
        # print error
        stderr.write('error on loading %s.urls: %s' % (app_name, error))
