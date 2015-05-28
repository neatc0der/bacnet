# pylint: disable=too-few-public-methods, invalid-name, unused-argument, no-self-use

"""
Terra_Board ABLIB_Dummy Module
------------------------------

This module contains dummy classes for hardware abstraction.
"""

from bacnet.debugging import bacnet_debug, ModuleLogger


ModuleLogger(level='INFO')


@bacnet_debug(formatter='%(levelname)s:%(module)s: %(message)s')
class ABLIB_Dummy(object):
    """
    This class is a generic dummy class.
    """

    name = ''
    identifier = None

    def __init__(self, *args, **kwargs):
        """
        This function is a generic dummy constructor.
        """

        pass

    def __repr__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return u'<%s.%s  \'%s %s\'>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.name,
            self.identifier,
        )

    def __str__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()

    def __unicode__(self):
        """
        This function returns a unicode representation of the instance.

        :return: unicode representation
        """
        return self.__repr__()


class BinaryReadDummy(ABLIB_Dummy):
    """
    This class is a dummy for reading binary values.
    """

    # define initial value
    value = False

    def get(self, identifier=None):
        """
        This function is a dummy for getting the led status.
        """

        # get name
        name = self.name

        # add identifier
        if identifier is not None:
            name = '%s %s' % (name, str(identifier))

        elif self.identifier is not None:
            name = '%s %s' % (name, str(self.identifier))

        # print info
        # self._info('%s - %s: get() <- %s' % (self.__class__.__name__, name, self.value))

        # return value
        return self.value


class BinaryWriteDummy(BinaryReadDummy):
    """
    This class is a dummy for reading and writing binary values
    """

    def on(self, identifier=None):
        """
        This function is a dummy for turning on the led.
        """

        # set value
        self.value = True

        # get name
        name = self.name

        # add identifier
        if identifier is not None:
            name = '%s %s' % (name, str(identifier))

        elif self.identifier is not None:
            name = '%s %s' % (name, str(self.identifier))

        # print info
        self._info('%s - %s: on()' % (self.__class__.__name__, name))

    def off(self, identifier=None):
        """
        This function is a dummy for turning off the led.
        """

        # set value
        self.value = False

        # get name
        name = self.name

        # add identifier
        if identifier is not None:
            name = '%s %s' % (name, str(identifier))

        elif self.identifier is not None:
            name = '%s %s' % (name, str(self.identifier))

        # print info
        self._info('%s - %s: off()' % (self.__class__.__name__, name))


class Daisy11(BinaryWriteDummy):
    """
    This class is a dummy for the terra board's led array.
    """

    # define name
    name = 'LED'

    def __init__(self, connector_id, led_id):
        """
        This function is a dummy constructor.
        """

        # set id
        self.identifier = led_id

        # call predecessor
        super(self.__class__, self).__init__(self, connector_id, led_id)


class Daisy19(BinaryWriteDummy):
    """
    This class is a dummy for the terra board's 4 channel output switch.
    """

    # define name
    name = 'Output'

    def __init__(self, connector_id, position, output_id):
        """
        This function is a dummy constructor.
        """

        # set id
        self.identifier = output_id

        # call predecessor
        super(self.__class__, self).__init__(self, connector_id, position, output_id)


class Daisy20(BinaryReadDummy):
    """
    This class is a dummy for the terra board's adc.
    """

    # define name
    name = 'ADC'

    def convert(self, value):
        """
        This function is a dummy to convert the bit value into voltage.

        :param value: bit value
        :return: voltage
        """

        return float(value)


class Daisy22(BinaryWriteDummy):
    """
    This class is a dummy for the terra board's backlight led of the lcd display.
    """

    # define name
    name = 'Backlight LED'


class Daisy24(ABLIB_Dummy):
    """
    This class is a dummy for the terra board's lcd display and button array.
    """

    backled = Daisy22()
    name = 'LCD'

    def setcurpos(self, x, y):
        """
        This function is a dummy for setting the cursor on the LCD display.

        :param x: x position
        :param y: y position
        :return: None
        """

        # print info
        self._info(
            '%s - %s set cursor: x=%i, y=%i' %
            (self.__class__.__name__, self.name, x, y)
        )

    def putstring(self, value):
        """
        This function is a dummy for putting a string to the LCD display.

        :param value: string
        :return: None
        """

        # print info
        self._info('%s - %s put: %r' % (self.__class__.__name__, self.name, value))

    def pressed(self, keyid):
        """
        This function is a dummy for checking pressed buttons.

        :param keyid: button id
        :return: button pressed
        """

        # print info
        # self._info(
        #     '%s - %s key: get(%s) <- False' %
        #     (self.__class__.__name__, self.name, keyid)
        # )

        # always return false
        return False
