from multiprocessing import shared_memory

from .message import Message
import asyncio


class Queue:
    def __init__(self, name, on_message=None, size=1025):
        self.length = 10
        self.name = name
        self.size = size
        self.nextMessageAddress = 0
        self.currentAddress = 0
        try:
            self.mem = shared_memory.SharedMemory(name=self.name, create=True, size=self.size)
        except FileExistsError:
            self.mem = shared_memory.SharedMemory(name=self.name, size=self.size)

        self.on_message = on_message

    def get(self):
        pass

    def put(self, data):
        msg = Message(data)
        self.nextMessageAddress += msg.write_to_buffer(self.mem.buf, self.nextMessageAddress)

    def handle_incoming_message(self):
        msg = Message.from_buffer(self.mem, self.nextMessageAddress)
        if self.on_message:
            self.on_message(msg)

    async def wait_for_message(self):
        while True:
            await asyncio.sleep(.1)
            if self.mem.buf[self.nextMessageAddress] == 2:
                self.handle_incoming_message()
