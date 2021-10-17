import asyncio
from multiprocessing import shared_memory

from .dataframe import MemoryBlock
from .processor import Processor
from .mem_queue import Queue

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
        global control_mem_name
        # mem = shared_memory.SharedMemory(size=5000)
        # MemoryBlock.__init__(self, mem)
        pass

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
        self.controller = True
        self.active = list()
        self._init()
        self.queues = []
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    def _init(self):
        self.control_mem = ControlMemory()

    def _map_pipe(self):
        self.queues = self.allocate_queues()
        for q in self.queues:
            self.node_client.register_queue(q)
        # for p in all_procs:
        #     self.control_mem.register_proc(p.name)

    def _prepare(self):
        self.enum()
        self.register()
        self._map_pipe()
        return self.serve()

    def start(self):
        if not self._prepare():
            raise BrokenPipeError
        self.active = super(Pipe, self).start()
        print("Started {} processors".format(self.count))
        loop = asyncio.get_event_loop()
        loop.run_forever()

    def register(self):
        if self.node_client.register_controller(self.on_ws_message):
            self.registered = True
            print("controller registered")

    def serve(self):
        if self.node_client.serve():
            print("serving")
            return True
        else:
            print("Error serving")
            return False

    async def wait_for_completion(self):
        while True:
            await asyncio.sleep(.1)
            for p in self.active:
                if p.proc:
                    line = p.proc.stdout.readline()
                    if line:
                        print("{}>>>{}".format(p.name, line))
