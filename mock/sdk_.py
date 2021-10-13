import multiprocessing
import numpy as np
import asyncio
import subprocess
from multiprocessing import shared_memory


def rs232_checksum(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)


class Message:
    header_size = 10
    fotter_size = 10

    def __init__(self, data):
        self.data = data
        self.data_size = len(self.data)

    def write_to_buffer(self, buffer, address):
        buffer[address] = 1
        size_bytes = self.data_size.to_bytes(4, 'big')
        buffer[address + 1:address + 5] = size_bytes
        data_start = address + self.header_size
        data_end = data_start + self.data_size
        buffer[data_start:data_end] = self.data
        buffer[address] = 2
        return self.size

    @staticmethod
    def from_buffer(self, buffer, address):
        size = int.from_bytes(buffer[1], 'big')
        m = Message(buffer[address + self.header_size:len(self.data)])
        return m

    @property
    def size(self):
        return self.header_size + len(self.data) + self.fotter_size


class MessageMemory:
    def __init__(self, data):
        self.data = data


class Processor:
    ...

    async def waiter(self, event):
        print('waiting for it ...')
        await event.wait()
        self.on_data_callback(self.get_current_message_data())

    def __init__(self, name, path=None):  # name is unique per pipe
        self.proc = None
        self.path = path
        self.on_data_callback = None
        self.name = name
        self.length = 10
        self.children = list()
        self.inQ = Queue('{}_in'.format(self.name), self.on_message)
        self.outQ = Queue('{}_out'.format(self.name))
        # self.smd = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def add(self, processor):
        if self.get(processor.name):
            return
        print("Adding {}".format(processor.name))
        self.children.append(processor)
        return processor

    def get(self, name):
        proc = next((p for p in self.children if p.name == name), None)
        return proc

    def start(self):
        started = []
        if self.path:
            started.append(self)
            self.proc = subprocess.Popen([r'E:\Shabtay\platform\micro-pipelines\venv\Scripts\python.exe', self.path],
                                         stdout=subprocess.PIPE)
        for p in self.children:
            started.extend(p.start())
        return started

    def all_child_procs(self):
        procs = [self]
        for p in self.children:
            procs.extend(p.all_child_procs())
        return procs

    @property
    def count(self):
        me = 0
        if self.proc:
            me = 1
        return me + sum([p.count for p in self.children])

    def on_data(self, on_data):
        self.on_data_callback = on_data

    def on_message(self, msg):
        if self.on_data_callback:
            self.on_data_callback(msg.data)

    def get_current_message_data(self):
        return 1

    def emit(self, data):
        self.outQ.put(bytearray(data))


class Queue:
    def __init__(self, name, on_message=None, size=1025):
        self.length = 10
        self.name = name
        self.size = size
        self.nextAddress = 0
        self.currentAddress = 0
        try:
            self.mem = shared_memory.SharedMemory(name=self.name, create=True, size=self.size)
        except FileExistsError:
            self.mem = shared_memory.SharedMemory(name=self.name, size=self.size)

        self.on_message = on_message

    def get(self):
        return self.smd.pop(list(np.min(self.smd.keys()))[0])

    def put(self, data):
        msg = Message(data)
        self.nextAddress += msg.write_to_buffer(self.mem.buf, self.nextAddress)

    def handle_incoming_message(self):
        msg = Message.from_buffer(self.mem, self.nextAddress)
        if self.on_message:
            self.on_message(msg)


    async def wait_for_message(self):
        while True:
            await asyncio.sleep(.1)
            if self.mem[self.nextMessageAddress] == 2:
                self.handle_incoming_message()


class Block:
    ...


control_mem_name = "control_mem"


class MemoryBlock:
    def __init__(self, block):
        self.block = block

    def read_u8(self, address):
        return self.block.buf[address]

    def write_u8(self, address, value):
        self.block[address] = value

    def write_bytes(self, address, byte_arr):
        self.block.buf[address:address + len(byte_arr)] = byte_arr


class ControlMemory(MemoryBlock):
    PROC_TABLE_OFFSET = 1000
    PROC_TABLE_SIZE = 1000
    PROC_TABLE_ENTRY_SIZE = 100
    Q_TABLE_OFFSET = PROC_TABLE_OFFSET + PROC_TABLE_SIZE
    Q_TABLE_ENTRY_SIZE = 100
    Q_TABLE_SIZE = 1000
    NEXT_PROC_ID = 1

    def __init__(self):
        mem = shared_memory.SharedMemory(name=control_mem_name, create=True, size=5000)
        MemoryBlock.__init__(self, mem)

    def get_available_proc_block_offset(self):
        for i in range(ControlMemory.PROC_TABLE_OFFSET, ControlMemory.PROC_TABLE_OFFSET + ControlMemory.PROC_TABLE_SIZE,
                       ControlMemory.PROC_TABLE_ENTRY_SIZE):
            if not self.read_u8(i):
                return i
        return -1

    def register_proc(self, name):
        proc_block_address=self.get_available_proc_block_offset()
        if proc_block_address<0:
            return
        encoded_name = name.encode()
        byte_array = bytearray(encoded_name)
        self.write_bytes(proc_block_address,byte_array)

class Pipe(Processor):

    def __init__(self, name):
        Processor.__init__(self, name)
        self.active = list()
        self._init()
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def _init(self):
        self.control_mem = ControlMemory()

    def _map_pipe(self):
        all_procs=self.all_child_procs()
        for p in all_procs:
            self.control_mem.register_proc(p.name)

    def start(self):
        self._map_pipe()
        self.active = super(Pipe, self).start()
        print("Started {} processors".format(self.count))
        asyncio.run(self.wait_for_completion())
        return self.active

    async def wait_for_completion(self):
        while True:
            await asyncio.sleep(.1)
            for p in self.active:
                if p.proc:
                    line = p.proc.stdout.readline()
                    if (line):
                        print("{}>>>{}".format(p.name, line))
