# pylint: disable=global-statement

"""
Object Define Module
--------------------

This module contains user specific definitions of BACpypes Object and a list to collect all builtin
Objects needed.
"""

from __future__ import absolute_import

from bacnet.debugging import ModuleLogger

from .basic import StreamAccessFileObject, ExecProgramObject


ModuleLogger(level='INFO')


OBJECT_LIST = None


def get_initial_object_list():
    """
    This function creates the object list.

    :return: object list
    """

    global OBJECT_LIST

    # check if object list was generated already
    if OBJECT_LIST is not None:

        # return object list
        return OBJECT_LIST

    # create object list
    OBJECT_LIST = [
        StreamAccessFileObject(
            objectIdentifier=('file', 1),
            objectName='configuration',
            description='Python File for Autonomous Operation',
            readOnly=False,
            fileType='text/x-python',
        ),
        ExecProgramObject(
            objectIdentifier=('program', 1),
            objectName='control',
            description='Control for Autonomous Operation',
            reasonForHalt='normal',
            instanceOf='configuration',
            reliability='noFaultDetected',
            outOfService=False,
        ),
    ]

    # return object list
    return OBJECT_LIST
