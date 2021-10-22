import asyncio

from typing import Dict

from .processor import Processor
from .. import API_Proc
from ..node.node import ComputeNode

control_mem_name = "control_mem"


class Pipe(Processor):

    def __init__(self, name):
        Processor.__init__(self, name)
        self.controller = True
        self.active = list()
        self.queues = []
        self.node = ComputeNode.instance()
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

    async def _map_pipe(self):
        self.queues = self.allocate_queues()
        for q in self.queues:
            await self.node_client.register_queue(q)
        # for p in all_procs:
        #     self.control_mem.register_proc(p.name)

    async def _prepare(self):
        self.enum()
        await self.register(self)
        await self._map_pipe()
        return True

    async def register(self, proc):
        response_data = await self.node.register_proc(proc.api_def)
        print(f"Registered:  {proc.api_def.name}")
        proc.registered = True
        if response_data and 'messages' in response_data:
            messages = response_data['messages']
            for m in messages:
                proc.handle_message(m)
        if not proc.registered:
            raise EnvironmentError(f"Cant register processor {self.name}")
        for p in proc.children:
            await self.register(p)
        return True

    async def start(self):
        await self.node.init(self.name)
        if not await self._prepare():
            raise BrokenPipeError
        await asyncio.wait([await self.node.start()])

    async def broadcast(self, body: Dict):
        msg = {"type": "broadcast", "body": body}
        return await self.node_client.send_message(msg)
