# pylint: disable=invalid-name, unused-variable, too-few-public-methods, import-error, broad-except
# pylint: disable=no-name-in-module

"""
Terra Module
------------------

This module contains Terra Board specific objects.
"""

from __future__ import absolute_import

import os

from bacnet.object.properties import HardwareAccessObject
from bacnet.object.primitivedata import RingList

from bacnet.debugging import ModuleLogger


logger = ModuleLogger(formatter='%(levelname)s:hardware:terra: %(message)s')


USE_DUMMY = True


class New_Daisy20(object):
    """
    DAISY-20 (ADC module)
    """

    max_voltage = 0
    volt_per_point = 0
    adc_path = '/sys/bus/iio/devices/iio:device0/'
    chan_file = 'in_voltage%i_raw'

    def __init__(self, max_voltage=10, bits=10):
        """
        init
        """
        self.max_voltage = max_voltage
        self.volt_per_point = float(max_voltage) / float(2**bits)
        self.last_value_set = 0.0

    def get(self, ch=0):
        """
        get
        """
        with open(os.path.join(self.adc_path, (self.chan_file % ch)), 'r') as fd:
            value = fd.read()

        return int(value)

    def convert(self, bit_value):
        """
        convert
        """

        return float(bit_value) * self.volt_per_point


try:
    # load Terra Board Library
    import ablib

    # check if hardware can be accessed
    DAISY24 = ablib.Daisy24(0, 0x3F)

    # store original Daisy20 (ADC)
    Old_Daisy20 = ablib.Daisy20

    # check if path to new daisy20 exists
    if os.path.exists(Old_Daisy20.adcpath):
        # override Daisy20 adc path
        New_Daisy20.adc_path = Old_Daisy20.adcpath

        # override Daisy20 chan file
        New_Daisy20.chan_file = 'chan%i'

    # replace original Daisy20 (ADC)
    ablib.Daisy20 = New_Daisy20

except Exception as error:
    # print warning
    if USE_DUMMY:
        logger.info('using ablib_dummy')

    # load dummy library
    from . import ablib_dummy as ablib

    # create dummy
    DAISY24 = ablib.Daisy24(0, 0x3F)


DAISY20 = ablib.Daisy20()


class AbstractDaisy20(object):
    """
    This class is an abstraction of the ablib.Daisy20 class.
    """

    identifier = None

    def __init__(self, identifier):
        """
        This function is a constructor for the adc dummies.
        """
        if not identifier in range(4):
            raise ValueError('identifier out of range')

        # store identifier
        self.identifier = identifier

        # get buffer
        self.buffer = RingList(10)

    def get(self):
        """
        This function is a wrapper for the get function.

        :return: voltage
        """

        # get bit value without the last 3 bits
        bit_value = DAISY20.get(self.identifier) & 0x3f8

        # append value to buffer
        self.buffer.append(bit_value)

        # get buffer
        bfr = tuple(buf for buf in self.buffer if buf is not None)

        # set mask to 2^10 - 1
        mask = 0x03ff

        # loop through buffer
        for buffer_value in bfr:
            # mask and buffer value
            mask = mask & buffer_value

        # check if masked bit value is smaller than 0.2
        if DAISY20.convert(mask ^ bit_value) < 0.2:
            # set value to bit value
            value = bit_value

            # store value as last set
            DAISY20.last_value_set = value

        else:
            # get last value
            value = DAISY20.last_value_set

        # return updated value
        return DAISY20.convert(value)


class AbstractDaisy24Button(object):
    """
    This class is an abstraction for buttons of the ablib.Daisy24 class.
    """

    identifier = None

    def __init__(self, identifier):
        """
        This function is a constructor for the button dummies.
        """
        if not identifier in range(4):
            raise ValueError('identifier out of range')

        # store identifier
        self.identifier = identifier

    def get(self):
        """
        This function is a wrapper for the pressed function.

        :return: button pressed
        """

        # return actual value
        return DAISY24.pressed(self.identifier)


class AbstractDaisy24LCD(object):
    """
    This class is an abstraction for lcd of the ablib.Daisy24 class.
    """

    identifier = None
    value = ''

    def __init__(self, identifier=None):
        """
        This function is a constructor for the lcd dummies.
        """

        # store identifier
        self.identifier = identifier
        self.value = ''

    def get(self):
        """
        This function is a providing a value buffer.

        :return: button pressed/not pressed
        """

        # return actual value
        return self.value

    def write(self, value):
        """
        This function is a wrapper for the putstring and setcurpos function

        :return: None
        """

        # format string
        value = value[:32].ljust(32)

        # write to display
        DAISY24.setcurpos(0, 0)
        DAISY24.putstring(value[:16])
        DAISY24.setcurpos(0, 1)
        DAISY24.putstring(value[16:])

        # store value
        self.value = value

        # return value
        return value


class AbstractDaisy24Backlight(object):
    # pylint: disable=no-self-use
    """
    This class is an abstraction for backlight of the ablib.Daisy24 class.
    """

    def __init__(self, identifier=None):
        """
        This function is a constructor for the backlight dummies.
        """

        # store identifier
        self.identifier = identifier

    def get(self):
        """
        This function is a wrapper for the backled.get function.

        :return: led on/off
        """

        # return actual value
        return DAISY24.backled.get()

    def on(self):
        """
        This function is a wrapper for the backled.on function.

        :return: None
        """

        # turn on backlight
        return DAISY24.backled.on()

    def off(self):
        """
        This function is a wrapper for the backled.off function.

        :return: None
        """

        # turn off backlight
        return DAISY24.backled.off()


# check if hardware is supported or dummies are allowed
if USE_DUMMY or not hasattr(ablib, 'ABLIB_Dummy'):
    HARDWARE_LIST = (
        {
            # TODO: trigger support
            'name': 'ADC',
            'hardware': tuple(
                HardwareAccessObject(AbstractDaisy20(i))
                for i in xrange(4)
            ),
            'objectType': 'analogInput',
            'poll': 0.2,
            'initials': {
                'objectName': '{module}_adc_ad{index}',
                'description': '{Module} Daisy20 ADC AD{index}',
            },
        },
        {
            'name': 'Button',
            'hardware': tuple(
                HardwareAccessObject(AbstractDaisy24Button(i)) for i in xrange(0, 4)
            ),
            'objectType': 'binaryInput',
            'poll': 0.05,
            'initials': {
                'objectName': '{module}_button_key{index}',
                'description': '{Module} Daisy24 Button {index}',
            },
        },
        {
            'name': 'Backlight',
            'hardware': HardwareAccessObject(AbstractDaisy24Backlight(), write=True),
            'objectType': 'binaryOutput',
            'initials': {
                'objectName': '{module}_led_backlight',
                'description': '{Module} Daisy24 Backlight LED',
            },
        },
        {
            'name': 'LED',
            'hardware': tuple(
                HardwareAccessObject(ablib.Daisy11('D11', 'L%i' % i), write=True)
                for i in xrange(1, 9)
            ),
            'objectType': 'binaryOutput',
            'initials': {
                'objectName': '{module}_led_l{index1}',
                'description': '{Module} Daisy11 LED L{index1}',
            },
        },
        {
            'name': 'Switch',
            'hardware': tuple(
                HardwareAccessObject(ablib.Daisy19('D14', 'first', 'CH%i' % i))
                for i in xrange(1, 5)
            ),
            'objectType': 'binaryOutput',
            'initials': {
                'objectName': '{module}_switch_ch{index1}',
                'description': '{Module} Daisy19 Switch CH{index1}',
            },
        },
        {
            'name': 'LCD',
            'hardware': HardwareAccessObject(AbstractDaisy24LCD(), write=True),
            'objectType': 'characterstringValue',
            'initials': {
                'objectName': '{module}_lcd',
                'description': '{Module} Daisy24 LCD 16x2',
            },
        },
    )
