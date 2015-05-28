# pylint: disable=undefined-variable, invalid-name, broad-except

"""
This exampe displays the voltage on ch1 to ch4 on lcd depending on which button was pressed.
"""

from time import time as current_time

map_output = {
    # (object type, instance, property index): 'object_type instance'
    ('binaryInput', 1, None): 'binaryOutput 2',
    ('binaryInput', 2, None): 'binaryOutput 3',
    ('binaryInput', 3, None): 'binaryOutput 4',
    ('binaryInput', 4, None): 'binaryOutput 5',
}

last_display_write = current_time()

# set display value
display_value = ('analogInput', 1)

# initial reading of analogInput 1
transmit('read 1 %s %i presentValue' % display_value)

# do forever
while True:
    try:
        # wait for new messages
        parsed_data = receive()

        # check if data is a dictionary
        if not isinstance(parsed_data, dict):
            # ignore message
            continue

        # check if message is a value information
        if parsed_data['class'] in ('ConfirmedCOVNotificationRequest', 'ReadPropertyMultipleACK',
                                    'ReadPropertyACK', 'UnconfirmedCOVNotificationRequest'):
            # get message content
            content = parsed_data['content']

            # loop through output map
            for input, output in map_output.iteritems():
                # check if input value type is defined in content
                if input[0] in content:
                    # check if input value identifier is defined in content
                    if input[1] in content[input[0]]:
                        # check if present value was defined
                        if 'presentValue' in content[input[0]][input[1]]:
                            # get value
                            value = content[input[0]][input[1]]['presentValue'][input[2]]

                            # request value update to output
                            transmit('write 1 %s presentValue %s' % (output, value))

                            # check if value is active
                            if value == 'active':
                                # set object instance
                                display_value = (display_value[0], input[1])

                                # request present value
                                transmit('read 1 %s %i presentValue' % display_value)

            # check if object instance is defined in content
            if display_value[0] in content and display_value[1] in content[display_value[0]]:
                # check if update time is not to short
                if current_time() - last_display_write > 0.5 and \
                    'presentValue' in content[display_value[0]][display_value[1]]:
                    # reset current time
                    last_display_write = current_time()

                    # get current value
                    value = content[display_value[0]][display_value[1]]['presentValue'][None]

                    # request display value update
                    transmit(
                        'write 1 characterstringValue 1 presentValue "%s %i:  %s"' % (
                            display_value + (value,)
                        )
                    )

    except Exception:
        pass
