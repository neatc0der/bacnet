# pylint: disable=undefined-variable, invalid-name, broad-except

"""
This example turns on LED L1 on Daisy 11 when pressing key0 on Daisy 24.
"""

map_output = {
    # (object type, instance, property index): 'object_type instance'
    ('binaryInput', 1, None): 'binaryOutput 2',
    ('binaryInput', 2, None): 'binaryOutput 3',
    ('binaryInput', 3, None): 'binaryOutput 4',
    ('binaryInput', 4, None): 'binaryOutput 5',
}

# do forever
while True:
    try:
        # wait for new messages
        parsed_data = receive()

        # check if data is a dictionary
        if not isinstance(parsed_data, dict):
            # check if data is None
            if parsed_data is not None:
                # print error
                print >> sys.stderr, 'unsupported instance type'
                print >> sys.stderr, parsed_data

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

    except Exception:
        pass
