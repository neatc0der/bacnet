# pylint: disable=invalid-name, unused-variable, broad-except, too-many-branches, too-many-arguments
# pylint: disable=no-name-in-module, too-many-statements

"""
Object Basic Module
--------------------

This module contains basic definitions of BACpypes Object.
"""

from __future__ import absolute_import

from multiprocessing import Queue
import os
from tempfile import NamedTemporaryFile
from threading import Thread

from bacpypes.errors import ExecutionError

from bacnet.debugging import bacnet_debug, ModuleLogger

from bacnet.settings import DATA_PATH, SANDBOX_TMP, INTERFACE_SCRIPT

from bacnet.sandbox import get_sandbox_process, sandbox_interact

from .general import register_object_type, ProgramObject


# enable logging
ModuleLogger()


@bacnet_debug
@register_object_type
class ExecProgramObject(ProgramObject):
    """
    This class provides additional functionality for python programs.
    """

    def __init__(self, **kwargs):
        """
        This function initializes the object.

        :return: None
        """

        self._debug('__init__ %r' % kwargs)

        self._exec_file = None

        ProgramObject.__init__(self, **kwargs)

        self._state_queue = Queue()

        self._program = None

        file_name = self.ReadProperty('instanceOf')
        file_name = getattr(file_name, 'value', str(file_name))
        file_name = os.path.join(DATA_PATH, file_name)

        self._source_file = file_name

        self._watchdog_thread = None
        self._halt_thread = None

        self.WriteProperty('programChange', 'ready', direct=True)
        self.WriteProperty('programState', 'idle', direct=True)

    def set_application(self, application):
        """
        This function defines the application associated to this object.

        :param application: application object
        :return: None
        """

        # call predecessor
        ProgramObject.set_application(self, application)

        # check if application object exists
        if application is not None:
            # read object name
            obj_name = self.ReadProperty('instanceOf')
            obj_name = getattr(obj_name, 'value', str(obj_name))

            # get file object by name
            file_obj = application.get_object_by_name(obj_name)

            # check if file object exists
            if file_obj is not None:
                # get file name
                file_name = file_obj.get_filename()

                # set file name
                self._source_file = file_name

    def __del__(self):
        """
        This function handles object deletion.

        :return: None
        """

        self._debug('delete')

        # check if execution file is defined
        if self._exec_file is not None:
            # get current state
            current_state = self.ReadProperty('programState')
            current_state = getattr(current_state, 'value', current_state)

            # check if program is running
            if current_state in ('loading', 'running', 'waiting'):
                # halt program
                self.haltProgram()

            # check if program is loaded
            if current_state != 'idle':
                # unload
                self.unloadProgram()

    def safe_delete(self):
        """
        This function handles safe deletion

        :return: None
        """

        self.__del__()

    def loadProgram(self):
        """
        This function loads the program.

        :return: None
        """

        self._debug('loadProgram')

        try:

            # set state to loading
            self.WriteProperty('programState', 'loading', direct=True)

            # get temp file
            temp_file = NamedTemporaryFile(mode='w', delete=False, dir=SANDBOX_TMP)

            # store file name
            self._exec_file = temp_file.name

            self._debug('created temp file: %s', self._exec_file)

            # read interface and write to temp file
            with open(INTERFACE_SCRIPT, 'r') as interface_file:
                temp_file.file.write(interface_file.read())

            # read source file and write to temp file
            with open(self._source_file, 'r') as source_file:
                temp_file.file.write(source_file.read())

            # close temp file
            temp_file.file.close()

        except Exception as error:
            self._exception(error)

            # set state to halted
            self.WriteProperty('programState', 'idle', direct=True)

            # set reason to loadFailed
            self.WriteProperty('reasonForHalt', 'loadFailed', direct=True)

            return

        self.runProgram()

    def runProgram(self):
        """
        This function runs the program.

        :return: None
        """

        self._debug('runProgram')

        # set state to running
        self.WriteProperty('programState', 'running', direct=True)

        # get relative path to execution file
        exec_file = ''.join(self._exec_file.rpartition('tmp/')[1:])

        # initialize program
        self._program = get_sandbox_process(exec_file)

        # set change state to ready
        self.WriteProperty('programChange', 'ready', direct=True)

        try:
            # start interaction
            sandbox_interact(self._program)

        except Exception as error:
            self._exception(error)

        # set state to halted
        self.WriteProperty('programState', 'halted', direct=True)

        # check if program terminated successfully
        if self._program is None:
            # set reason to internal
            self.WriteProperty('reasonForHalt', 'internal', direct=True)

        elif self._program.poll() != 0:
            # set reason to program
            self.WriteProperty('reasonForHalt', 'program', direct=True)

        else:
            # set reason to normal
            self.WriteProperty('reasonForHalt', 'normal', direct=True)

        # clean up
        self._program = None

        self._debug('runProgram: finished')

    def haltProgram(self):
        """
        This function halts the program.

        :return: None
        """

        self._debug('haltProgram')

        # check if halt thread is still running
        if self._halt_thread is None or not self._halt_thread.isAlive():
            # start thread
            self._halt_thread = Thread(target=self.do_haltProgram)
            self._halt_thread.setDaemon(True)
            self._halt_thread.start()

            self._halt_thread.join(1.0)

            # set reason to internal
            self.WriteProperty('reasonForHalt', 'internal', direct=True)

            # set state to halted
            self.WriteProperty('programState', 'halted', direct=True)

            # set change state to ready
            self.WriteProperty('programChange', 'ready', direct=True)

        else:
            self._debug('halt thread already running')

    def do_haltProgram(self):
        """
        This functions watches over the halt process of the executed program.

        :return: None
        """

        self._debug('running: halt thread')

        # check if program is still running
        if self._program is not None:
            # terminate program
            self._program.kill()

        # check if watchdog is still running
        if self._watchdog_thread is not None and self._watchdog_thread.isAlive():
            # wait for thread to stop
            self._watchdog_thread.join(0.5)

        self._debug('finished: halt thread')

    def unloadProgram(self):
        """
        This function unloads the program.

        :return: None
        """

        self._debug('unloadProgram')

        # set state to unloading
        self.WriteProperty('programState', 'unloading', direct=True)

        # remove temp file
        os.remove(self._exec_file)

        # clean up
        self._exec_file = None

        # set state to idle
        self.WriteProperty('programState', 'idle', direct=True)

    def watchdog(self, *funcs):
        """
        This function watches over the executed program changes.

        :return: None
        """

        self._debug('running: watchdog thread')

        for func in funcs:
            func()

        # set change state to ready
        self.WriteProperty('programChange', 'ready', direct=True)

        self._debug('finished: watchdog thread')

    def WriteProperty(self, prop_id, value, arrayIndex=None, priority=None, direct=False):
        """
        This function writes to property.

        :param prop_id: property identifier
        :param value: value
        :param arrayIndex: index
        :param priority: priority
        :param direct: direct
        :return: None
        """

        # check if program state should be changed
        if prop_id == 'programChange':

            # read state
            new_state = getattr(value, 'value', value)

            # get current change state
            current_change = self.ReadProperty('programChange')

            # get current state
            current_state = self.ReadProperty('programState')
            current_state = getattr(current_state, 'value', current_state)

            self._debug('WriteProperty: change program state to %s', new_state)

            # initializes functions to be executed
            funcs = ()

            # check if object is ready
            if current_change is not None and current_change != 'ready' and value != 'ready':
                raise ExecutionError(errorClass='object', errorCode='busy')

            if new_state == 'load':
                if current_state == 'idle':
                    funcs += (self.loadProgram,)
                elif current_state in ('halted', 'running'):
                    if current_state == 'halted':
                        self.haltProgram()
                    funcs += (self.runProgram,)
                elif current_state in ('loading', 'unloading', 'waiting'):
                    return

            elif new_state == 'run':
                if current_state == 'idle':
                    funcs += (self.loadProgram,)
                elif current_state == 'halted':
                    funcs += (self.runProgram,)
                elif current_state in ('loading', 'running', 'unloading', 'waiting'):
                    return

            elif new_state == 'halt':
                if current_state in ('waiting', 'running'):
                    self.haltProgram()
                return

            elif new_state == 'restart':
                if current_state in ('halted', 'running'):
                    if current_state == 'running':
                        self.haltProgram()
                    funcs += (self.runProgram,)
                elif current_state == 'idle':
                    funcs += (self.loadProgram,)
                else:
                    return

            elif new_state == 'unload':
                if current_state in ('halted', 'waiting', 'running', 'loading'):
                    if current_state in ('running', 'loading'):
                        self.haltProgram()
                    funcs += (self.unloadProgram,)
                else:
                    return

            elif new_state != 'ready':
                self._error('unknown programChange: %s' % new_state)

            if value != 'ready' and value != current_change:
                if (current_change is not None and not funcs) or \
                        (self._watchdog_thread is not None and self._watchdog_thread.is_alive()):
                    raise ExecutionError(errorClass='object', errorCode='internalError')

                elif self._watchdog_thread is None or not self._watchdog_thread.is_alive():
                    # set program change value
                    ProgramObject.WriteProperty(self, prop_id, value, arrayIndex, priority, direct)

                    # start thread
                    self._watchdog_thread = Thread(target=self.watchdog, args=funcs)
                    self._watchdog_thread.setDaemon(True)
                    self._watchdog_thread.start()

            elif value == 'ready':
                # set program change state
                ProgramObject.WriteProperty(self, prop_id, value, arrayIndex, priority, direct)
        else:
            return ProgramObject.WriteProperty(self, prop_id, value, arrayIndex, priority, direct)
