# Blues Serial-Over-I2C Protocol Analyzer
# For more information and documentation, please go to https://dev.blues.io/guides-and-tutorials/notecard-guides/serial-over-i2c-protocol/

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, NumberSetting

# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):

    # Parameters
    notecard_i2c_addr = NumberSetting(min_value=0, max_value=127)

    # An optional list of types this analyzer produces, providing a way to customize the way frames are displayed in Logic 2.
    result_types = {
        'addr': {
            'format': '{{data.sender}}'
        },
        'hdr': {
            'format': '{{data.action}}: {{data.length}}'
        },
        'note': {
            'format': '{{data.Note}}'
        },
        'query': {
            'format': 'Query Notecard'
        },
        'request': {
            'format': 'Request: {{data.length}}'
        }
    }

    def __init__(self):

        self.data = {
            'note': [],
            'start_time': None
        }
        self.hdr1 = None
        self.hdr2 = None
        self.ignore = False
        self.request_start_time = None
        self.read = None

        if self.notecard_i2c_addr == 0x00:
            self.notecard_i2c_addr = 0x17

        print(f"=======================================")
        print(f"Blues Serial-Over-I2C Protocol Analyzer")
        print()
        print('Settings:')
        print(f"- Notecard I2C Address: 0x{int(self.notecard_i2c_addr):02X}")
        print()
        print(f"https://dev.blues.io/guides-and-tutorials/notecard-guides/serial-over-i2c-protocol/")

    def decode(self, frame: AnalyzerFrame):

        if frame.type == 'start':
            # /--------------------------------------/
            # /------/ START FRAME DATA ITEMS /------/
            # /--------------------------------------/
            # /--------------------------------------/

            self.data = {
                'note': [],
                'start_time': None
            }
            self.hdr1 = None
            self.hdr2 = None
            self.ignore = False
            self.request_start_time = None
            self.read = None

        elif frame.type == 'address':
            # /----------------------------------------/
            # /------/ ADDRESS FRAME DATA ITEMS /------/
            # /----------------------------------------/
            # Key: ack, Value: True
            # Key: address, Value: b'\x17'
            # Key: read, Value: False
            # /----------------------------------------/
            if (frame.data['address'][0] != self.notecard_i2c_addr):
                self.ignore = True
                return None

            print(f"=======================================")
            self.read = frame.data['read']

            sender = 'Host MCU' if not frame.data['read'] else 'Notecard'
            print(f"Sender: {sender}")
            return AnalyzerFrame('addr', frame.start_time, frame.end_time, {
                'sender': sender
            })

        elif frame.type == 'data':
            # /-------------------------------------/
            # /------/ DATA FRAME DATA ITEMS /------/
            # /-------------------------------------/
            # Key: ack, Value: True
            # Key: data, Value: b'^'
            # /-------------------------------------/
            if self.ignore:
                return None

            if self.read: # Notecard Response
                # Special Handling for Header Byte 1
                if self.hdr1 == None:
                    self.hdr1 = frame.data['data'][0]

                    # Handle Notecard Response
                    print(f"Queued: {self.hdr1}")
                    return AnalyzerFrame('hdr', frame.start_time, frame.end_time, {
                        'action': 'Queued',
                        'length': self.hdr1
                    })

                # Special Handling for Header Byte 2
                elif self.hdr2 == None:
                    self.hdr2 = frame.data['data'][0]

                    # Handle Notecard Response
                    print(f"Sending: {self.hdr2}")
                    return AnalyzerFrame('hdr', frame.start_time, frame.end_time, {
                        'action': 'Sending',
                        'length': self.hdr2
                    })

            else: # Host MCU Request
                # Special Handling for Header Byte 1
                if self.hdr1 == None:
                    self.hdr1 = frame.data['data'][0]

                    # Handle Host MCU Request
                    if self.hdr1 == 0:
                        self.request_start_time = frame.start_time
                        return None
                    else:
                        print(f"Sending: {self.hdr1}")
                        return AnalyzerFrame('hdr', frame.start_time, frame.end_time, {
                            'action': 'Sending',
                            'length': self.hdr1
                        })

                # Special Handling for Header Byte 2
                elif self.hdr2 == None:
                    self.hdr2 = frame.data['data'][0]

                    # Handle Host MCU Request
                    if self.request_start_time != None:
                        if self.hdr2 == 0:
                            # Handle Query Request
                            print(f"Query Notecard")
                            return AnalyzerFrame('query', self.request_start_time, frame.end_time, None)
                        else:
                            # Handle Request Bytes
                            print(f"Request: {self.hdr2}")
                            return AnalyzerFrame('request', self.request_start_time, frame.end_time, {
                                'length': self.hdr2
                            })

            # Handle Note Bytes (Request or Response)
            if self.data['start_time'] == None:
                self.data['start_time'] = frame.start_time

            self.data['note'].append(frame.data['data'])

        elif frame.type == 'stop':
            # /-------------------------------------/
            # /------/ STOP FRAME DATA ITEMS /------/
            # /-------------------------------------/
            # /-------------------------------------/

            if len(self.data['note']) > 0:
                note = ''.join([byte.decode('ascii') for byte in self.data['note']]).rstrip('\n')
                print(f"Note: {note}")
                return AnalyzerFrame('note', self.data['start_time'], frame.end_time, {
                    'Note': note
                })
            else:
                return None

        # Return the data frame itself
        return None
