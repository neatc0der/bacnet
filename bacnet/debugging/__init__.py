# pylint: disable=broad-except, too-few-public-methods, invalid-name, too-many-arguments
# pylint: disable=too-many-branches, global-statement

"""
Debugging Module
----------------

This module contains basic debugging functionality.
"""

from datetime import datetime
import dateutil.tz
import inspect
import logging
from multiprocessing.queues import JoinableQueue
from threading import Lock, Event
import time

from bacnet.debugging.log import LoggingFormatter, MultiProcessingLog

LOGGER = []

LOG_HANDLER = None
LOG_QUEUE = None


class TimeoutJoinableQueue(JoinableQueue):
    """
    This class is an updated version of JoinableQueue with join timeout.
    """

    def __init__(self, *args, **kwargs):
        """
        This function initializes the object.
        """
        # call predecessor
        JoinableQueue.__init__(self, *args, **kwargs)

        # initialize lock and event
        self.all_tasks_done = Lock()
        self.all_tasks_done_event = Event()

    def join(self, timeout=None):
        # pylint: disable=arguments-differ
        """
        This function overrides the join function with timeout support.
        """

        self.all_tasks_done.acquire()

        try:
            endtime = time.time() + timeout
            while not self._unfinished_tasks._semlock._is_zero():
                remaining = endtime - time.time()
                if remaining <= 0.0:
                    raise Exception

                self.all_tasks_done_event.wait(remaining)

        except Exception:
            pass

        finally:
            self.all_tasks_done.release()


def iso_now():
    """
    This function returns current time in iso format.

    :return: time in iso format
    """

    return datetime.utcnow().replace(tzinfo=dateutil.tz.tzutc()).isoformat()


def get_formatter(color=None):
    """
    This function returns a logging formatter instance.

    :param color: set color
    :return: logging formatter
    """
    return LoggingFormatter('%(levelname)s:%(filename)s:%(lineno)04d:%(name)s: %(message)s', color)


def get_loggers(prefix=None):
    """
    This function returns the list of all loggers.

    :return: list of loggers
    """

    # get all loggers
    loggers = list(logging.Logger.manager.loggerDict.keys())

    # filter loggers by prefix
    if prefix is not None:
        loggers = list(l for l in loggers if l.startswith(prefix))

    # sort loggers
    loggers.sort()

    # return loggers
    return loggers


def set_handler(name, **kwargs):
    """
    This function assigns logging handler to certain loggers.

    :param name: logger name
    :return: None
    """

    details = kwargs.get('details', None)
    color = kwargs.get('color', None)
    level = kwargs.get('level', logging.ERROR)
    formatter = kwargs.get('formatter', True)
    init = kwargs.get('init', None)
    obj = kwargs.get('obj', None)
    queue = getattr(LOG_HANDLER, 'queue', LOG_QUEUE)

    # get logger by name
    logger = logging.getLogger(name)

    # remove all handlers
    for handler_obj in logger.handlers:
        if formatter is None and logger.handlers[0] == handler_obj:
            formatter = handler_obj.formatter

        handler_obj.close()
        logger.removeHandler(handler_obj)

    # check for preset level
    if init is True and 1 < logger.level < level:
        level = logger.level

    # create handler
    hdlr = MultiProcessingLog('%s.log' % name.split('.')[0], queue=queue, obj=obj)
    hdlr.setLevel(level)

    # set formatter if color is set
    if formatter is True or (formatter is None and len(logger.handlers) == 0):
        hdlr.setFormatter(
            get_formatter(color)
        )

    elif not formatter in (False, None):
        if isinstance(formatter, LoggingFormatter):
            hdlr.setFormatter(formatter)
        else:
            hdlr.setFormatter(LoggingFormatter(formatter, color))

    # set details
    if details is not None:
        globs = getattr(logger, 'globs', None)
        if globs is not None:
            globs['_debug'] = details

        if not init:
            for logger_name in get_loggers():
                if logger_name.startswith(name) and logger_name != name:
                    set_handler(logger_name, **kwargs)

    # add handler to logger
    logger.addHandler(hdlr)

    # do not propagate
    logger.propagate = False

    # set logging level
    logger.setLevel(level)


def bacnet_debug(func=None, formatter=True, level=None):
    """
    This function is a decorator for objects to add debugging methods.

    :param formatter: set formatter string
    :param level: set log level
    :return: updated object
    """

    def wrapper(obj):
        """
        This function is a decorator wrapper.

        :param obj: object
        :return: updated object
        """

        # set name
        name = '%s.%s' % (obj.__module__, obj.__name__)

        # create a logger for this object
        logger = logging.getLogger(name)

        # get module logger
        module_logger = logging.getLogger(obj.__module__)

        # set new level
        new_level = module_logger.level if level is None else level

        # set new handler
        set_handler(name, level=new_level, formatter=formatter, obj=obj)

        # do not propagate
        logger.propagate = False

        # make it available to instances
        obj._logger = logger
        obj._debug = logger.debug
        obj._info = logger.info
        obj._warning = logger.warning
        obj._error = logger.error
        obj._exception = logger.exception
        obj._fatal = logger.fatal

        return obj

    if func is None:
        return wrapper

    else:
        return wrapper(func)


def set_debug(args=None, stream=None):
    """
    This function sets basic logging parameters.

    :param args: arguments
    :return: log queue
    """

    global LOG_HANDLER

    level = logging.ERROR
    bug_list = []

    if args is not None:
        # check if log level was defined
        if hasattr(args, 'level') and args.level is not None:
            if args.level.isdigit():
                level = int(args.level)
            else:
                level = args.level.upper()

        # check for debug
        if args.debug is None:
            # --debug not specified
            bug_list = []
        elif not args.debug:
            # --debug, but no arguments
            bug_list = ["bacnet"]
        else:
            # --debug with arguments
            bug_list = args.debug

        # disable stream output if quiet is requested
        if not args.verbose:
            stream = None

    loggers = get_loggers()
    for logger in loggers:
        set_handler(logger, level=level, formatter=None, init=True)

    log_queue = LOG_QUEUE

    if LOG_HANDLER is None:
        LOG_HANDLER = MultiProcessingLog('bacnet.log', stream=stream, queue=log_queue, thread=True)
        LOG_HANDLER.level = level
        LOG_HANDLER.formatter = LoggingFormatter(
            get_formatter()
        )

        logging.root.handlers[0].close()
        logging.root.handlers[0] = LOG_HANDLER

    # set level for buggers to debug
    if level > logging.DEBUG:
        level = logging.DEBUG

    # attach any that are specified
    if args is not None and hasattr(args, 'color') and args.color:
        for i, debug_name in enumerate(bug_list):
            set_handler(debug_name, details=1, level=level, color=(i % 6) + 2)
    else:
        for debug_name in bug_list:
            set_handler(debug_name, details=1, level=level)

    return log_queue


def ModuleLogger(context=None, details=0, level=None, module_name=None, formatter=True):
    """
    This function creates a general logger.

    :return: None
    """

    # check if context was defined
    if context is None:
        # get frame
        frame = inspect.stack()[1][0]

        # read globals
        globs = frame.f_globals

    else:
        # get globals
        globs = context

    # read module name
    name = globs['__name__'] if module_name is None else module_name

    # create a logger to be assigned to _log
    logger = logging.getLogger(name)

    # put in a reference to the module globals
    logger.globs = globs

    # set global variables
    globs['_debug'] = details
    globs['_log'] = logger

    global LOG_QUEUE

    if LOG_QUEUE is None:
        LOG_QUEUE = TimeoutJoinableQueue()

    set_handler(
        name,
        level=level if level is not None else logging.root.level,
        formatter=formatter,
        init=True
    )

    LOGGER.append(logger)

    return logger
