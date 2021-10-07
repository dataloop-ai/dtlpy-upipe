import multiprocessing
import shared_memory_dict
import numpy as np
import asyncio


def rs232_checksum(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)


class Message:
    header_size = 10
    fotter_size = 10

    def __init__(self, data):
        self.data = data

    def write_to_buffer(self, buffer, address):
        buffer[address] = 1
        buffer[address + self.header_size:len(self.data)] = bytearray(self.data)
        buffer[address] = 2
        return self.size

    @property
    def size(self):
        return self.header_size + len(self.data) + self.fotter_size


class MessageMemory:
    def __init__(self, data):
        self.data = data


class Processor(multiprocessing.Process):
    ...

    async def waiter(self, event):
        print('waiting for it ...')
        await event.wait()
        self.on_data(self.get_current_message_data())

    def __init__(self, name):
        self.on_data = None
        self.name -= name
        self.length = 10
        self.smd = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def on_data(self, on_data):
        self.on_data = on_data

    def get_current_message_data(self):
        return 1


class Queue:
    def __init__(self, name):
        self.length = 10
        self.nextMessageAddress = 0
        self.smd = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def get(self):
        return self.smd.pop(list(np.min(self.smd.keys()))[0])

    def put(self, data):
        msg = Message(data)
        self.nextMessageAddress += msg.write_to_buffer(self.smd, self.nextMessageAddress)


class Block:
    ...


class Pipe:

    def __init__(self):
        self.processors = list()
        self.main_block = shared_memory_dict.SharedMemoryDict(name='u_pipe_main', size=1025)

    def add(self, processor):
        self.processors.append(processor)

    def start(self):
        for p in self.processors:
            ...
