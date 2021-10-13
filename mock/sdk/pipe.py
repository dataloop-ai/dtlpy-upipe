import asyncio
from multiprocessing import shared_memory

from .message import MemoryBlock
from .processor import Processor

control_mem_name = "control_mem"


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
        proc_block_address = self.get_available_proc_block_offset()
        if proc_block_address < 0:
            return
        encoded_name = name.encode()
        byte_array = bytearray(encoded_name)
        self.write_bytes(proc_block_address, byte_array)


class Pipe(Processor):

    def __init__(self, name):
        Processor.__init__(self, name)
        self.active = list()
        self._init()
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def _init(self):
        self.control_mem = ControlMemory()

    def _map_pipe(self):
        all_procs = self.all_child_procs()
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
                    if line:
                        print("{}>>>{}".format(p.name, line))
