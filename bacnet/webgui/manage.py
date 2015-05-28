#!/usr/bin/env python

"""
Manage Module
-------------

This module manages the django environment and process start up.
"""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webgui.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
