class Operation(Enum):
    take = 0
    write = 1


# TODO
class LogEntry:
    """ An entry in our replicated, distributed log

    LogEntries include the current term number and the command to be
    replicated to the StateMachine

    """
    def __init__(self, term, operation, payload):
        self.current_term = term
        self.event_type = Operation(operation)
        self.payload = payload

# TODO
class Log:
    """ The replicated, distributed log

    """
    def __init__(self):
        self.log_list = []
        self.commited = False
        self.next_available_index = 0

    def append(self, logEntry):
        self.log_list.append(logEntry)
        self.next_available_index += 1

    def display(self):
        for le in self.log_list:
            print(f'Term:{le.current_term}\n Event:{le.event_type}\n Payload:{le.payload}')
            print('\n')
