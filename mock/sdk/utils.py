from enum import IntEnum
from multiprocessing import shared_memory

from mock.sdk import API_Proc


class MEMORY_ALLOCATION_MODE(IntEnum):
    CREATE_ONLY = 1
    USE_ONLY = 2
    CREATE_OR_USE = 3


class SharedMemoryBuffer:

    def __init__(self, name: str, size: int, mode=MEMORY_ALLOCATION_MODE.USE_ONLY):
        self.size = size
        self.name = name
        self.mode = mode
        self.mem = None
        self.init()

    def init(self):
        if self.mode == MEMORY_ALLOCATION_MODE.USE_ONLY:
            try:
                self.mem = shared_memory.SharedMemory(name=self.name, size=self.size)
            except FileNotFoundError:
                raise MemoryError("Accessing unallocated memory")

        if self.mode == MEMORY_ALLOCATION_MODE.CREATE_ONLY:
            try:
                self.mem = shared_memory.SharedMemory(name=self.name, create=True, size=self.size)
            except FileExistsError:
                raise MemoryError("Memory already allocated")
        if self.mode == MEMORY_ALLOCATION_MODE.CREATE_OR_USE:
            try:
                self.mem = shared_memory.SharedMemory(name=self.name, size=self.size)
            except FileNotFoundError:
                try:
                    self.mem = shared_memory.SharedMemory(name=self.name, create=True, size=self.size)
                    self.mem.buf[:] = bytearray(self.size)
                except FileExistsError:
                    raise MemoryError("Memory allocation conflict")

    @property
    def buffer(self):
        return self.mem.buf

    def read_int(self, address, size=4):
        return int.from_bytes(self.buffer[address:address + size], "little")

    def write_int(self, address, value: int, size=4):
        self.buffer[address:address + size] = value.to_bytes(size, "little")


def processor_shared_memory_name(proc: API_Proc):
    return f"processor_control_{proc.name}"
