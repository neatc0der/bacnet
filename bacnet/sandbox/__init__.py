# pylint: disable=broad-except

"""
Sandbox Module
--------------

This module contains handlers for the pypy sandbox environment.
"""

from __future__ import absolute_import

import os
import platform

from bacnet.debugging import bacnet_debug, ModuleLogger

try:
    from .process import PyPySandboxProcess

except ImportError:
    PyPySandboxProcess = None

# enable logging
ModuleLogger()


# set environment variables
STARTDIR = os.getcwd()
SANDBOX = 'bacnet/sandbox/pypy/pypy/sandbox'
SANDBOX_TMP = 'tmp'
SANDBOX_COMPILED = '../goal/%s/pypy-c'


def get_platform_name():
    """
    This function returns the platform name.

    :return: platform name
    """

    # get system
    system = platform.system().lower()

    # get architecture
    machine = platform.machine()

    # check if machine is arm with hard float
    if machine.startswith('armv7'):
        # reset machine description
        machine = 'armhf'

    # check if machine is arm with soft float
    elif machine.startswith('arm'):
        # reset machine description
        machine = 'armel'

    # return platform name
    return '%s-%s' % (system, machine)


# set platform name
PLATFORM_NAME = get_platform_name()


@bacnet_debug
def sandbox_support(platform_name=PLATFORM_NAME):
    """
    This function checks if compiled sandbox version of pypy exists for this system.

    :return: sandbox is supported on this system
    """

    # get path to executable
    if os.getcwd().endswith('sandbox'):
        executable = SANDBOX_COMPILED % platform_name

    else:
        executable = os.path.realpath(os.path.join(SANDBOX, SANDBOX_COMPILED)) % platform_name

    sandbox_support._debug('checking for sandbox executable: %s', executable)

    # return if sandbox is supported
    return os.path.exists(executable)


@bacnet_debug
def get_sandbox_process(executable):
    """
    This function returns a sandbox process object.

    :param executable: relative path to untrusted executable
    :return: sandbox process
    """

    self = get_sandbox_process

    # print platform info
    self._debug('platform: %s', PLATFORM_NAME)

    # get path to sandbox
    sandbox_executable = SANDBOX_COMPILED % PLATFORM_NAME

    # check if sandbox version is supported
    if not sandbox_support():
        # print error
        self._error('sandboxing unsupported: changing to pypy without sandboxing (DANGEROUS!)')

        # get path to pypy
        sandbox_executable = os.popen('which pypy').read().strip('\r\n')

        # check if pypy was found
        if not sandbox_executable:
            self._error('pypy not found')
            return


    # initialize sandbox process
    sandbox_process = None

    try:
        # change to sandbox directory
        os.chdir(SANDBOX)

        # create sandbox process
        sandbox_process = PyPySandboxProcess(
            sandbox_executable,
            [
                # '--heapsize',
                # str(50 * 1024 * 1024),
                executable,
            ],
            tmpdir=SANDBOX_TMP,
            debug=False,
        )

    finally:
        # return to execution directory
        os.chdir(STARTDIR)

    self._debug('sandbox process: %s', sandbox_process)

    # return sandbox process
    return sandbox_process


@bacnet_debug
def sandbox_interact(sandbox_process):
    """
    This function interacts with the sandbox process.

    :param sandbox_process: sandbox process object
    :return: None
    """

    self = sandbox_interact

    self._debug('process interaction started')

    # check is sandbox process was defined
    if sandbox_process is not None:
        try:
            # start interaction
            sandbox_process.interact()

        finally:
            # kill process
            sandbox_process.kill()

    self._debug('process stopped')
