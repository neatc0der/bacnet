"""
App Settings Module
------------------

This module contains app specific definitions for Django settings.
"""

import os

# get important directory locations
SETTINGS_DIR = os.path.dirname(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(SETTINGS_DIR)
APP_DIR = os.path.join(BASE_DIR, '%s')
TEMPLATE_DIR = os.path.join(BASE_DIR, '{0}/templates/{0}')


# define applications
ACTIVE_APPS_DICT = {
    'control': {
        'prefix': r'',
    },
}


# get tuple of active applications
ACTIVE_APPS = tuple(ACTIVE_APPS_DICT.keys())


# define additional applications
ADDITIONAL_APPS = ()
