# pylint: disable=broad-except, import-error, super-on-old-class, star-args, too-many-branches
# pylint: disable=too-many-statements, no-member

"""
PyPy Interact Module
--------------------

This module provides execution command to the pypy sandbox.
"""

from __future__ import absolute_import

import os
import sys

from bacnet.debugging import ModuleLogger

from rpython.translator.sandbox.sandlib import SimpleIOSandboxedProc, VirtualizedSandboxedProc,\
    read_message, write_message, write_exception, shortrepr
from rpython.translator.sandbox.vfs import Dir, RealDir, RealFile
import pypy


# enable logging
ModuleLogger()


# set environment variables
LIB_ROOT = os.path.dirname(os.path.dirname(pypy.__file__))


class PyPySandboxProcess(VirtualizedSandboxedProc, SimpleIOSandboxedProc):
    """
    This class provides sandbox process execution.
    """
    argv0 = '/bin/pypy-c'
    virtual_cwd = '/tmp'
    virtual_env = {}
    virtual_console_isatty = True

    api_access = None

    access_granted = False

    def __init__(self, executable, arguments, tmpdir=None, debug=True):
        """
        This function initializes the sandbox process object.

        :param executable: path to pypy sandbox executable
        :param arguments: arguments for sandbox environment
        :param tmpdir: temp directory
        :param debug: debugging
        """

        self.executable = executable = os.path.abspath(executable)
        self.tmpdir = tmpdir
        self.debug = debug
        super(PyPySandboxProcess, self).__init__([self.argv0] + arguments, executable=executable)

        from bacnet.api import BACnetAPI
        self.api_access = BACnetAPI()

    def do_transmit(self, line):
        """
        This function handles manager access for the pypy sandbox environment.

        :param line: command
        :return: None
        """

        if self.api_access is not None:
            self.api_access.send(self.api_access.create(line))

    def handle_until_return(self):
        """
        This function is being executed until the subprocess returns.

        :return:
        """
        child_stdin = self.popen.stdin
        child_stdout = self.popen.stdout
        if self.os_level_sandboxing and sys.platform.startswith('linux'):
            # rationale: we wait until the child process started completely,
            # letting the C library do any system calls it wants for
            # initialization.  When the RPython code starts up, it quickly
            # does its first system call.  At this point we turn seccomp on.
            import select
            select.select([child_stdout], [], [])
            file_descriptor = open('/proc/%d/seccomp' % self.popen.pid, 'w')
            print >> file_descriptor, 1
            file_descriptor.close()

        while True:
            try:
                fnname = read_message(child_stdout, timeout=0.01)
                args = read_message(child_stdout)
            except EOFError:
                try:
                    apdu = self.api_access.receive(False)
                    while apdu is not None:
                        write_message(child_stdin, 0)
                        write_message(child_stdin, self.api_access.parse(apdu))
                        child_stdin.flush()
                        apdu = self.api_access.receive(False)

                except IOError:
                    break

                except Exception:
                    pass

                continue

            except Exception:
                break
            if self.log and not self.is_spam(fnname, *args):
                self.log.call(
                    '%s(%s)' % (
                        fnname,
                        ', '.join([shortrepr(x) for x in args])
                    )
                )
            try:
                answer, resulttype = self.handle_message(fnname, *args)
            except Exception as error:
                trace = sys.exc_info()[2]
                write_exception(child_stdin, error, trace)
                if self.log:
                    if str(error):
                        self.log.exception('%s: %s' % (error.__class__.__name__, error))
                    else:
                        self.log.exception('%s' % (error.__class__.__name__,))
            else:
                if self.log and not self.is_spam(fnname, *args):
                    self.log.result(shortrepr(answer))
                try:
                    write_message(child_stdin, 0)  # error code - 0 for ok
                    write_message(child_stdin, answer, resulttype)
                    child_stdin.flush()
                except (IOError, OSError):
                    # likely cause: subprocess is dead, child_stdin closed
                    if self.poll() is not None:
                        break
                    else:
                        raise

        returncode = self.wait()
        return returncode

    def build_virtual_root(self):
        """
        This function builds a virtual file system. Access to own executable, pure python libraries
        and temporary directory is granted.
        """

        exclude = ['.pyc', '.pyo']

        if self.tmpdir is None:
            tmpdirnode = Dir({})

        else:
            tmpdirnode = RealDir(self.tmpdir, exclude=exclude)

        libroot = str(LIB_ROOT)

        return Dir({
            'bin': Dir({
                'pypy-c': RealFile(self.executable, mode=0111),
                'lib-python': RealDir(os.path.join(libroot, 'lib-python'), exclude=exclude),
                'lib_pypy': RealDir(os.path.join(libroot, 'lib_pypy'), exclude=exclude),
            }),
            'tmp': tmpdirnode,
        })
