# pylint: disable=bare-except, broad-except, too-few-public-methods

"""
Debugging Log Module
--------------------

This module contains necessary objects to support logging in multiprocessing environments.
"""

import threading
import traceback
import sys
from logging import Formatter, BASIC_FORMAT, Handler
from logging.handlers import RotatingFileHandler

from bacpypes.debugging import DebugContents

if sys.version_info[0] < 3:
    import cStringIO as io
else:
    import io


class LoggingFormatter(Formatter):
    """
    This class is a wrapper for logging formatter to support coloring.
    """

    def __init__(self, fmt=None, color=None):
        """
        This function initializes the color.

        :param color: color number
        :return: None
        """

        Formatter.__init__(self, fmt if fmt is not None else BASIC_FORMAT, None)

        # check the color
        if color is not None:
            if color not in range(8):
                raise ValueError('colors are 0 (black) through 7 (white)')

        # store color
        self.color = color

    def format(self, record):
        """
        This function formats the message.

        :param record: logging record
        :return: message text
        """

        try:
            # use the basic formatting
            msg = Formatter.format(self, record) + '\n'

            # look for detailed arguments
            for arg in record.args:
                if isinstance(arg, DebugContents):
                    if msg:
                        sio = io.StringIO()
                        sio.write(msg)
                        msg = None
                    sio.write('   %r\n' % (arg,))
                    arg.debug_contents(indent=2, file=sio)

            # get the message from the StringIO buffer
            if not msg:
                msg = sio.getvalue()

            # trim off the last '\n'
            msg = msg[:-1]

        except Exception as error:
            record_attrs = [
                attr + ': ' + str(getattr(record, attr, 'N/A'))
                for attr in
                ('name', 'level', 'pathname', 'lineno', 'msg', 'args', 'exc_info', 'func')
            ]
            record_attrs[:0] = ["LoggingFormatter exception: " + str(error)]
            msg = '\n   '.join(record_attrs)

        # set color if defined
        if self.color is not None:
            msg = '\x1b[%dm' % (30+self.color,) + msg + '\x1b[0m'

        # return message
        return msg


class MultiProcessingLog(Handler):
    """
    This class sends logs to queues.
    """
    def __init__(self, name, mode='a', maxsize=0, backupcount=0, **kwargs):
        """
        This function initializes the handler object.
        :param name: name
        :param mode: mode
        :param maxsize: maximum size
        :param backupcount: backup count
        :return:
        """

        Handler.__init__(self)

        self._handler = None

        self.queue = kwargs.get('queue', None)
        self.obj = kwargs.get('obj', None)

        # check if queue was defined
        if self.queue is None and self.obj is None:
            raise AttributeError('missing queue!')

        self.stream = kwargs.get('stream', None)

        if kwargs.get('thread', False):
            self._handler = RotatingFileHandler(name, mode, maxsize, backupcount)

            receive_thread = threading.Thread(target=self.receive)
            receive_thread.daemon = True
            receive_thread.start()

    def setFormatter(self, fmt):
        """
        This function sets the formatter.

        :param fmt: formatter instance
        :return:
        """

        Handler.setFormatter(self, fmt)

    def receive(self):
        """
        This function polls for received logs.

        :return: None
        """

        while hasattr(self.queue, 'get'):
            try:
                record = self.queue.get()

            except:
                continue

            try:
                if self._handler is not None:
                    self._handler.stream.write(u'%s\n' % record)
                    self._handler.flush()

                # write to stream
                if self.stream is not None:
                    self.stream.write(u'%s\n' % record)
                    self.flush()

            except EOFError:
                break

            except:
                traceback.print_exc(file=sys.stderr)

            finally:
                if hasattr(self.queue, 'task_done'):
                    self.queue.task_done()

    def send(self, record):
        """
        This function queues the message.

        :param record: message
        :return: None
        """

        if self.queue is None:
            log_queue = getattr(self.obj, 'log', None)
            if log_queue is None:
                raise ValueError('queue is not defined')
            self.queue = log_queue

        self.queue.put_nowait(record)

    def emit(self, record):
        """
        This function sends the message to queue.

        :param record: message
        :return: None
        """

        try:
            record = self.format(record)
            self.send(record)

        except (KeyboardInterrupt, SystemExit):
            raise

        except:
            self.handleError(record)

    def close(self):
        """
        This function closes the handler.

        :return: None
        """

        if self._handler is not None:
            self._handler.close()

        Handler.close(self)
