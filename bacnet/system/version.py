# pylint: disable=broad-except, star-args

"""
BACnet System Version Module
----------------------------

This module handles version printing and normalizing according to PEP 386.
"""

from __future__ import absolute_import

import subprocess

from verlib import NormalizedVersion


__author__ = 'Tobias Grosch'
__program__ = 'BACnet Controller Software'
__version__ = ((0, 4), ('c', 0))


def create_version(version):
    """
    This function is a verlib wrapper to create necessary version and git information.

    :param version: get current version tuple
    :return: full_version, git_info
    """
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.STDOUT,
        )
        git_changes = 'modified' in subprocess.check_output(
            ["git", "status"],
            stderr=subprocess.STDOUT,
        )
        gitless_version = 'v%s' % str(NormalizedVersion.from_parts(*version))

    except Exception:
        git_commit = None

    # pack git information
    git = (git_commit,)

    if git_commit is not None:
        try:
            git_count = subprocess.check_output(
                ["git", "rev-list", "%s..HEAD" % gitless_version, '--count'],
                stderr=subprocess.STDOUT,
            )
            git_count = git_count.split('\n')[0]

            if not git_count.isdigit():
                git_count = '0'

        except Exception:
            git_count = '0'

        git += (git_changes, git_count)
        version += (('dev', git_count),)

    version = 'v%s' % str(NormalizedVersion.from_parts(*version))

    # return full version and git information
    return version, git


__version__, __git_info__ = create_version(__version__)


VERSION_TEXT = None


def get_version():
    # pylint: disable=global-statement
    """
    This function returns current version string and exits program.

    :return: None
    """

    global VERSION_TEXT

    # check if version was created
    if VERSION_TEXT is not None:
        return VERSION_TEXT

    # read version
    version = str(__version__)

    # specify version
    if len(__git_info__) > 1:
        git_commit = __git_info__[0][:6]
        if __git_info__[1]:
            git_commit += '-post'
        version += ' (commit: %s)' % git_commit

    # store version
    VERSION_TEXT = '%s by %s: %s' % (__program__, __author__, version)

    # return version
    return VERSION_TEXT
