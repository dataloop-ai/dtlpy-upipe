import asyncio
from multiprocessing import shared_memory

from .processor import Processor

control_mem_name = "control_mem"


class Pipe(Processor):

    def __init__(self, name):
        Processor.__init__(self, name)
        self.controller = True
        self.active = list()
        self.queues = []
        # self.main_block = shared_memory_dict.SharedMemoryDict(name=name, size=1025)

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
